# django-traffic-orchestrator

Official Django integration for [Traffic Orchestrator](https://trafficorchestrator.com).

📖 [API Reference](https://trafficorchestrator.com/docs#api) · [SDK Guides](https://trafficorchestrator.com/docs/sdk/django) · [OpenAPI Spec](https://api.trafficorchestrator.com/api/v1/openapi.json)

## Install

```bash
pip install django-traffic-orchestrator
```

## Configuration

```python
# settings.py
INSTALLED_APPS = [
    'traffic_orchestrator.django',
]

TRAFFIC_ORCHESTRATOR = {
    'API_KEY': os.environ.get('TO_API_KEY'),
    'TIMEOUT': 5,
    'RETRIES': 3,
}
```

## Middleware (Automatic License Checking)

```python
# settings.py
MIDDLEWARE = [
    'traffic_orchestrator.django.middleware.LicenseMiddleware',
    # ...
]
```

## Decorator

```python
from traffic_orchestrator.django.decorators import require_license

@require_license(plan='pro')
def premium_view(request):
    return JsonResponse({'access': 'granted'})
```

## Template Tag

```django
{% load traffic_orchestrator %}
{% if_licensed 'pro' %}
  <div>Premium content</div>
{% endif_licensed %}
```

## API Methods

| Method/Decorator | Auth | Description |
| --- | --- | --- |
| `@require_license(plan)` | Yes | View decorator — restrict by plan |
| `{% if_licensed %}` | Yes | Template tag — conditional content |
| `validate_license(token, domain)` | No | Validate a license key |
| `verify_offline(token)` | No | Ed25519 offline verification |
| `list_licenses()` | Yes | List all licenses |
| `create_license(options)` | Yes | Create a new license |
| `add_domain(id, domain)` | Yes | Add domain to license |
| `remove_domain(id, domain)` | Yes | Remove domain from license |
| `get_usage()` | Yes | Get usage statistics |
| `health_check()` | No | Check API health |

## Multi-Environment

```python
# settings.py
TRAFFIC_ORCHESTRATOR = {
    'API_KEY': os.environ.get('TO_API_KEY'),
    # Staging
    'API_URL': os.environ.get('TO_API_URL', 'https://api.trafficorchestrator.com/api/v1'),
}
```

## Offline Verification (Enterprise)

Validate licenses locally without API calls using Ed25519 JWT signatures:

```python
# settings.py
TRAFFIC_ORCHESTRATOR = {
    'PUBLIC_KEY': os.environ.get('TO_PUBLIC_KEY'),
}

# views.py
from traffic_orchestrator.django import verify_offline

result = verify_offline(license_token)
if result.valid:
    print(f"Plan: {result.plan_id}")
```

## Requirements

- Python 3.8+
- Django 4.0+

## License

MIT
