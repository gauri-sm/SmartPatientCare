"""REST API endpoints for patient management."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.models.db_models import PatientDB
from backend.models.schemas import PatientResponse

router = APIRouter(prefix="/api/patients", tags=["Patients"])


@router.get("", response_model=List[PatientResponse])
def get_all_patients(db: Session = Depends(get_db)):
    """Retrieve list of all admitted patients."""
    patients = db.query(PatientDB).all()
    return [p.to_dict() for p in patients]


@router.get("/{id}", response_model=PatientResponse)
def get_patient(id: str, db: Session = Depends(get_db)):
    """Retrieve full details of a single patient by ID."""
    patient = db.query(PatientDB).filter(PatientDB.patient_id == id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID '{id}' not found"
        )
    return patient.to_dict()
