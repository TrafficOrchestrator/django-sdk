"""
Management command: python manage.py check_license

Validates the configured license key and displays status.
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from traffic_orchestrator_django.client import TrafficOrchestratorClient


class Command(BaseCommand):
    help = "Validate your Traffic Orchestrator license key"

    def add_arguments(self, parser):
        parser.add_argument(
            "--key",
            type=str,
            help="License key to validate (overrides settings)",
        )
        parser.add_argument(
            "--domain",
            type=str,
            help="Domain to validate against",
        )
        parser.add_argument(
            "--health",
            action="store_true",
            help="Also check API health status",
        )

    def handle(self, *args, **options):
        config = getattr(settings, "TRAFFIC_ORCHESTRATOR", {})
        license_key = options["key"] or config.get("LICENSE_KEY", "")

        if not license_key:
            raise CommandError(
                "No license key provided. Use --key or set TRAFFIC_ORCHESTRATOR['LICENSE_KEY'] in settings."
            )

        client = TrafficOrchestratorClient.from_django_settings()

        # Health check
        if options["health"]:
            self.stdout.write("\n📡 API Health Check...")
            try:
                health = client.health_check()
                if health.get("status") == "ok":
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"  ✅ API healthy (v{health.get('version', '?')})"
                        )
                    )
                else:
                    self.stdout.write(self.style.ERROR("  ❌ API unhealthy"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ❌ API unreachable: {e}"))

        # License validation
        self.stdout.write("\n🔑 License Validation...")
        try:
            result = client.validate_license(license_key, domain=options.get("domain"))

            if result.get("valid"):
                self.stdout.write(self.style.SUCCESS("  ✅ License is VALID"))
                if result.get("plan"):
                    self.stdout.write(f"     Plan: {result['plan']}")
                if result.get("domains"):
                    self.stdout.write(f"     Domains: {', '.join(result['domains'])}")
                if result.get("expiresAt"):
                    self.stdout.write(f"     Expires: {result['expiresAt']}")
            else:
                msg = result.get("message") or result.get("error") or "Unknown error"
                self.stdout.write(self.style.ERROR(f"  ❌ License INVALID: {msg}"))

        except Exception as e:
            raise CommandError(f"Validation failed: {e}")

        # Usage stats (if API key is configured)
        if config.get("API_KEY"):
            self.stdout.write("\n📊 Usage Statistics...")
            try:
                usage = client.get_usage()
                self.stdout.write(f"     Today: {usage.get('validationsToday', 0)} validations")
                self.stdout.write(f"     Month: {usage.get('validationsMonth', 0)}/{usage.get('monthlyLimit', 0)}")
                self.stdout.write(f"     Active Licenses: {usage.get('activeLicenses', 0)}")
                self.stdout.write(f"     Active Domains: {usage.get('activeDomains', 0)}")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"     ⚠ Could not fetch usage: {e}"))

        self.stdout.write("")
