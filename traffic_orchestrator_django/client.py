"""
Traffic Orchestrator Django SDK

Enterprise license management with middleware, template tags,
and management commands for Django applications.

Settings (in settings.py):
    TRAFFIC_ORCHESTRATOR = {
        'API_URL': 'https://api.trafficorchestrator.com/api/v1',
        'API_KEY': '',
        'LICENSE_KEY': '',
        'TIMEOUT': 10,
        'RETRIES': 2,
    }

Middleware:
    MIDDLEWARE = [
        ...
        'traffic_orchestrator_django.middleware.LicenseValidationMiddleware',
    ]
"""

import time
import json
import base64
import hashlib
import logging
import requests
from typing import Optional, Dict, Any, List

__version__ = "2.0.0"
logger = logging.getLogger("traffic_orchestrator")


class TrafficOrchestratorError(Exception):
    """Base exception for Traffic Orchestrator SDK errors."""
    def __init__(self, message: str, code: str = "UNKNOWN", status: int = 0):
        super().__init__(message)
        self.code = code
        self.status = status


class TrafficOrchestratorClient:
    """Core client for Traffic Orchestrator API.

    Usage:
        from traffic_orchestrator_django import TrafficOrchestratorClient

        client = TrafficOrchestratorClient(api_key="sk_live_xxxxx")
        result = client.validate_license("LK-xxxx-xxxx", domain="example.com")
    """

    def __init__(
        self,
        api_url: str = "https://api.trafficorchestrator.com/api/v1",
        api_key: Optional[str] = None,
        timeout: int = 10,
        retries: int = 2,
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.retries = retries

    @classmethod
    def from_django_settings(cls) -> "TrafficOrchestratorClient":
        """Create client from Django settings."""
        from django.conf import settings
        config = getattr(settings, "TRAFFIC_ORCHESTRATOR", {})
        return cls(
            api_url=config.get("API_URL", "https://api.trafficorchestrator.com/api/v1"),
            api_key=config.get("API_KEY", ""),
            timeout=config.get("TIMEOUT", 10),
            retries=config.get("RETRIES", 2),
        )

    # ── Core: License Validation ─────────────────────────────────────────

    def validate_license(self, token: str, domain: Optional[str] = None) -> Dict[str, Any]:
        """Validate a license key against the API server."""
        payload: Dict[str, str] = {"token": token}
        if domain:
            payload["domain"] = domain
        return self._request("POST", "/validate", json=payload)

    @staticmethod
    def verify_offline(
        token: str,
        public_key_pem: str,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Validate a license offline using Ed25519 public key verification."""
        try:
            from cryptography.hazmat.primitives import serialization
            import jwt

            public_key = serialization.load_pem_public_key(
                public_key_pem.encode() if isinstance(public_key_pem, str) else public_key_pem
            )
            decoded = jwt.decode(
                token,
                public_key,
                algorithms=["EdDSA"],
                audience=["license-validation", "license-offline"],
                issuer="trafficorchestrator.com",
            )

            if domain and "dom" in decoded:
                domains = decoded["dom"]
                if not any(d in domain for d in domains):
                    return {"valid": False, "message": "Domain mismatch"}

            return {
                "valid": True,
                "payload": decoded,
                "plan": decoded.get("plan"),
                "domains": decoded.get("dom"),
                "expiresAt": decoded.get("exp"),
            }
        except Exception as e:
            return {"valid": False, "message": str(e)}

    # ── License Management ───────────────────────────────────────────────

    def list_licenses(self) -> List[Dict[str, Any]]:
        """List all licenses for the authenticated user."""
        data = self._request("GET", "/portal/licenses")
        return data.get("licenses", [])

    def create_license(
        self,
        app_name: str,
        domain: Optional[str] = None,
        plan_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new license."""
        payload: Dict[str, str] = {"appName": app_name}
        if domain:
            payload["domain"] = domain
        if plan_id:
            payload["planId"] = plan_id
        return self._request("POST", "/portal/licenses", json=payload)

    def rotate_license(self, license_id: str) -> Dict[str, Any]:
        """Rotate a license key (revoke old, generate new)."""
        return self._request("POST", f"/portal/licenses/{license_id}/rotate")

    def add_domain(self, license_id: str, domain: str) -> Dict[str, Any]:
        """Add a domain to a license."""
        return self._request("POST", f"/portal/licenses/{license_id}/domains", json={"domain": domain})

    def remove_domain(self, license_id: str, domain: str) -> Dict[str, Any]:
        """Remove a domain from a license."""
        return self._request("DELETE", f"/portal/licenses/{license_id}/domains", json={"domain": domain})

    def delete_license(self, license_id: str) -> Dict[str, Any]:
        """Delete (revoke) a license."""
        return self._request("DELETE", f"/portal/licenses/{license_id}")

    def update_settings(self, license_id: str, **settings: Any) -> Dict[str, Any]:
        """Update license settings (allowed_ips, environment)."""
        return self._request("PUT", f"/portal/licenses/{license_id}/settings", json=settings)

    # ── Usage & Analytics ────────────────────────────────────────────────

    def get_usage(self) -> Dict[str, Any]:
        """Get current usage statistics."""
        return self._request("GET", "/portal/stats")

    # ── Health ───────────────────────────────────────────────────────────

    def health_check(self) -> Dict[str, Any]:
        """Check API health status."""
        return self._request("GET", "/health")

    # ── Internal ─────────────────────────────────────────────────────────

    
    def _require_api_key(self, method):
        """Raises if no API key is configured, with a developer-friendly signup URL."""
        if not self.api_key:
            raise Exception(
                "TrafficOrchestrator Auth Error: Missing API Key. To generate your free API Key in 60 seconds, visit: https://trafficorchestrator.com/dashboard/keys"
            )

    def _request(self, method: str, path: str, **kwargs: Any) -> Dict[str, Any]:
        url = f"{self.api_url}{path}"
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        last_error: Optional[Exception] = None

        for attempt in range(self.retries + 1):
            try:
                response = requests.request(
                    method, url, headers=headers, timeout=self.timeout, **kwargs,
                )
                data = response.json()

                if not response.ok:
                    err = TrafficOrchestratorError(
                        data.get("error", f"HTTP {response.status_code}"),
                        code=data.get("code", "UNKNOWN"),
                        status=response.status_code,
                    )
                    raise err

                return data

            except TrafficOrchestratorError:
                raise
            except requests.exceptions.RequestException as e:
                last_error = e
                if attempt < self.retries:
                    time.sleep(min(1.0 * (2 ** attempt), 5.0))

        raise last_error or TrafficOrchestratorError("Request failed after retries")
