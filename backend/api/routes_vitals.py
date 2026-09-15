"""REST API endpoints for patient vitals data and trends."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.models.db_models import PatientDB, VitalsReadingDB
from backend.models.schemas import ECGWaveformResponse
from backend.services.event_service import EventService
from melisa.patient_device_monitoring.src.ecg_analyzer import ECGAnalyzer

router = APIRouter(prefix="/api/vitals", tags=["Vitals"])



@router.get("/latest/{patient_id}")
def get_latest_vitals(patient_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Retrieve the most recent vital signs for a given patient."""
    # Check if patient exists
    patient = db.query(PatientDB).filter(PatientDB.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found"
        )

    # Get from real-time cache
    cached = EventService.get_latest_vitals(patient_id)
    if cached:
        return {
            "patient_id": patient_id,
            "room_id": patient.room_id,
            "name": patient.name,
            "vitals": cached,
            "source": "live_telemetry"
        }

    # Fallback to patient baseline vitals
    return {
        "patient_id": patient_id,
        "room_id": patient.room_id,
        "name": patient.name,
        "vitals": patient.baseline_vitals,
        "source": "baseline"
    }


@router.get("/history/{patient_id}")
def get_vitals_history(
    patient_id: str,
    limit: int = Query(60, ge=5, le=500, description="Number of historical readings"),
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Retrieve timeseries vitals readings for dashboard charts."""
    readings = (
        db.query(VitalsReadingDB)
        .filter(VitalsReadingDB.patient_id == patient_id)
        .order_by(VitalsReadingDB.timestamp.desc())
        .limit(limit)
        .all()
    )
    # Return in chronological order for charting
    return [r.to_dict() for r in reversed(readings)]


@router.get("/ecg/{patient_id}", response_model=ECGWaveformResponse)
def get_patient_ecg_waveform(
    patient_id: str,
    duration_seconds: float = Query(
        2.0,
        gt=0.0,
        le=10.0,
        description="Duration of ECG waveform in seconds (must be positive, max 10.0s)"
    ),
    sampling_rate: int = Query(
        250,
        ge=10,
        le=1000,
        description="Sampling frequency in Hz (must be positive, max 1000Hz)"
    ),
    db: Session = Depends(get_db)
) -> ECGWaveformResponse:
    """Generate simulated ECG lead waveform for a patient using current or baseline vitals."""
    patient = db.query(PatientDB).filter(PatientDB.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found"
        )

    # Check live telemetry cache first
    cached = EventService.get_latest_vitals(patient_id)
    heart_rate: Optional[float] = None
    rhythm: str = "NORMAL_SINUS_RHYTHM"

    if cached:
        # Check if live heart rate is cached
        hr_entry = cached.get("heart_rate")
        if hr_entry and hr_entry.get("value") is not None:
            try:
                heart_rate = float(hr_entry["value"])
            except (ValueError, TypeError):
                heart_rate = None

        # Check if live ecg_rhythm is cached
        rhythm_entry = cached.get("ecg_rhythm")
        if rhythm_entry and rhythm_entry.get("value") is not None:
            rhythm = str(rhythm_entry["value"])

    # Fallback to patient baseline vitals if no live heart rate
    if heart_rate is None:
        base_vitals = patient.baseline_vitals or {}
        heart_rate = float(base_vitals.get("heart_rate", 75.0))

    # Infer rhythm if still default and rate indicates extreme state
    if rhythm == "NORMAL_SINUS_RHYTHM" and heart_rate <= 0:
        rhythm = "ASYSTOLE"

    # Map rhythm to ECGAnalyzer rhythm_type parameter ("VFIB" or "NORMAL")
    rhythm_type = "VFIB" if "VFIB" in rhythm.upper() else "NORMAL"

    # Generate waveform points using Melisa's ECGAnalyzer
    points = ECGAnalyzer.generate_single_lead_points(
        heart_rate=int(round(heart_rate)),
        duration_seconds=duration_seconds,
        sampling_rate=sampling_rate,
        rhythm_type=rhythm_type
    )

    return ECGWaveformResponse(
        patient_id=patient_id,
        heart_rate=heart_rate,
        rhythm=rhythm,
        sampling_rate=sampling_rate,
        duration_seconds=duration_seconds,
        points=points
    )

