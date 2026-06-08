from django.conf import settings

# Internal base URL the AA backend uses to reach Grafana, e.g. "http://grafana:3000"
GRAFANA_PROXY_BASE_URL: str = getattr(
    settings, "AAGRAFANADASHBOARD_GRAFANA_BASE_URL", ""
).rstrip("/")

# Public-facing path under which the proxy is served. Must match Grafana's
# `root_url` / `serve_from_sub_path` configuration so Grafana emits links that
# point back through this proxy.
GRAFANA_PROXY_PATH: str = getattr(
    settings, "AAGRAFANADASHBOARD_PROXY_PATH", "/statistics/grafana/"
)

# Service account token (or API key) used by the proxy/API calls. Grafana sees
# every AA user as this single account; the AA permission gates who gets here.
GRAFANA_API_TOKEN: str = getattr(settings, "AAGRAFANADASHBOARD_GRAFANA_API_TOKEN", "")

# Tag used to select which dashboards appear on the Statistics tab.
GRAFANA_DASHBOARD_TAG: str = getattr(
    settings, "AAGRAFANADASHBOARD_DASHBOARD_TAG", "alliance-auth"
)

# Timeout (seconds) for requests made to Grafana.
GRAFANA_REQUEST_TIMEOUT: float = getattr(
    settings, "AAGRAFANADASHBOARD_REQUEST_TIMEOUT", 30
)
