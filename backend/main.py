"""SmartPatientCare Central FastAPI Backend Application.

Maintained by Melisa. Integrates REST & WebSocket APIs, SQLite DB, and real-time telemetry streaming.
"""

from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes_events import router as events_router
from backend.api.routes_patients import router as patients_router
from backend.api.routes_vitals import router as vitals_router
from backend.api.websocket import router as ws_router
from backend.database.seeder import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SmartPatientCareBackend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context: initialize DB and seed initial patient data."""
    logger.info("Initializing SmartPatientCare database and seeding mock data...")
    init_db()
    logger.info("Database ready. SmartPatientCare backend is online.")
    yield
    logger.info("Shutting down SmartPatientCare backend...")


app = FastAPI(
    title="SmartPatientCare Backend API",
    description="Central telemetry ingest, patient monitoring, and alert dispatch service.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for frontend dashboard (Gauri's module)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits all origins during hackathon development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(patients_router)
app.include_router(events_router)
app.include_router(vitals_router)
app.include_router(ws_router)


@app.get("/", tags=["Health"])
def root_status():
    """Service status and quick health check."""
    return {
        "service": "SmartPatientCare Backend",
        "status": "HEALTHY",
        "version": "1.0.0",
        "endpoints": {
            "patients": "/api/patients",
            "patient_detail": "/api/patients/{id}",
            "events": "/api/events",
            "active_events": "/api/events/active",
            "acknowledge_event": "/api/events/{id}/acknowledge",
            "resolve_event": "/api/events/{id}/resolve",
            "vitals": "/api/vitals",
            "ecg_waveform": "/api/vitals/ecg/{patient_id}",
            "alerts_websocket": "/ws/alerts",
            "telemetry_websocket": "/ws/telemetry",
            "docs": "/docs"
        }
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import os
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    logger.info("Starting server on %s:%d (CORS enabled for all origins)", host, port)
    uvicorn.run("backend.main:app", host=host, port=port, reload=True)

