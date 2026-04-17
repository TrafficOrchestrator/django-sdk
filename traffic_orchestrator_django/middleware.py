"""
Django middleware for automatic license validation.

Add to settings.py:
    MIDDLEWARE = [
        ...
        'traffic_orchestrator_django.middleware.LicenseValidationMiddleware',
    ]

    TRAFFIC_ORCHESTRATOR = {
        'LICENSE_KEY': 'LK-xxxx-xxxx',
        'PROTECTED_PATHS': ['/api/', '/dashboard/'],  # Optional
        'EXCLUDE_PATHS': ['/health/', '/public/'],     # Optional
    }
"""

import logging
from django.conf import settings
from django.http import JsonResponse
from django.core.cache import cache

from .client import TrafficOrchestratorClient

logger = logging.getLogger("traffic_orchestrator")


class LicenseValidationMiddleware:
    """Validates the Traffic Orchestrator license on protected paths.

    Results are cached for 1 hour to avoid excessive API calls.
    """

    CACHE_KEY = "traffic_orchestrator_license_status"
    CACHE_TTL = 3600  # 1 hour

    def __init__(self, get_response):
        self.get_response = get_response
        self.config = getattr(settings, "TRAFFIC_ORCHESTRATOR", {})
        self.protected_paths = self.config.get("PROTECTED_PATHS", [])
        self.exclude_paths = self.config.get("EXCLUDE_PATHS", ["/health/"])

    def __call__(self, request):
        # Skip excluded paths
        for path in self.exclude_paths:
            if request.path.startswith(path):
                return self.get_response(request)

        # Only check protected paths if specified, otherwise check all
        if self.protected_paths:
            protected = any(request.path.startswith(p) for p in self.protected_paths)
            if not protected:
                return self.get_response(request)

        # Check license (from header or config)
        license_key = (
            request.META.get("HTTP_X_LICENSE_KEY")
            or self.config.get("LICENSE_KEY", "")
        )

        if not license_key:
            return self.get_response(request)

        # Use cached result
        cached = cache.get(self.CACHE_KEY)
        if cached is not None:
            if not cached.get("valid"):
                return JsonResponse(
                    {"error": "Invalid license", "code": "LICENSE_INVALID"},
                    status=403,
                )
            request.license = cached
            return self.get_response(request)

        # Validate against API
        try:
            client = TrafficOrchestratorClient.from_django_settings()
            result = client.validate_license(license_key, domain=request.get_host())
            cache.set(self.CACHE_KEY, result, self.CACHE_TTL)

            if not result.get("valid"):
                logger.warning("License validation failed: %s", result.get("message"))
                return JsonResponse(
                    {"error": result.get("message", "Invalid license"), "code": "LICENSE_INVALID"},
                    status=403,
                )

            request.license = result
        except Exception as e:
            logger.error("License validation error: %s", str(e))
            # Fail open — don't block requests if API is unreachable
            request.license = {"valid": False, "error": str(e)}

        return self.get_response(request)
