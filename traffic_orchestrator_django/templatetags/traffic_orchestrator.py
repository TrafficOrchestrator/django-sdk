"""
Django template tags for Traffic Orchestrator.

Usage in templates:
    {% load traffic_orchestrator %}

    {% license_status %}
    {% license_status "LK-xxxx-xxxx" %}
"""

from django import template
from django.conf import settings
from django.core.cache import cache
from django.utils.safestring import mark_safe

from ..client import TrafficOrchestratorClient

register = template.Library()


@register.simple_tag
def license_status(license_key=None):
    """Display license validation status as HTML badge."""
    config = getattr(settings, "TRAFFIC_ORCHESTRATOR", {})
    key = license_key or config.get("LICENSE_KEY", "")

    if not key:
        return mark_safe('<span class="to-status to-no-key">No license configured</span>')

    cache_key = f"to_license_{key[:8]}"
    cached = cache.get(cache_key)

    if cached is None:
        try:
            client = TrafficOrchestratorClient.from_django_settings()
            cached = client.validate_license(key)
            cache.set(cache_key, cached, 3600)
        except Exception:
            cached = {"valid": False, "error": "API unreachable"}

    if cached.get("valid"):
        plan = cached.get("plan", "")
        return mark_safe(f'<span class="to-status to-valid">✅ Licensed ({plan})</span>')

    return mark_safe('<span class="to-status to-invalid">❌ Unlicensed</span>')


@register.simple_tag
def license_plan(license_key=None):
    """Return the license plan name."""
    config = getattr(settings, "TRAFFIC_ORCHESTRATOR", {})
    key = license_key or config.get("LICENSE_KEY", "")

    if not key:
        return ""

    cache_key = f"to_license_{key[:8]}"
    cached = cache.get(cache_key)

    if cached is None:
        try:
            client = TrafficOrchestratorClient.from_django_settings()
            cached = client.validate_license(key)
            cache.set(cache_key, cached, 3600)
        except Exception:
            return ""

    return cached.get("plan", "")
