"""
API Routes for SmartPatientCare Backend
======================================
Provides endpoints for patients, alerts, telemetry, and scenario simulation.

Disclaimer:
Prototype for hackathon demonstration only. Not medically validated and not
intended for clinical decision-making.
"""

from fastapi import APIRouter, HTTPException, Query, Body
from typing import Optional, Dict, Any, List
from backend.services.patient_service import PatientService

router = APIRouter(prefix="/api", tags=["SmartPatientCare"])

# Service will be injected or initialized
patient_service = PatientService()


@router.get("/health")
def health_check():
    return {
        "status": "HEALTHY",
        "service": "SmartPatientCare Nursing Station Backend",
        "version": "1.0.0",
        "disclaimer": "Prototype for hackathon demonstration only. Not medically validated.",
    }


@router.get("/stats")
def get_stats():
    """
    Returns dashboard summary statistics (total patients, stable, attention, critical alerts).
    """
    return patient_service.get_station_stats()


@router.get("/patients")
def get_all_patients():
    """
    Returns all monitored patients with real-time vitals and connected devices.
    """
    return patient_service.get_all_patients()


@router.get("/patients/{patient_id}")
def get_patient(patient_id: str):
    """
    Returns detailed patient monitoring record and alert history.
    """
    p = patient_service.get_patient(patient_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return p


@router.get("/alerts")
def get_alerts(
    status: Optional[str] = Query(None, description="ACTIVE, ACKNOWLEDGED, RESOLVED"),
    patient_id: Optional[str] = Query(None, description="Patient ID filter"),
    severity: Optional[str] = Query(None, description="INFO, WARNING, CRITICAL"),
):
    """
    Returns prioritized list of alerts.
    """
    return patient_service.get_alerts(status=status, patient_id=patient_id, severity=severity)


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    payload: Dict[str, str] = Body(default={"nurse_id": "Nurse On Duty"}),
):
    """
    Nurse acknowledges an active alert.
    """
    nurse = payload.get("nurse_id", "Nurse On Duty")
    alert = patient_service.acknowledge_alert(alert_id, acknowledged_by=nurse)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found or already acknowledged")
    return alert


@router.post("/alerts/{alert_id}/resolve")
def resolve_alert(
    alert_id: str,
    payload: Dict[str, str] = Body(default={"resolution_note": "Condition stabilized"}),
):
    """
    Nurse resolves an alert after clinical intervention.
    """
    note = payload.get("resolution_note", "Condition stabilized")
    alert = patient_service.resolve_alert(alert_id, note=note)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    return alert


@router.get("/scenarios")
def get_available_scenarios():
    """
    Returns the list of hackathon demonstration scenarios.
    """
    return patient_service.scenario_runner.get_available_scenarios()


@router.post("/simulate/{scenario_id}")
def trigger_scenario(
    scenario_id: str,
    patient_id: Optional[str] = Query(None, description="Optional target patient ID"),
):
    """
    Triggers an emergency simulation scenario, feeding telemetry through the alert engine.
    """
    try:
        result = patient_service.execute_scenario(scenario_id, patient_id=patient_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/events")
def ingest_event(event: Dict[str, Any]):
    """
    Ingests an external event (e.g. from CV fall detection, physical sensors, or emergency button),
    normalizing via Sandra's RulesEngine and routing through the centralized Priority Alert Manager.
    """
    try:
        alert = patient_service.ingest_event(event)
        return {"status": "SUCCESS", "event": alert, "alert": alert}
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid event schema: {str(e)}")


@router.get("/events")
def get_all_events(
    status: Optional[str] = Query(None, description="ACTIVE, ACKNOWLEDGED, RESOLVED"),
    patient_id: Optional[str] = Query(None, description="Patient ID filter"),
    severity: Optional[str] = Query(None, description="CRITICAL, HIGH, WARNING, MEDIUM, LOW, INFO"),
):
    """
    Returns all centralized events and alerts from Sandra's priority queue.
    """
    return patient_service.get_alerts(status=status, patient_id=patient_id, severity=severity)


@router.get("/events/active")
def get_active_events(
    patient_id: Optional[str] = Query(None, description="Patient ID filter"),
    severity: Optional[str] = Query(None, description="CRITICAL, HIGH, WARNING, MEDIUM, LOW, INFO"),
):
    """
    Returns currently active events and alerts from Sandra's priority queue.
    """
    return patient_service.get_alerts(status="ACTIVE", patient_id=patient_id, severity=severity)
