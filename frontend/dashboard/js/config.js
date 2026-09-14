/**
 * SmartPatientCare - Frontend Configuration
 * Author: Gauri (Frontend & CV Lead)
 * 
 * Provides centralized backend URL and endpoints with graceful fallback.
 */

const CONFIG = {
  // Backend base URL (can be customized via window.ENV_BACKEND_URL if set in container/deployment)
  BACKEND_URL: (typeof window !== 'undefined' && window.ENV_BACKEND_URL) || 'http://localhost:8000',

  // REST API Endpoints
  API_ENDPOINTS: {
    PATIENTS: '/api/patients',
    PATIENT_BY_ID: (id) => `/api/patients/${id}`,
    EVENTS: '/api/events',
    ACTIVE_EVENTS: '/api/events/active',
    ACKNOWLEDGE_EVENT: (id) => `/api/events/${id}/acknowledge`,
    RESOLVE_EVENT: (id) => `/api/events/${id}/resolve`,
  },

  // WebSocket Endpoint for Real-time Alerts
  WS_ENDPOINT: '/ws/alerts',

  // Mock simulation settings
  MOCK_MODE: {
    // If backend is unreachable, automatically fall back to mock engine
    AUTO_FALLBACK: true,
    // Interval for generating simulated telemetry/alerts if WebSocket is disconnected (ms)
    SIMULATION_INTERVAL_MS: 12000,
    // Vitals fluctuation interval (ms)
    VITALS_TICK_MS: 3000,
  },

  // Severity definitions
  SEVERITY: {
    INFO: 'INFO',
    WARNING: 'WARNING',
    CRITICAL: 'CRITICAL',
  },

  // Event Lifecycle Statuses
  STATUS: {
    ACTIVE: 'ACTIVE',
    ACKNOWLEDGED: 'ACKNOWLEDGED',
    RESOLVED: 'RESOLVED',
  }
};

if (typeof module !== 'undefined' && module.exports) {
  module.exports = CONFIG;
}
