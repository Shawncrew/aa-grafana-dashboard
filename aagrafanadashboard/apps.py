from django.apps import AppConfig

from . import __version__


class AaGrafanaDashboardConfig(AppConfig):
    name = "aagrafanadashboard"
    label = "aagrafanadashboard"
    verbose_name = f"AA Grafana Dashboard v{__version__}"
