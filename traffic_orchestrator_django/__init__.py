"""Traffic Orchestrator Django SDK - License validation for Django applications."""

from .client import TrafficOrchestratorClient, TrafficOrchestratorError

__version__ = "2.0.0"
__all__ = ["TrafficOrchestratorClient", "TrafficOrchestratorError"]

default_app_config = "traffic_orchestrator_django.apps.TrafficOrchestratorConfig"
