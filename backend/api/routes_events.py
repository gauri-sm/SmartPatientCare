"""REST API endpoints for telemetry and emergency event ingestion and queries."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.database.database import get_db
from backend.models.schemas import SmartPatientCareEvent, EventCreate, EventStatusUpdate
from backend.services.event_service import EventService

router = APIRouter(prefix="/api/events", tags=["Events & Alerts"])


@router.get("/active", response_model=List[SmartPatientCareEvent])
def get_active_events(
    limit: int = Query(100, ge=1, le=500, description="Max number of active alerts to return"),
    db: Session = Depends(get_db)
):
    """Retrieve all currently active events and alerts across all patients."""
    return EventService.get_active_events(db=db, limit=limit)


@router.get("", response_model=List[SmartPatientCareEvent])
def get_events(
    patient_id: Optional[str] = Query(None, description="Filter by patient ID (e.g. P001)"),
    severity: Optional[str] = Query(None, description="Filter by severity: INFO, WARNING, CRITICAL, etc."),
    status: Optional[str] = Query(None, description="Filter by status: ACTIVE, ACKNOWLEDGED, RESOLVED"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    limit: int = Query(50, ge=1, le=500, description="Max number of events to return"),
    db: Session = Depends(get_db)
):
    """Retrieve telemetry events and alerts with optional filtering."""
    return EventService.get_events(
        db=db,
        patient_id=patient_id,
        severity=severity,
        status=status,
        event_type=event_type,
        limit=limit
    )


@router.post("", response_model=SmartPatientCareEvent, status_code=status.HTTP_201_CREATED)
async def ingest_event(event_data: EventCreate, db: Session = Depends(get_db)):
    """Ingest a new telemetry or alert event.

    Supports events from:
    - CCTV / YOLO (with optional video_source, camera_id, evidence_type)
    - Medical device simulator (vitals, ECG)
    - IV drip simulator
    - Emergency alert engine
    """
    return await EventService.ingest_event(db=db, event_data=event_data)


@router.post("/{id}/acknowledge", response_model=SmartPatientCareEvent)
async def acknowledge_event(id: str, db: Session = Depends(get_db)):
    """Acknowledge an active event or alert by ID."""
    updated = await EventService.acknowledge_event(db=db, event_id=id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID '{id}' not found"
        )
    return updated


@router.post("/{id}/resolve", response_model=SmartPatientCareEvent)
async def resolve_event(id: str, db: Session = Depends(get_db)):
    """Resolve an event or alert by ID."""
    updated = await EventService.resolve_event(db=db, event_id=id)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID '{id}' not found"
        )
    return updated


@router.patch("/{event_id}/status", response_model=SmartPatientCareEvent)
async def update_event_status(
    event_id: str,
    status_update: EventStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update event status (e.g., mark as ACKNOWLEDGED or RESOLVED)."""
    updated = await EventService.update_event_status(
        db=db,
        event_id=event_id,
        new_status=status_update.status
    )
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID '{event_id}' not found"
        )
    return updated
