"""Telemetry Generator for IV Drip Monitoring.

Generates telemetry events strictly conforming to shared/schemas/event_schema.json
and provides JSON Schema validation.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple
import jsonschema


class DripTelemetryGenerator:
    """Creates and validates IV drip telemetry events according to shared/schemas/event_schema.json."""

    def __init__(self, schema_path: Optional[str] = None):
        if not schema_path:
            repo_root = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..")
            )
            schema_path = os.path.join(repo_root, "shared", "schemas", "event_schema.json")

        self.schema_path = schema_path
        self._schema = self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        if not os.path.exists(self.schema_path):
            raise FileNotFoundError(f"Schema file not found at: {self.schema_path}")
        with open(self.schema_path, "r", encoding="utf-8") as f:
            return json.load(f)

    @property
    def schema(self) -> Dict[str, Any]:
        return self._schema

    @staticmethod
    def generate_iso_timestamp() -> str:
        """Return an ISO 8601 UTC timestamp in Zulu format (YYYY-MM-DDTHH:MM:SSZ)."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def build_event(
        self,
        event_type: str,
        patient_id: str,
        room_id: str,
        source: str,
        parameter: str,
        value: Any,
        unit: str,
        severity: str,
        message: str,
        status: str = "ACTIVE",
        event_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Construct an event payload and validate it against the JSON schema."""
        if not event_id:
            event_id = f"EVT-DRIP-{uuid.uuid4().hex[:8].upper()}"

        # Clean value type to match schema: ["number", "string", "boolean", "null"]
        clean_value = value
        if isinstance(value, float):
            clean_value = round(value, 2)

        event = {
            "event_id": str(event_id),
            "timestamp": self.generate_iso_timestamp(),
            "event_type": str(event_type),
            "patient_id": str(patient_id),
            "room_id": str(room_id),
            "source": str(source),
            "parameter": str(parameter),
            "value": clean_value,
            "unit": str(unit),
            "severity": str(severity),
            "message": str(message),
            "status": str(status),
        }

        # Validate against schema
        self.validate(event)
        return event

    def validate(self, event: Dict[str, Any]) -> None:
        """Validate an event dictionary against the shared schema.

        Raises jsonschema.ValidationError if invalid.
        """
        jsonschema.validate(instance=event, schema=self._schema)

    def is_valid(self, event: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """Return (True, None) if valid, or (False, error_message) if invalid."""
        try:
            self.validate(event)
            return (True, None)
        except jsonschema.ValidationError as err:
            return (False, str(err.message))
