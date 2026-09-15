"""Database seeder to populate mock patients from shared contracts."""

import json
import logging
import os
from sqlalchemy.orm import Session
from backend.database.database import engine, Base, SessionLocal
from backend.models.db_models import PatientDB

logger = logging.getLogger(__name__)

# Find path to shared/mock_data/patients.json relative to repository root
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MOCK_PATIENTS_PATH = os.path.join(ROOT_DIR, "shared", "mock_data", "patients.json")


def seed_patients(db: Session) -> int:
    """Read shared/mock_data/patients.json and seed into the database if missing."""
    if not os.path.exists(MOCK_PATIENTS_PATH):
        logger.warning("Mock patients file not found at %s", MOCK_PATIENTS_PATH)
        return 0

    with open(MOCK_PATIENTS_PATH, "r", encoding="utf-8") as f:
        patients_data = json.load(f)

    seeded_count = 0
    for p in patients_data:
        existing = db.query(PatientDB).filter(PatientDB.patient_id == p["patient_id"]).first()
        if not existing:
            patient_record = PatientDB(
                patient_id=p["patient_id"],
                room_id=p["room_id"],
                name=p["name"],
                age=p["age"],
                gender=p["gender"],
                admission_date=p["admission_date"],
                condition=p["condition"],
                status=p["status"],
                assigned_doctor=p["assigned_doctor"],
                assigned_nurse=p["assigned_nurse"],
            )
            patient_record.devices_connected = p.get("devices_connected", [])
            patient_record.baseline_vitals = p.get("baseline_vitals", {})
            db.add(patient_record)
            seeded_count += 1

    if seeded_count > 0:
        db.commit()
        logger.info("Successfully seeded %d patients into the database.", seeded_count)

    return seeded_count


def init_db():
    """Create all tables and seed mock data."""
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_patients(db)
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_db()
    print("Database initialized and seeded successfully.")
