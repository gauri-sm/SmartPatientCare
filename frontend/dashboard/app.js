/**
 * SmartPatientCare — Nursing Station Console Controller
 * 
 * Disclaimer:
 * Prototype for hackathon demonstration only. Not medically validated and not
 * intended for clinical decision-making.
 */

// Application State
const state = {
  patients: [],
  alerts: [],
  stats: {},
  activeFilter: 'ACTIVE',
  selectedPatientId: null,
  wsConnected: false,
  soundEnabled: true,
  audioCtx: null,
};

// DOM References
const elements = {
  clockDisplay: document.getElementById('clockDisplay'),
  connectionPill: document.getElementById('connectionPill'),
  connectionLabel: document.getElementById('connectionLabel'),
  soundToggleBtn: document.getElementById('soundToggleBtn'),
  soundIcon: document.getElementById('soundIcon'),
  refreshBtn: document.getElementById('refreshBtn'),
  targetPatientSelect: document.getElementById('targetPatientSelect'),

  // KPIs
  valTotalPatients: document.getElementById('valTotalPatients'),
  valStablePatients: document.getElementById('valStablePatients'),
  valAttentionPatients: document.getElementById('valAttentionPatients'),
  valCriticalAlerts: document.getElementById('valCriticalAlerts'),
  valLastSync: document.getElementById('valLastSync'),

  // Containers
  patientCardsGrid: document.getElementById('patientCardsGrid'),
  alertsList: document.getElementById('alertsList'),
  patientSectionCount: document.getElementById('patientSectionCount'),

  // Modal
  patientModal: document.getElementById('patientModal'),
  closeModalBtn: document.getElementById('closeModalBtn'),
  modalDoneBtn: document.getElementById('modalDoneBtn'),
  modalPatientName: document.getElementById('modalPatientName'),
  modalDemographics: document.getElementById('modalDemographics'),
  modalRoomTag: document.getElementById('modalRoomTag'),
  modalPatientId: document.getElementById('modalPatientId'),
  modalDoctor: document.getElementById('modalDoctor'),
  modalNurse: document.getElementById('modalNurse'),
  modalStatusBadge: document.getElementById('modalStatusBadge'),
  modalDevicesList: document.getElementById('modalDevicesList'),
  modalVitalsGrid: document.getElementById('modalVitalsGrid'),
  modalEcgTag: document.getElementById('modalEcgTag'),
  ecgCanvas: document.getElementById('ecgCanvas'),
  trendCanvas: document.getElementById('trendCanvas'),
  modalDripPanel: document.getElementById('modalDripPanel'),
  modalDripBar: document.getElementById('modalDripBar'),
  modalDripVolume: document.getElementById('modalDripVolume'),
  modalDripRate: document.getElementById('modalDripRate'),
  modalDripEstTime: document.getElementById('modalDripEstTime'),
  modalDripStatusTag: document.getElementById('modalDripStatusTag'),
  modalAlertHistory: document.getElementById('modalAlertHistory'),

  // Modal Quick Actions
  quickTriggerSpO2: document.getElementById('quickTriggerSpO2'),
  quickTriggerDrip: document.getElementById('quickTriggerDrip'),
  quickTriggerNormal: document.getElementById('quickTriggerNormal'),
};

// 1. Audio Notification Synthesizer (Web Audio API)
function playAlertBeep(isCritical = false) {
  if (!state.soundEnabled) return;
  try {
    if (!state.audioCtx) {
      state.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    const ctx = state.audioCtx;
    if (ctx.state === 'suspended') {
      ctx.resume();
    }
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = isCritical ? 'sawtooth' : 'sine';
    osc.frequency.setValueAtTime(isCritical ? 880 : 440, ctx.currentTime);
    gain.gain.setValueAtTime(0.08, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + (isCritical ? 0.4 : 0.2));
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + (isCritical ? 0.4 : 0.2));
  } catch (e) {
    // Ignore audio permission errors
  }
}

// 2. Real-Time Station Clock
function updateClock() {
  const now = new Date();
  const timeStr = now.toISOString().substring(11, 19) + ' UTC';
  if (elements.clockDisplay) {
    elements.clockDisplay.textContent = timeStr;
  }
}
setInterval(updateClock, 1000);
updateClock();

// 3. Data Fetching & Sync
async function fetchSnapshot() {
  try {
    const [pRes, aRes, sRes] = await Promise.all([
      fetch('/api/patients'),
      fetch('/api/alerts'),
      fetch('/api/stats'),
    ]);

    if (pRes.ok) state.patients = await pRes.json();
    if (aRes.ok) state.alerts = await aRes.json();
    if (sRes.ok) state.stats = await sRes.json();

    renderDashboard();
    if (state.selectedPatientId) {
      updateModalContent(state.selectedPatientId);
    }
  } catch (err) {
    console.warn('Sync error:', err);
  }
}

// 4. WebSocket Initialization
let ws = null;
function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  try {
    ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      state.wsConnected = true;
      elements.connectionPill.innerHTML = '<span class="status-dot online"></span><span>LIVE TELEMETRY</span>';
      elements.connectionPill.className = 'connection-pill';
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'SNAPSHOT') {
          state.patients = data.patients || [];
          state.alerts = data.alerts || [];
          state.stats = data.stats || {};
          renderDashboard();
          if (state.selectedPatientId) {
            updateModalContent(state.selectedPatientId);
          }
        }
      } catch (err) {
        console.warn('WS message parse error:', err);
      }
    };

    ws.onclose = () => {
      state.wsConnected = false;
      elements.connectionPill.innerHTML = '<span class="status-dot offline"></span><span>POLLING FALLBACK</span>';
      setTimeout(initWebSocket, 3000);
    };

    ws.onerror = () => {
      ws.close();
    };
  } catch (e) {
    console.warn('WS connection failed, falling back to polling.');
  }
}

// Fallback polling interval every 2.5 seconds
setInterval(fetchSnapshot, 2500);

// 5. Render KPIs
function renderKPIs() {
  const s = state.stats;
  elements.valTotalPatients.textContent = s.total_patients ?? state.patients.length;
  elements.valStablePatients.textContent = s.stable_patients ?? 0;
  elements.valAttentionPatients.textContent = s.attention_patients ?? 0;
  elements.valCriticalAlerts.textContent = s.active_critical_alerts ?? 0;

  const now = new Date();
  elements.valLastSync.textContent = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  // Critical pulse style on KPI card if alerts > 0
  const kpiCrit = document.getElementById('kpiCritical');
  if (s.active_critical_alerts > 0) {
    kpiCrit.style.borderColor = '#ef4444';
    kpiCrit.style.backgroundColor = 'rgba(239, 68, 68, 0.12)';
  } else {
    kpiCrit.style.borderColor = '';
    kpiCrit.style.backgroundColor = '';
  }
}

// 6. Render Patient Monitoring Cards
function renderPatientCards() {
  if (!elements.patientCardsGrid) return;

  if (state.patients.length === 0) {
    elements.patientCardsGrid.innerHTML = '<div class="empty-alerts-placeholder">Connecting to telemetry network...</div>';
    return;
  }

  elements.patientSectionCount.textContent = `${state.patients.length} Beds Active`;

  elements.patientCardsGrid.innerHTML = state.patients.map((p) => {
    const v = p.vitals || {};
    const drip = p.iv_drip || {};
    const ecg = p.ecg || {};
    const hasCrit = (p.active_alerts || []).some(a => a.severity === 'CRITICAL');
    const hasWarn = (p.active_alerts || []).some(a => a.severity === 'WARNING');

    let cardClass = 'patient-card';
    if (hasCrit) cardClass += ' critical-state';
    else if (hasWarn) cardClass += ' warning-state';

    let statusClass = 'status-badge';
    const st = (p.status || 'Stable').toLowerCase();
    if (st === 'critical' || hasCrit) statusClass += ' critical';
    else if (st === 'attention' || hasWarn) statusClass += ' attention';
    else if (st === 'observation') statusClass += ' observation';
    else statusClass += ' stable';

    // Highlight abnormalities
    const hrClass = (v.heart_rate > 120 || v.heart_rate < 50) ? (v.heart_rate > 140 || v.heart_rate < 45 ? 'abnormal-critical' : 'abnormal-warning') : '';
    const spo2Class = (v.spo2 < 95) ? (v.spo2 < 90 ? 'abnormal-critical' : 'abnormal-warning') : '';
    const bpClass = (v.systolic_bp >= 140 || v.systolic_bp <= 85) ? (v.systolic_bp >= 180 ? 'abnormal-critical' : 'abnormal-warning') : '';
    const tempClass = (v.temperature >= 38.0 || v.temperature <= 35.5) ? (v.temperature >= 39.0 ? 'abnormal-critical' : 'abnormal-warning') : '';
    const rrClass = (v.respiratory_rate >= 22 || v.respiratory_rate <= 10) ? 'abnormal-warning' : '';

    // Drip mini bar width & class
    const dripPct = Math.min(100, Math.max(0, (drip.volume_remaining_ml / 500) * 100));
    let dripFillClass = 'drip-mini-fill';
    if (drip.volume_remaining_ml <= 25) dripFillClass += ' empty';
    else if (drip.volume_remaining_ml <= 100) dripFillClass += ' low';

    const ecgBadgeColor = (ecg.status === 'CRITICAL') ? '#ef4444' : (ecg.status === 'WARNING' ? '#f59e0b' : '#10b981');

    return `
      <div class="${cardClass}" data-patient-id="${p.patient_id}">
        <div class="card-top">
          <div class="patient-name-wrap">
            <span class="room-badge">${p.room_id}</span>
            <h3>${p.name}</h3>
            <span class="patient-subtitle">${p.age}y • ${p.gender} • ${p.condition}</span>
          </div>
          <span class="${statusClass}">${hasCrit ? 'CRITICAL' : (hasWarn ? 'ATTENTION' : p.status)}</span>
        </div>

        <div class="card-vitals-grid">
          <div class="vital-cell ${hrClass}">
            <span class="vital-label">HR</span>
            <div class="vital-value-wrap">
              <span class="vital-val">${v.heart_rate ? Math.round(v.heart_rate) : '--'}</span>
              <span class="vital-unit">bpm</span>
            </div>
          </div>

          <div class="vital-cell ${spo2Class}">
            <span class="vital-label">SpO2</span>
            <div class="vital-value-wrap">
              <span class="vital-val">${v.spo2 ? Math.round(v.spo2) : '--'}</span>
              <span class="vital-unit">%</span>
            </div>
          </div>

          <div class="vital-cell ${bpClass}">
            <span class="vital-label">BP</span>
            <div class="vital-value-wrap">
              <span class="vital-val">${v.blood_pressure || '--/--'}</span>
              <span class="vital-unit">mmHg</span>
            </div>
          </div>

          <div class="vital-cell ${tempClass}">
            <span class="vital-label">TEMP</span>
            <div class="vital-value-wrap">
              <span class="vital-val">${v.temperature ? v.temperature.toFixed(1) : '--'}</span>
              <span class="vital-unit">°C</span>
            </div>
          </div>

          <div class="vital-cell ${rrClass}">
            <span class="vital-label">RR</span>
            <div class="vital-value-wrap">
              <span class="vital-val">${v.respiratory_rate ? Math.round(v.respiratory_rate) : '--'}</span>
              <span class="vital-unit">/min</span>
            </div>
          </div>

          <div class="vital-cell">
            <span class="vital-label">ALERT COUNT</span>
            <div class="vital-value-wrap">
              <span class="vital-val" style="color: ${hasCrit ? '#ef4444' : (hasWarn ? '#f59e0b' : '#64748b')}">${(p.active_alerts || []).length}</span>
              <span class="vital-unit">active</span>
            </div>
          </div>
        </div>

        <div class="card-devices-strip">
          <div class="device-indicator" title="IV Infusion Reservoir">
            <span>💧 IV: <strong>${Math.round(drip.volume_remaining_ml || 0)}ml</strong></span>
            <div class="drip-mini-bar"><div class="${dripFillClass}" style="width: ${dripPct}%"></div></div>
          </div>
          <div class="device-indicator" title="Bedside ECG Rhythm">
            <span>ECG: <strong style="color: ${ecgBadgeColor}">${(ecg.rhythm || 'SINUS').replace(/_/g, ' ')}</strong></span>
          </div>
        </div>

        <div class="card-footer-actions">
          <span class="last-update-time">Doc: ${p.assigned_doctor || 'Staff'}</span>
          <button class="view-details-btn" onclick="openPatientModal('${p.patient_id}')">Patient Dossier →</button>
        </div>
      </div>
    `;
  }).join('');
}

// 7. Render Alerts Priority Queue (Right Column)
function renderAlertsList() {
  if (!elements.alertsList) return;

  let filtered = state.alerts;
  if (state.activeFilter !== 'ALL') {
    filtered = state.alerts.filter(a => a.status === state.activeFilter);
  }

  if (filtered.length === 0) {
    elements.alertsList.innerHTML = `
      <div class="empty-alerts-placeholder">
        <span>✓ No ${state.activeFilter.toLowerCase()} alerts in station queue</span>
      </div>
    `;
    return;
  }

  elements.alertsList.innerHTML = filtered.map((a) => {
    const sev = a.severity.toLowerCase();
    const timeAgo = formatTimestamp(a.created_at);

    return `
      <div class="alert-card ${sev} ${a.status.toLowerCase()}" id="alert-${a.alert_id}">
        <div class="alert-card-top">
          <span class="alert-severity-badge ${sev}">${a.severity}</span>
          <span class="alert-time">${timeAgo}</span>
        </div>

        <div class="alert-patient-room">
          ${a.patient_name} <span style="color: #38bdf8; font-size: 11px;">(${a.room_id})</span>
        </div>

        <div class="alert-message">${a.message}</div>

        ${a.camera_id || a.video_source ? `
          <div class="cctv-evidence-badge">
            <span>📹 ${a.camera_id ? a.camera_id : 'CCTV'}</span>
            ${a.video_source ? `<span>• ${a.video_source}</span>` : ''}
          </div>
        ` : ''}

        <div class="alert-meta-details">
          <span>Observed: <strong>${a.value} ${a.unit}</strong></span>
          <span>Expected: <strong>${a.expected_range}</strong></span>
        </div>

        ${a.status === 'ACTIVE' ? `
          <div class="alert-actions">
            <button class="alert-btn ack" onclick="acknowledgeAlert('${a.alert_id}')">✓ Acknowledge</button>
            <button class="alert-btn res" onclick="resolveAlert('${a.alert_id}')">Resolve</button>
          </div>
        ` : a.status === 'ACKNOWLEDGED' ? `
          <div class="alert-actions">
            <span style="font-size: 11px; color: #94a3b8; align-self: center;">Ack by: ${a.acknowledged_by || 'Nurse'}</span>
            <button class="alert-btn res" onclick="resolveAlert('${a.alert_id}')">Resolve</button>
          </div>
        ` : `
          <div style="font-size: 11px; color: #10b981; margin-top: 4px;">Resolved: ${a.resolution_note || 'Stabilized'}</div>
        `}
      </div>
    `;
  }).join('');
}

function formatTimestamp(isoStr) {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch (e) {
    return isoStr;
  }
}

// 8. Master Render Function
function renderDashboard() {
  renderKPIs();
  renderPatientCards();
  renderAlertsList();
}

// 9. Alert Actions
async function acknowledgeAlert(alertId) {
  try {
    const res = await fetch(`/api/alerts/${alertId}/acknowledge`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nurse_id: 'Nurse Station' }),
    });
    if (res.ok) {
      await fetchSnapshot();
    }
  } catch (e) {
    console.error('Failed to acknowledge alert:', e);
  }
}

async function resolveAlert(alertId) {
  try {
    const res = await fetch(`/api/alerts/${alertId}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ resolution_note: 'Verified & stabilized by clinical nurse' }),
    });
    if (res.ok) {
      await fetchSnapshot();
    }
  } catch (e) {
    console.error('Failed to resolve alert:', e);
  }
}

// 10. Simulation Scenario Runner
async function triggerScenario(scenarioId) {
  const patientSelect = elements.targetPatientSelect;
  const targetPatient = patientSelect ? patientSelect.value : '';
  const url = targetPatient
    ? `/api/simulate/${scenarioId}?patient_id=${targetPatient}`
    : `/api/simulate/${scenarioId}`;

  try {
    const res = await fetch(url, { method: 'POST' });
    const data = await res.json();
    playAlertBeep(scenarioId.includes('CRISIS') || scenarioId.includes('CRITICAL') || scenarioId.includes('SPO2') || scenarioId.includes('HEART') || scenarioId.includes('ARRHYTHMIA'));
    await fetchSnapshot();
  } catch (e) {
    console.error('Failed to trigger scenario:', e);
  }
}

// 11. Patient Detail Modal Logic
function openPatientModal(patientId) {
  state.selectedPatientId = patientId;
  updateModalContent(patientId);
  elements.patientModal.style.display = 'flex';
  startEcgWaveformAnimation();
}

function closePatientModal() {
  elements.patientModal.style.display = 'none';
  state.selectedPatientId = null;
  stopEcgWaveformAnimation();
}

function updateModalContent(patientId) {
  const p = state.patients.find(item => item.patient_id === patientId);
  if (!p) return;

  elements.modalRoomTag.textContent = p.room_id;
  elements.modalPatientName.textContent = p.name;
  elements.modalDemographics.textContent = `${p.age} years • ${p.gender} • Admitted: ${p.admission_date ? p.admission_date.substring(0, 10) : ''}`;
  elements.modalPatientId.textContent = p.patient_id;
  elements.modalDoctor.textContent = p.assigned_doctor;
  elements.modalNurse.textContent = p.assigned_nurse;

  elements.modalStatusBadge.textContent = p.status;
  elements.modalStatusBadge.className = `status-badge ${p.status.toLowerCase()}`;

  // Connected Devices
  elements.modalDevicesList.innerHTML = (p.devices_connected || []).map(d => `<span class="device-chip">${d.replace(/_/g, ' ')}</span>`).join('');

  // High-Res Vitals
  const v = p.vitals || {};
  elements.modalVitalsGrid.innerHTML = `
    <div class="modal-vital-box">
      <span class="modal-vital-label">HEART RATE</span>
      <span class="modal-vital-val" style="color: ${v.heart_rate > 100 || v.heart_rate < 60 ? '#f59e0b' : '#10b981'}">${v.heart_rate ? Math.round(v.heart_rate) : '--'} bpm</span>
      <span class="modal-vital-range">Expected: 60 - 100 bpm</span>
    </div>
    <div class="modal-vital-box">
      <span class="modal-vital-label">OXYGEN SAT (SpO2)</span>
      <span class="modal-vital-val" style="color: ${v.spo2 < 95 ? '#ef4444' : '#10b981'}">${v.spo2 ? Math.round(v.spo2) : '--'}%</span>
      <span class="modal-vital-range">Expected: ≥ 95%</span>
    </div>
    <div class="modal-vital-box">
      <span class="modal-vital-label">BLOOD PRESSURE</span>
      <span class="modal-vital-val" style="color: ${v.systolic_bp >= 140 ? '#ef4444' : '#10b981'}">${v.blood_pressure || '--/--'}</span>
      <span class="modal-vital-range">Expected: 90-120 / 60-80 mmHg</span>
    </div>
    <div class="modal-vital-box">
      <span class="modal-vital-label">TEMPERATURE</span>
      <span class="modal-vital-val" style="color: ${v.temperature >= 38 ? '#ef4444' : '#10b981'}">${v.temperature ? v.temperature.toFixed(1) : '--'} °C</span>
      <span class="modal-vital-range">Expected: 36.5 - 37.5 °C</span>
    </div>
    <div class="modal-vital-box">
      <span class="modal-vital-label">RESPIRATION</span>
      <span class="modal-vital-val">${v.respiratory_rate ? Math.round(v.respiratory_rate) : '--'} /min</span>
      <span class="modal-vital-range">Expected: 12 - 20 /min</span>
    </div>
  `;

  // ECG Status
  const ecg = p.ecg || {};
  elements.modalEcgTag.textContent = (ecg.rhythm || 'NORMAL SINUS RHYTHM').replace(/_/g, ' ');
  elements.modalEcgTag.style.color = (ecg.status === 'CRITICAL') ? '#ef4444' : (ecg.status === 'WARNING' ? '#f59e0b' : '#10b981');

  // IV Drip Panel
  const drip = p.iv_drip || {};
  const dripVol = drip.volume_remaining_ml ?? 0;
  const dripRate = drip.flow_rate_ml_h ?? 100;
  const dripPct = Math.min(100, Math.max(0, (dripVol / 500) * 100));

  elements.modalDripBar.style.width = `${dripPct}%`;
  elements.modalDripVolume.textContent = `${Math.round(dripVol)} ml`;
  elements.modalDripRate.textContent = `${Math.round(dripRate)} ml/h`;

  const estHours = dripRate > 0 ? (dripVol / dripRate).toFixed(1) : '0';
  elements.modalDripEstTime.textContent = dripRate > 0 ? `~${estHours} hrs` : 'Flow halted';

  if (dripVol <= 10) {
    elements.modalDripStatusTag.textContent = 'DEPLETED / EMPTY';
    elements.modalDripStatusTag.style.color = '#ef4444';
    elements.modalDripBar.style.backgroundColor = '#ef4444';
  } else if (dripVol <= 100) {
    elements.modalDripStatusTag.textContent = 'LOW RESERVOIR';
    elements.modalDripStatusTag.style.color = '#f59e0b';
    elements.modalDripBar.style.backgroundColor = '#f59e0b';
  } else {
    elements.modalDripStatusTag.textContent = 'ADEQUATE INFUSION';
    elements.modalDripStatusTag.style.color = '#10b981';
    elements.modalDripBar.style.backgroundColor = '#38bdf8';
  }

  // Patient Alerts History
  const patientAlerts = state.alerts.filter(a => a.patient_id === patientId);
  if (patientAlerts.length === 0) {
    elements.modalAlertHistory.innerHTML = '<div class="empty-alerts-placeholder">No alerts recorded for this patient.</div>';
  } else {
    elements.modalAlertHistory.innerHTML = patientAlerts.map(a => `
      <div class="alert-card ${a.severity.toLowerCase()} ${a.status.toLowerCase()}">
        <div class="alert-card-top">
          <span class="alert-severity-badge ${a.severity.toLowerCase()}">${a.severity}</span>
          <span class="alert-time">${formatTimestamp(a.created_at)}</span>
        </div>
        <div class="alert-message">${a.message}</div>
        ${a.camera_id || a.video_source ? `
          <div class="cctv-evidence-badge">
            <span>📹 ${a.camera_id ? a.camera_id : 'CCTV'}</span>
            ${a.video_source ? `<span>• ${a.video_source}</span>` : ''}
          </div>
        ` : ''}
        <div class="alert-meta-details">
          <span>Status: <strong>${a.status}</strong></span>
          <span>Parameter: <strong>${a.parameter} (${a.value} ${a.unit})</strong></span>
        </div>
      </div>
    `).join('');
  }

  drawTrendGraph(v);
}

// 12. Dynamic ECG Canvas Waveform Simulation
let ecgAnimationId = null;
let ecgOffset = 0;

function startEcgWaveformAnimation() {
  if (ecgAnimationId) cancelAnimationFrame(ecgAnimationId);

  const canvas = elements.ecgCanvas;
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  function renderFrame() {
    const width = canvas.width;
    const height = canvas.height;
    ctx.fillStyle = '#060911';
    ctx.fillRect(0, 0, width, height);

    // Draw grid lines
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 1;
    for (let x = 0; x < width; x += 25) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
      ctx.stroke();
    }
    for (let y = 0; y < height; y += 25) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    const currentP = state.patients.find(p => p.patient_id === state.selectedPatientId);
    const rhythm = currentP && currentP.ecg ? currentP.ecg.rhythm : 'NORMAL_SINUS_RHYTHM';
    const isVfib = rhythm === 'VENTRICULAR_FIBRILLATION';

    ctx.strokeStyle = isVfib ? '#ef4444' : '#10b981';
    ctx.lineWidth = 2;
    ctx.beginPath();

    const midY = height / 2;
    for (let x = 0; x < width; x++) {
      let y = midY;
      const phase = (x + ecgOffset) % 150;

      if (isVfib) {
        // Chaotic fibrillation waveform
        const t = (x + ecgOffset) * 0.15;
        y = midY + Math.sin(t * 1.7) * 25 + Math.cos(t * 3.1) * 15 + (Math.random() - 0.5) * 8;
      } else {
        // Standard P-QRS-T complex
        if (phase >= 20 && phase <= 40) {
          // P Wave
          y = midY - Math.sin(((phase - 20) / 20) * Math.PI) * 8;
        } else if (phase >= 55 && phase <= 58) {
          // Q drop
          y = midY + 6;
        } else if (phase >= 59 && phase <= 65) {
          // R spike
          y = midY - 42;
        } else if (phase >= 66 && phase <= 70) {
          // S drop
          y = midY + 12;
        } else if (phase >= 90 && phase <= 120) {
          // T Wave
          y = midY - Math.sin(((phase - 90) / 30) * Math.PI) * 14;
        }
      }

      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    ecgOffset = (ecgOffset + 2) % 3000;
    ecgAnimationId = requestAnimationFrame(renderFrame);
  }

  renderFrame();
}

function stopEcgWaveformAnimation() {
  if (ecgAnimationId) {
    cancelAnimationFrame(ecgAnimationId);
    ecgAnimationId = null;
  }
}

// 13. Trend Graph
function drawTrendGraph(vitals) {
  const canvas = elements.trendCanvas;
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const width = canvas.width;
  const height = canvas.height;

  ctx.fillStyle = '#060911';
  ctx.fillRect(0, 0, width, height);

  // Sparkline of HR trend
  ctx.strokeStyle = '#38bdf8';
  ctx.lineWidth = 2;
  ctx.beginPath();
  const points = 20;
  const hrBase = vitals.heart_rate || 75;

  for (let i = 0; i < points; i++) {
    const x = (i / (points - 1)) * width;
    const jitter = Math.sin(i * 0.8) * 6 + ((i === points - 1) ? 0 : (Math.random() - 0.5) * 4);
    const normalizedY = (hrBase + jitter - 40) / 140; // range 40 - 180
    const y = height - (normalizedY * height * 0.7 + 15);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();

  // Label
  ctx.fillStyle = '#94a3b8';
  ctx.font = '10px Inter';
  ctx.fillText(`Current: ${Math.round(hrBase)} bpm`, 10, 15);
}

// 14. Event Listeners Setup
function setupEventListeners() {
  // Scenario Buttons
  document.querySelectorAll('.sim-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const scenario = btn.getAttribute('data-scenario');
      if (scenario) triggerScenario(scenario);
    });
  });

  // Filter Pills
  document.querySelectorAll('.filter-pill').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      state.activeFilter = pill.getAttribute('data-filter');
      renderAlertsList();
    });
  });

  // Refresh Button
  if (elements.refreshBtn) {
    elements.refreshBtn.addEventListener('click', () => {
      fetchSnapshot();
    });
  }

  // Sound Toggle
  if (elements.soundToggleBtn) {
    elements.soundToggleBtn.addEventListener('click', () => {
      state.soundEnabled = !state.soundEnabled;
      elements.soundIcon.textContent = state.soundEnabled ? '🔔' : '🔕';
    });
  }

  // Modal Close
  if (elements.closeModalBtn) elements.closeModalBtn.addEventListener('click', closePatientModal);
  if (elements.modalDoneBtn) elements.modalDoneBtn.addEventListener('click', closePatientModal);
  if (elements.patientModal) {
    elements.patientModal.addEventListener('click', (e) => {
      if (e.target === elements.patientModal) closePatientModal();
    });
  }

  // Modal Quick Triggers
  if (elements.quickTriggerSpO2) {
    elements.quickTriggerSpO2.addEventListener('click', () => {
      if (state.selectedPatientId) {
        fetch(`/api/simulate/LOW_SPO2?patient_id=${state.selectedPatientId}`, { method: 'POST' }).then(() => fetchSnapshot());
      }
    });
  }
  if (elements.quickTriggerDrip) {
    elements.quickTriggerDrip.addEventListener('click', () => {
      if (state.selectedPatientId) {
        fetch(`/api/simulate/DRIP_LOW?patient_id=${state.selectedPatientId}`, { method: 'POST' }).then(() => fetchSnapshot());
      }
    });
  }
  if (elements.quickTriggerNormal) {
    elements.quickTriggerNormal.addEventListener('click', () => {
      if (state.selectedPatientId) {
        fetch(`/api/simulate/NORMAL_BASELINE?patient_id=${state.selectedPatientId}`, { method: 'POST' }).then(() => fetchSnapshot());
      }
    });
  }
}

// Global scope helpers for HTML onclick
window.openPatientModal = openPatientModal;
window.acknowledgeAlert = acknowledgeAlert;
window.resolveAlert = resolveAlert;

// Initialize on Load
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  fetchSnapshot();
  initWebSocket();
});
