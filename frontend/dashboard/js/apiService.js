/**
 * SmartPatientCare - API Service Layer & WebSocket Client
 * Author: Gauri (Frontend & CV Lead)
 * 
 * Provides clean abstractions for backend REST API and WebSocket integration,
 * with comprehensive, seamless fallback to local mock data if the backend is offline.
 */

class ApiService {
  constructor(config, mockData) {
    this.config = config;
    this.mockData = mockData;
    this.backendUrl = config.BACKEND_URL;
    
    // In-memory state caches for graceful offline/demo mode
    this.patients = JSON.parse(JSON.stringify(mockData.patients));
    this.alerts = JSON.parse(JSON.stringify(mockData.initialAlerts));
    
    // Connection tracking
    this.isBackendOnline = false;
    this.isWsConnected = false;
    this.ws = null;
    this.wsReconnectTimeout = null;
    this.listeners = {
      eventReceived: [],
      connectionChanged: [],
      patientUpdated: []
    };

    // Auto-mock simulation ticker
    this.mockTimer = null;
    this.vitalsTimer = null;
  }

  /**
   * Register event callbacks
   */
  on(event, callback) {
    if (this.listeners[event]) {
      this.listeners[event].push(callback);
    }
  }

  notify(event, data) {
    if (this.listeners[event]) {
      this.listeners[event].forEach(cb => {
        try {
          cb(data);
        } catch (err) {
          console.error(`Error in listener for ${event}:`, err);
        }
      });
    }
  }

  /**
   * Helper to construct complete API URLs
   */
  _getUrl(path) {
    return `${this.backendUrl.replace(/\/$/, '')}${path}`;
  }

  /**
   * GET /api/patients
   */
  async getPatients() {
    try {
      const response = await fetch(this._getUrl(this.config.API_ENDPOINTS.PATIENTS), {
        signal: AbortSignal.timeout(3000)
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      this.isBackendOnline = true;
      this.patients = data;
      this.notify('connectionChanged', { backend: true, ws: this.isWsConnected });
      return data;
    } catch (err) {
      // Graceful fallback to mock data
      this.isBackendOnline = false;
      this.notify('connectionChanged', { backend: false, ws: this.isWsConnected });
      return this.patients;
    }
  }

  /**
   * GET /api/patients/{id}
   */
  async getPatientById(id) {
    try {
      const response = await fetch(this._getUrl(this.config.API_ENDPOINTS.PATIENT_BY_ID(id)), {
        signal: AbortSignal.timeout(3000)
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (err) {
      return this.patients.find(p => p.patient_id === id) || null;
    }
  }

  /**
   * GET /api/events
   */
  async getEvents() {
    try {
      const response = await fetch(this._getUrl(this.config.API_ENDPOINTS.EVENTS), {
        signal: AbortSignal.timeout(3000)
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data = await response.json();
      this.alerts = data;
      return data;
    } catch (err) {
      return this.alerts;
    }
  }

  /**
   * GET /api/events/active
   */
  async getActiveEvents() {
    try {
      const response = await fetch(this._getUrl(this.config.API_ENDPOINTS.ACTIVE_EVENTS), {
        signal: AbortSignal.timeout(3000)
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return await response.json();
    } catch (err) {
      return this.alerts.filter(a => a.status === 'ACTIVE' || a.status === 'ACKNOWLEDGED');
    }
  }

  /**
   * POST /api/events
   */
  async postEvent(eventData) {
    try {
      const response = await fetch(this._getUrl(this.config.API_ENDPOINTS.EVENTS), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(eventData),
        signal: AbortSignal.timeout(3000)
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const created = await response.json();
      this.handleIncomingEvent(created);
      return created;
    } catch (err) {
      // Local ingestion in mock mode
      const localEvent = {
        ...eventData,
        event_id: eventData.event_id || `EVT-${Date.now().toString().slice(-6)}`,
        timestamp: eventData.timestamp || new Date().toISOString(),
        status: eventData.status || 'ACTIVE'
      };
      this.handleIncomingEvent(localEvent);
      return localEvent;
    }
  }

  /**
   * POST /api/events/{id}/acknowledge
   */
  async acknowledgeEvent(eventId) {
    try {
      const response = await fetch(this._getUrl(this.config.API_ENDPOINTS.ACKNOWLEDGE_EVENT(eventId)), {
        method: 'POST',
        signal: AbortSignal.timeout(3000)
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const updated = await response.json();
      this._updateAlertInState(updated);
      return updated;
    } catch (err) {
      // Update local state
      const alert = this.alerts.find(a => a.event_id === eventId);
      if (alert) {
        alert.status = 'ACKNOWLEDGED';
        this._updateAlertInState(alert);
      }
      return alert;
    }
  }

  /**
   * POST /api/events/{id}/resolve
   */
  async resolveEvent(eventId) {
    try {
      const response = await fetch(this._getUrl(this.config.API_ENDPOINTS.RESOLVE_EVENT(eventId)), {
        method: 'POST',
        signal: AbortSignal.timeout(3000)
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const updated = await response.json();
      this._updateAlertInState(updated);
      return updated;
    } catch (err) {
      // Update local state
      const alert = this.alerts.find(a => a.event_id === eventId);
      if (alert) {
        alert.status = 'RESOLVED';
        this._updateAlertInState(alert);
      }
      return alert;
    }
  }

  _updateAlertInState(updatedAlert) {
    const idx = this.alerts.findIndex(a => a.event_id === updatedAlert.event_id);
    if (idx !== -1) {
      this.alerts[idx] = updatedAlert;
    }
    this._recomputePatientStatus(updatedAlert.patient_id);
  }

  /**
   * Process an incoming event (from WebSocket, REST, or local generator)
   */
  handleIncomingEvent(event) {
    // Add to alert collection (prepended for recency)
    const existingIndex = this.alerts.findIndex(a => a.event_id === event.event_id);
    if (existingIndex >= 0) {
      this.alerts[existingIndex] = event;
    } else {
      this.alerts.unshift(event);
    }

    // Update patient status & telemetry accordingly
    const patient = this.patients.find(p => p.patient_id === event.patient_id);
    if (patient) {
      // Update parameter if present
      if (event.parameter === 'heart_rate' && typeof event.value === 'number') {
        patient.heart_rate = event.value;
      } else if (event.parameter === 'spo2' && typeof event.value === 'number') {
        patient.spo2 = event.value;
      } else if (event.parameter === 'respiratory_rate' && typeof event.value === 'number') {
        patient.respiratory_rate = event.value;
      } else if (event.source === 'drip_sensor' || event.event_type.includes('DRIP')) {
        if (event.event_type === 'DRIP_FINISHED') {
          patient.drip_status = 'Finished';
          patient.drip_level = 0;
        } else if (event.event_type === 'DRIP_NEARLY_FINISHED') {
          patient.drip_status = 'Nearly Finished';
          patient.drip_level = 10;
        } else if (event.event_type === 'DRIP_LOW') {
          patient.drip_status = 'Low';
          patient.drip_level = 20;
        }
      }

      // Computer Vision events
      if (event.source === 'computer_vision' || event.event_type === 'FALL_DETECTED' || event.event_type === 'PATIENT_ABNORMALITY') {
        patient.cv_last_event = event.event_type;
        if (event.event_type === 'FALL_DETECTED') {
          patient.cv_status = 'FALL DETECTED';
        } else if (event.message && event.message.toLowerCase().includes('bed')) {
          patient.cv_status = 'PATIENT LEFT BED';
        } else if (event.message && event.message.toLowerCase().includes('position')) {
          patient.cv_status = 'UNUSUAL POSITION';
        } else {
          patient.cv_status = 'ABNORMAL MOVEMENT';
        }
      }

      this._recomputePatientStatus(patient.patient_id);
    }

    // Broadcast to UI subscribers
    this.notify('eventReceived', event);
  }

  /**
   * Recalculate patient status (NORMAL / WARNING / CRITICAL) and alert count
   */
  _recomputePatientStatus(patientId) {
    const patient = this.patients.find(p => p.patient_id === patientId);
    if (!patient) return;

    const patientActiveAlerts = this.alerts.filter(
      a => a.patient_id === patientId && (a.status === 'ACTIVE' || a.status === 'ACKNOWLEDGED')
    );

    patient.active_alert_count = patientActiveAlerts.length;

    const hasCritical = patientActiveAlerts.some(a => a.severity === 'CRITICAL');
    const hasWarning = patientActiveAlerts.some(a => a.severity === 'WARNING');

    if (hasCritical) {
      patient.status = 'CRITICAL';
    } else if (hasWarning) {
      patient.status = 'WARNING';
    } else {
      patient.status = 'NORMAL';
    }

    this.notify('patientUpdated', patient);
  }

  /**
   * WebSocket Connection Management
   */
  initWebSocket() {
    if (typeof WebSocket === 'undefined') return;

    // Convert http/https URL to ws/wss
    const wsBase = this.backendUrl.replace(/^http(s)?:\/\//, (match, p1) => (p1 ? 'wss://' : 'ws://'));
    const wsUrl = `${wsBase.replace(/\/$/, '')}${this.config.WS_ENDPOINT}`;

    try {
      if (this.ws) {
        this.ws.close();
      }

      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.isWsConnected = true;
        this.notify('connectionChanged', { backend: this.isBackendOnline, ws: true });
        this.stopMockSimulation(); // Stop automatic synthetic events when real WS is live
      };

      this.ws.onmessage = (evt) => {
        try {
          const event = JSON.parse(evt.data);
          this.handleIncomingEvent(event);
        } catch (err) {
          console.error('Error parsing incoming WebSocket message:', err);
        }
      };

      this.ws.onclose = () => {
        this.isWsConnected = false;
        this.notify('connectionChanged', { backend: this.isBackendOnline, ws: false });
        this._scheduleWsReconnect();
      };

      this.ws.onerror = () => {
        this.isWsConnected = false;
        this.notify('connectionChanged', { backend: this.isBackendOnline, ws: false });
      };
    } catch (e) {
      this.isWsConnected = false;
      this.notify('connectionChanged', { backend: this.isBackendOnline, ws: false });
      this._scheduleWsReconnect();
    }
  }

  _scheduleWsReconnect() {
    if (this.wsReconnectTimeout) clearTimeout(this.wsReconnectTimeout);
    // Attempt reconnection every 10 seconds
    this.wsReconnectTimeout = setTimeout(() => {
      this.initWebSocket();
    }, 10000);
  }

  /**
   * Mock Simulation Engine (Active when offline or manually initiated)
   */
  startMockSimulation() {
    if (this.mockTimer) return;

    // Periodic random events to simulate lively nursing station
    this.mockTimer = setInterval(() => {
      // Only generate if WebSocket is not connected
      if (!this.isWsConnected) {
        const event = this.mockData.generateRandomEvent();
        this.handleIncomingEvent(event);
      }
    }, this.config.MOCK_MODE.SIMULATION_INTERVAL_MS);

    // Subtle vitals fluctuation to bring monitor alive
    this.vitalsTimer = setInterval(() => {
      this.patients.forEach(p => {
        // Minor natural variance
        const hrDelta = Math.floor(Math.random() * 3) - 1;
        p.heart_rate = Math.max(50, Math.min(160, p.heart_rate + hrDelta));

        const rrDelta = Math.floor(Math.random() * 3) - 1;
        p.respiratory_rate = Math.max(10, Math.min(35, p.respiratory_rate + rrDelta));

        // IV drip drainage
        if (p.drip_level > 0 && Math.random() > 0.6) {
          p.drip_level = Math.max(0, p.drip_level - 1);
          if (p.drip_level === 0) {
            p.drip_status = 'Finished';
          } else if (p.drip_level <= 10) {
            p.drip_status = 'Nearly Finished';
          } else if (p.drip_level <= 25) {
            p.drip_status = 'Low';
          }
        }
      });
      this.notify('patientUpdated', null);
    }, this.config.MOCK_MODE.VITALS_TICK_MS);
  }

  stopMockSimulation() {
    if (this.mockTimer) {
      clearInterval(this.mockTimer);
      this.mockTimer = null;
    }
    if (this.vitalsTimer) {
      clearInterval(this.vitalsTimer);
      this.vitalsTimer = null;
    }
  }

  /**
   * Manual scenario triggers for hackathon demonstrations
   */
  triggerDemoScenario(scenarioIndex) {
    if (this.mockData.demoScenarios[scenarioIndex]) {
      const scenario = this.mockData.demoScenarios[scenarioIndex];
      const event = {
        event_id: `DEMO-${Date.now().toString().slice(-6)}`,
        timestamp: new Date().toISOString(),
        ...scenario.event
      };
      this.handleIncomingEvent(event);
      return event;
    }
    return null;
  }
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = ApiService;
}
