"""
SmartPatientCare - Computer Vision API Client
Author: Gauri (Frontend & CV Lead)

Transmits detected vision events to the SmartPatientCare backend API.
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

class CVBackendClient:
    """
    Sends event payloads to the central FastAPI backend POST /api/events endpoint.
    Uses standard library urllib to avoid requiring external requests package.
    """

    def __init__(self, backend_url: str = "http://localhost:8000"):
        self.backend_url = backend_url.rstrip("/")
        self.events_endpoint = f"{self.backend_url}/api/events"

    def send_event(self, event: Dict[str, Any], timeout: float = 3.0) -> bool:
        """
        Sends an event to the backend API.
        Returns True if successfully received (HTTP 200/201), False otherwise.
        """
        data_bytes = json.dumps(event).encode("utf-8")
        req = urllib.request.Request(
            self.events_endpoint,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status in (200, 201):
                    return True
                return False
        except urllib.error.URLError:
            # Backend may not be started yet during hackathon development
            return False
        except Exception:
            return False
