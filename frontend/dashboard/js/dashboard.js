/**
 * SmartPatientCare - Dashboard Controller with CCTV Event Evidence
 * Author: Gauri (Frontend & CV Lead)
 * 
 * Orchestrates UI interactions, real-time alert updates, patient selection,
 * emergency modal notifications, and automatic CCTV demo video evidence streaming.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize services
  const apiService = new ApiService(CONFIG, MOCK_DATA);
  const ecgWaveform = new EcgWaveform('ecgCanvas');

  // Application State
  let selectedPatientId = 'P001';
  let activeFilter = 'ACTIVE'; // 'ALL' | 'ACTIVE' | 'CRITICAL' | 'RESOLVED'
  let autoSimEnabled = true;
  let currentCctvEvent = null;

  // DOM Element References
  const clockEl = document.getElementById('liveClock');
  const dateEl = document.getElementById('liveDate');
  const connStatusBadge = document.getElementById('connStatusBadge');
  const connStatusText = document.getElementById('connStatusText');
  const patientGridEl = document.getElementById('patientGrid');
  const alertListEl = document.getElementById('alertList');
  const alertCountBadge = document.getElementById('totalActiveAlertCount');
  
  // Selected Patient View Elements
  const selPatientName = document.getElementById('selPatientName');
  const selPatientMeta = document.getElementById('selPatientMeta');
  const selPatientStatus = document.getElementById('selPatientStatus');
  const selHeartRate = document.getElementById('selHeartRate');
  const selSpo2 = document.getElementById('selSpo2');
  const selBp = document.getElementById('selBp');
  const selTemp = document.getElementById('selTemp');
  const selRespRate = document.getElementById('selRespRate');
  const selDripStatus = document.getElementById('selDripStatus');
  const selDripFill = document.getElementById('selDripFill');
  const selDripRate = document.getElementById('selDripRate');
  const selDripPercent = document.getElementById('selDripPercent');
  const selCvStatusBadge = document.getElementById('selCvStatusBadge');
  const selCvLastCheck = document.getElementById('selCvLastCheck');
  const selPatientCctvBtn = document.getElementById('selPatientCctvBtn');

  // CCTV Evidence Panel Elements
  const cctvEvidencePanel = document.getElementById('cctvEvidencePanel');
  const cctvCamBadge = document.getElementById('cctvCamBadge');
  const cctvSeverityBadge = document.getElementById('cctvSeverityBadge');
  const cctvMinimizeBtn = document.getElementById('cctvMinimizeBtn');
  const cctvVideoPlayer = document.getElementById('cctvVideoPlayer');
  const cctvOverlayCamera = document.getElementById('cctvOverlayCamera');
  const cctvOverlayStatus = document.getElementById('cctvOverlayStatus');
  const cctvPatientName = document.getElementById('cctvPatientName');
  const cctvRoomLocation = document.getElementById('cctvRoomLocation');
  const cctvEventType = document.getElementById('cctvEventType');
  const cctvIncidentTime = document.getElementById('cctvIncidentTime');
  const cctvEventMessage = document.getElementById('cctvEventMessage');
  const cctvAckBtn = document.getElementById('cctvAckBtn');
  const cctvResolveBtn = document.getElementById('cctvResolveBtn');
  const toggleCctvBtn = document.getElementById('toggleCctvBtn');

  // Emergency Modal Elements
  const emergencyModal = document.getElementById('emergencyModal');
  const emergencyRoom = document.getElementById('emergencyRoom');
  const emergencyType = document.getElementById('emergencyType');
  const emergencyMsg = document.getElementById('emergencyMsg');
  const emergencyTime = document.getElementById('emergencyTime');
  const emergencyAckBtn = document.getElementById('emergencyAckBtn');
  const emergencyCloseBtn = document.getElementById('emergencyCloseBtn');
  const emergencyViewCctvBtn = document.getElementById('emergencyViewCctvBtn');
  let currentEmergencyEvent = null;

  // Critical Event Types that require CCTV inspection
  const CRITICAL_EVENT_TYPES = [
    'FALL_DETECTED',
    'EMERGENCY',
    'LOW_SPO2',
    'ABNORMAL_ECG',
    'ABNORMAL_HEART_RATE',
    'ABNORMAL_BP',
    'DRIP_FINISHED',
    'VENTILATOR_DISCONNECT',
    'VENTILATOR_ALERT'
  ];

  function isCriticalEvent(event) {
    if (!event) return false;
    if (event.severity === 'CRITICAL') return true;
    return CRITICAL_EVENT_TYPES.includes(event.event_type);
  }

  // Clock Update
  function updateClock() {
    const now = new Date();
    clockEl.textContent = now.toLocaleTimeString('en-US', { hour12: false });
    dateEl.textContent = now.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  }
  setInterval(updateClock, 1000);
  updateClock();

  // Connection Status Update
  function updateConnectionUI(status) {
    if (status.ws) {
      connStatusBadge.className = 'status-dot dot-online';
      connStatusText.textContent = 'WebSocket Live';
    } else if (status.backend) {
      connStatusBadge.className = 'status-dot dot-warning';
      connStatusText.textContent = 'REST Live (WS Offline)';
    } else {
      connStatusBadge.className = 'status-dot dot-mock';
      connStatusText.textContent = 'Simulated Mode (Standalone)';
    }
  }

  // ====================================================================
  // CCTV Event Evidence Viewer Logic
  // ====================================================================
  function showCctvEvidence(event) {
    if (!event) return;
    currentCctvEvent = event;

    const patient = apiService.patients.find(p => p.patient_id === event.patient_id);
    const mapping = MOCK_DATA.cctvMapping[event.patient_id] || {
      video: 'videos/fall_demo_web.mp4',
      camera: `CAM-${event.room_id || '101'}`
    };

    // Determine video source path
    let videoSrc = 'videos/fall_demo_web.mp4';
    // Normalize path for web browser
    if (videoSrc.includes('/')) {
      const filename = videoSrc.split('/').pop();
      videoSrc = 'videos/' + filename;
    } else if (!videoSrc.startsWith('videos/')) {
      videoSrc = 'videos/' + videoSrc;
    }

    const cameraId = event.camera_id || mapping.camera || `CAM-${event.room_id}`;
    const pName = patient ? patient.name : 'Patient';

    // Populate CCTV Header & Details
    cctvCamBadge.textContent = `${cameraId} • ${event.room_id} (${event.patient_id})`;
    cctvOverlayCamera.textContent = cameraId;
    cctvOverlayStatus.textContent = `${event.event_type.replace(/_/g, ' ')} EVIDENCE`;

    cctvPatientName.textContent = `${event.patient_id} - ${pName}`;
    cctvRoomLocation.textContent = event.room_id;
    cctvEventType.textContent = event.event_type.replace(/_/g, ' ');
    cctvIncidentTime.textContent = new Date(event.timestamp).toLocaleTimeString();
    cctvEventMessage.textContent = event.message;

    // Severity styling
    cctvSeverityBadge.textContent = event.severity;
    cctvSeverityBadge.className = `badge-sev badge-${event.severity.toLowerCase()}`;
    if (event.severity === 'CRITICAL') {
      cctvEvidencePanel.classList.remove('warning-mode');
    } else {
      cctvEvidencePanel.classList.add('warning-mode');
    }

    // Update video source and play
    if (cctvVideoPlayer.getAttribute('data-current-src') !== videoSrc) {
      cctvVideoPlayer.setAttribute('data-current-src', videoSrc);
      cctvVideoPlayer.src = videoSrc;
      cctvVideoPlayer.load();
    }
    cctvVideoPlayer.play().catch(() => {});

    // Open/Expand Panel
    cctvEvidencePanel.classList.remove('collapsed');
  }

  function hideCctvEvidence() {
    cctvEvidencePanel.classList.add('collapsed');
    cctvVideoPlayer.pause();
  }

  // CCTV Minimize Button
  cctvMinimizeBtn.addEventListener('click', hideCctvEvidence);

  // CCTV Acknowledge & Resolve actions
  cctvAckBtn.addEventListener('click', async () => {
    if (currentCctvEvent) {
      await apiService.acknowledgeEvent(currentCctvEvent.event_id);
      renderAlertList();
      renderPatientCards();
    }
  });

  cctvResolveBtn.addEventListener('click', async () => {
    if (currentCctvEvent) {
      await apiService.resolveEvent(currentCctvEvent.event_id);
      renderAlertList();
      renderPatientCards();
      hideCctvEvidence();
    }
  });

  // Toggle CCTV Toolbar Button
  toggleCctvBtn.addEventListener('click', () => {
    if (cctvEvidencePanel.classList.contains('collapsed')) {
      const patient = apiService.patients.find(p => p.patient_id === selectedPatientId);
      const synthEvent = {
        event_id: `LIVE-${Date.now()}`,
        patient_id: selectedPatientId,
        room_id: patient ? patient.room_id : 'ROOM101',
        event_type: 'SURVEILLANCE_LIVE',
        severity: 'INFO',
        message: `Live bedside optical monitoring feed for ${selectedPatientId}`,
        timestamp: new Date().toISOString()
      };
      showCctvEvidence(synthEvent);
    } else {
      hideCctvEvidence();
    }
  });

  // Stream selected patient's CCTV button
  selPatientCctvBtn.addEventListener('click', () => {
    const patient = apiService.patients.find(p => p.patient_id === selectedPatientId);
    const synthEvent = {
      event_id: `LIVE-${Date.now()}`,
      patient_id: selectedPatientId,
      room_id: patient ? patient.room_id : 'ROOM101',
      event_type: 'BEDSIDE_CCTV',
      severity: patient && patient.status === 'CRITICAL' ? 'CRITICAL' : 'INFO',
      message: `Active CCTV stream for ${patient ? patient.name : selectedPatientId}`,
      timestamp: new Date().toISOString()
    };
    showCctvEvidence(synthEvent);
  });

  // Render Patient Overview Cards (P001 - P004)
  function renderPatientCards() {
    const patients = apiService.patients;
    patientGridEl.innerHTML = '';

    patients.forEach(patient => {
      const isSelected = patient.patient_id === selectedPatientId;
      const card = document.createElement('div');
      card.className = `patient-card status-${patient.status.toLowerCase()} ${isSelected ? 'selected' : ''}`;
      card.dataset.patientId = patient.patient_id;

      let statusClass = 'badge-normal';
      if (patient.status === 'WARNING') statusClass = 'badge-warning';
      if (patient.status === 'CRITICAL') statusClass = 'badge-critical';

      let dripClass = 'drip-normal';
      if (patient.drip_status === 'Low') dripClass = 'drip-low';
      if (patient.drip_status === 'Nearly Finished') dripClass = 'drip-warning';
      if (patient.drip_status === 'Finished') dripClass = 'drip-critical';

      card.innerHTML = `
        <div class="card-header">
          <div>
            <div class="card-room">${patient.room_id}</div>
            <div class="card-id-name">
              <span class="card-pid">${patient.patient_id}</span> • ${patient.name}
            </div>
          </div>
          <div class="card-header-right">
            <span class="patient-status-badge ${statusClass}">${patient.status}</span>
            ${patient.active_alert_count > 0 ? `<span class="alert-counter-badge">${patient.active_alert_count}</span>` : ''}
          </div>
        </div>

        <div class="vitals-mini-grid">
          <div class="mini-vital">
            <span class="mini-label">HR</span>
            <span class="mini-val ${patient.heart_rate > 100 || patient.heart_rate < 55 ? 'val-alert' : ''}">${patient.heart_rate} <span class="unit">bpm</span></span>
          </div>
          <div class="mini-vital">
            <span class="mini-label">SpO2</span>
            <span class="mini-val ${patient.spo2 < 93 ? 'val-alert' : ''}">${patient.spo2}<span class="unit">%</span></span>
          </div>
          <div class="mini-vital">
            <span class="mini-label">BP</span>
            <span class="mini-val">${patient.blood_pressure}</span>
          </div>
          <div class="mini-vital">
            <span class="mini-label">RESP</span>
            <span class="mini-val ${patient.respiratory_rate > 24 ? 'val-alert' : ''}">${patient.respiratory_rate} <span class="unit">rpm</span></span>
          </div>
          <div class="mini-vital">
            <span class="mini-label">TEMP</span>
            <span class="mini-val">${patient.temperature}°C</span>
          </div>
          <div class="mini-vital">
            <span class="mini-label">IV DRIP</span>
            <span class="mini-val ${dripClass}">${patient.drip_status}</span>
          </div>
        </div>

        ${patient.cv_status !== 'Normal in bed' ? `
          <div class="card-cv-alert">
            <span class="cv-alert-icon">👁️</span>
            <span class="cv-alert-text">${patient.cv_status}</span>
          </div>
        ` : ''}
      `;

      card.addEventListener('click', () => {
        selectPatient(patient.patient_id);
      });

      patientGridEl.appendChild(card);
    });
  }

  // Select a patient for the detailed Vital Monitoring panel
  function selectPatient(patientId) {
    selectedPatientId = patientId;
    renderPatientCards();
    updateSelectedPatientView();
  }

  // Update detailed monitoring section for the selected patient
  function updateSelectedPatientView() {
    const patient = apiService.patients.find(p => p.patient_id === selectedPatientId);
    if (!patient) return;

    // Header info
    selPatientName.textContent = `${patient.name} (${patient.age}y, ${patient.gender})`;
    selPatientMeta.textContent = `${patient.patient_id} • ${patient.room_id} • ${patient.condition} • Attending: ${patient.assigned_doctor}`;

    selPatientStatus.className = `patient-status-badge badge-${patient.status.toLowerCase()}`;
    selPatientStatus.textContent = patient.status;

    // Vitals
    selHeartRate.textContent = patient.heart_rate;
    selSpo2.textContent = patient.spo2;
    selBp.textContent = patient.blood_pressure;
    selTemp.textContent = `${patient.temperature}°C`;
    selRespRate.textContent = patient.respiratory_rate;

    // Update ECG rhythm rate
    ecgWaveform.setHeartRate(patient.heart_rate);

    // IV Drip Section
    selDripStatus.textContent = patient.drip_status;
    selDripStatus.className = `drip-val drip-${patient.drip_status.toLowerCase().replace(' ', '-')}`;
    selDripRate.textContent = `${patient.drip_rate} ml/hr`;
    selDripPercent.textContent = `${patient.drip_level}%`;
    selDripFill.style.height = `${patient.drip_level}%`;
    if (patient.drip_level <= 15) {
      selDripFill.style.backgroundColor = '#ff3366';
    } else if (patient.drip_level <= 35) {
      selDripFill.style.backgroundColor = '#ffaa00';
    } else {
      selDripFill.style.backgroundColor = '#00d084';
    }

    // Computer Vision Section
    selCvStatusBadge.textContent = patient.cv_status;
    if (patient.cv_status === 'FALL DETECTED') {
      selCvStatusBadge.className = 'cv-badge badge-cv-critical';
    } else if (patient.cv_status === 'PATIENT LEFT BED' || patient.cv_status === 'UNUSUAL POSITION' || patient.cv_status === 'ABNORMAL MOVEMENT') {
      selCvStatusBadge.className = 'cv-badge badge-cv-warning';
    } else {
      selCvStatusBadge.className = 'cv-badge badge-cv-normal';
    }

    selCvLastCheck.textContent = `Monitored: Feed Active (${new Date().toLocaleTimeString()})`;
  }

  // Render Alert Feed
  function renderAlertList() {
    const alerts = apiService.alerts;
    
    let filtered = alerts;
    if (activeFilter === 'ACTIVE') {
      filtered = alerts.filter(a => a.status === 'ACTIVE' || a.status === 'ACKNOWLEDGED');
    } else if (activeFilter === 'CRITICAL') {
      filtered = alerts.filter(a => a.severity === 'CRITICAL');
    } else if (activeFilter === 'RESOLVED') {
      filtered = alerts.filter(a => a.status === 'RESOLVED');
    }

    const activeCount = alerts.filter(a => a.status === 'ACTIVE' || a.status === 'ACKNOWLEDGED').length;
    alertCountBadge.textContent = `${activeCount} Active`;

    alertListEl.innerHTML = '';
    if (filtered.length === 0) {
      alertListEl.innerHTML = `<div class="empty-alerts">No alerts match the selected filter.</div>`;
      return;
    }

    filtered.forEach(alert => {
      const item = document.createElement('div');
      item.className = `alert-item severity-${alert.severity.toLowerCase()} status-${alert.status.toLowerCase()}`;
      
      const timeStr = new Date(alert.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

      // Action buttons depending on status
      let actionButtons = '';
      if (alert.status === 'ACTIVE') {
        actionButtons = `
          <button class="btn-ack" data-id="${alert.event_id}" title="Acknowledge">Acknowledge</button>
          <button class="btn-resolve" data-id="${alert.event_id}" title="Resolve">Resolve</button>
        `;
      } else if (alert.status === 'ACKNOWLEDGED') {
        actionButtons = `
          <span class="ack-tag">Acknowledged</span>
          <button class="btn-resolve" data-id="${alert.event_id}" title="Resolve">Resolve</button>
        `;
      } else {
        actionButtons = `<span class="resolved-tag">Resolved</span>`;
      }

      // CCTV Evidence Button
      const hasCctv = isCriticalEvent(alert) || alert.video_source || alert.source === 'computer_vision';
      const cctvButton = hasCctv ? `<button class="btn-alert-cctv" data-id="${alert.event_id}">📹 CCTV</button>` : '';

      const isCv = alert.source === 'computer_vision';

      item.innerHTML = `
        <div class="alert-top">
          <div class="alert-meta">
            <span class="badge-sev badge-${alert.severity.toLowerCase()}">${alert.severity}</span>
            <span class="alert-patient-room">${alert.patient_id} • ${alert.room_id}</span>
            <span class="alert-source ${isCv ? 'source-cv' : ''}">
              ${isCv ? '👁️ YOLO CV' : alert.source}
            </span>
          </div>
          <div class="alert-timestamp">${timeStr}</div>
        </div>
        <div class="alert-type">${alert.event_type}</div>
        <div class="alert-msg">${alert.message}</div>
        <div class="alert-actions-bar">
          <span class="alert-status-label">${alert.status}</span>
          <div class="alert-buttons">
            ${cctvButton}
            ${actionButtons}
          </div>
        </div>
      `;

      // Event listeners for action buttons
      const ackBtn = item.querySelector('.btn-ack');
      if (ackBtn) {
        ackBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          ackBtn.disabled = true;
          await apiService.acknowledgeEvent(alert.event_id);
          renderAlertList();
          renderPatientCards();
        });
      }

      const resBtn = item.querySelector('.btn-resolve');
      if (resBtn) {
        resBtn.addEventListener('click', async (e) => {
          e.stopPropagation();
          resBtn.disabled = true;
          await apiService.resolveEvent(alert.event_id);
          renderAlertList();
          renderPatientCards();
        });
      }

      const cctvBtn = item.querySelector('.btn-alert-cctv');
      if (cctvBtn) {
        cctvBtn.addEventListener('click', (e) => {
          e.stopPropagation();
          selectPatient(alert.patient_id);
          showCctvEvidence(alert);
        });
      }

      // Clicking alert selects patient & displays CCTV if critical
      item.addEventListener('click', () => {
        selectPatient(alert.patient_id);
        if (hasCctv) {
          showCctvEvidence(alert);
        }
      });

      alertListEl.appendChild(item);
    });
  }

  // Show prominent Emergency Modal
  function triggerEmergencyAlert(event) {
    currentEmergencyEvent = event;
    emergencyRoom.textContent = `${event.room_id} (${event.patient_id})`;
    emergencyType.textContent = event.event_type.replace(/_/g, ' ');
    emergencyMsg.textContent = event.message;
    emergencyTime.textContent = new Date(event.timestamp).toLocaleTimeString();
    
    emergencyModal.classList.remove('hidden');
    emergencyModal.classList.add('visible');

    // Also auto-select the patient in emergency
    selectPatient(event.patient_id);
  }

  // Emergency Modal Buttons
  emergencyAckBtn.addEventListener('click', async () => {
    if (currentEmergencyEvent) {
      await apiService.acknowledgeEvent(currentEmergencyEvent.event_id);
      renderAlertList();
      renderPatientCards();
    }
    emergencyModal.classList.remove('visible');
    emergencyModal.classList.add('hidden');
  });

  emergencyCloseBtn.addEventListener('click', () => {
    emergencyModal.classList.remove('visible');
    emergencyModal.classList.add('hidden');
  });

  emergencyViewCctvBtn.addEventListener('click', () => {
    emergencyModal.classList.remove('visible');
    emergencyModal.classList.add('hidden');
    if (currentEmergencyEvent) {
      showCctvEvidence(currentEmergencyEvent);
    }
  });

  // Filter Buttons
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeFilter = btn.dataset.filter;
      renderAlertList();
    });
  });

  // Demo Control Bar Triggers
  document.getElementById('demoFallBtn').addEventListener('click', () => {
    const event = apiService.triggerDemoScenario(0); // CV Fall
    if (event) {
      showCctvEvidence(event);
      triggerEmergencyAlert(event);
    }
  });

  document.getElementById('demoLeftBedBtn').addEventListener('click', () => {
    const event = apiService.triggerDemoScenario(1); // CV Left Bed
    if (event) {
      showCctvEvidence(event);
    }
  });

  document.getElementById('demoVentBtn').addEventListener('click', () => {
    const event = apiService.triggerDemoScenario(2); // Ventilator Disconnect
    if (event) {
      showCctvEvidence(event);
      triggerEmergencyAlert(event);
    }
  });

  document.getElementById('demoTachyBtn').addEventListener('click', () => {
    const event = apiService.triggerDemoScenario(3); // Tachycardia
    if (event) {
      showCctvEvidence(event);
      triggerEmergencyAlert(event);
    }
  });

  document.getElementById('demoCvPosBtn').addEventListener('click', () => {
    const event = apiService.triggerDemoScenario(4); // CV Unusual Position
    if (event) {
      showCctvEvidence(event);
    }
  });

  // Auto-simulation toggle
  const simToggleBtn = document.getElementById('toggleSimBtn');
  simToggleBtn.addEventListener('click', () => {
    autoSimEnabled = !autoSimEnabled;
    if (autoSimEnabled) {
      apiService.startMockSimulation();
      simToggleBtn.textContent = 'Auto-Sim: ON';
      simToggleBtn.className = 'btn-control btn-active';
    } else {
      apiService.stopMockSimulation();
      simToggleBtn.textContent = 'Auto-Sim: OFF';
      simToggleBtn.className = 'btn-control';
    }
  });

  // Event Listeners from ApiService
  apiService.on('eventReceived', (event) => {
    renderAlertList();
    renderPatientCards();
    updateSelectedPatientView();

    // Critical events automatically open CCTV evidence panel!
    if (isCriticalEvent(event)) {
      showCctvEvidence(event);
      triggerEmergencyAlert(event);
    }
  });

  apiService.on('patientUpdated', () => {
    renderPatientCards();
    updateSelectedPatientView();
  });

  apiService.on('connectionChanged', (status) => {
    updateConnectionUI(status);
  });

  // Initial Load
  async function init() {
    ecgWaveform.start();
    await apiService.getPatients();
    await apiService.getEvents();
    renderPatientCards();
    updateSelectedPatientView();
    renderAlertList();

    // Start background WebSocket client
    apiService.initWebSocket();

    // Start mock simulation as fallback
    apiService.startMockSimulation();
  }

  init();
});
