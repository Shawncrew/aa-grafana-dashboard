import logging

import requests

from . import app_settings

logger = logging.getLogger(__name__)

# Headers that must not be forwarded between AA and Grafana when proxying,
# since they describe the hop-by-hop connection rather than the payload.
_HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "content-encoding",
    "content-length",
}


def _grafana_session() -> requests.Session:
    session = requests.Session()
    if app_settings.GRAFANA_API_TOKEN:
        session.headers["Authorization"] = f"Bearer {app_settings.GRAFANA_API_TOKEN}"
    return session


def get_tagged_dashboards() -> list[dict]:
    """Return Grafana dashboard search results tagged for Alliance Auth."""
    if not app_settings.GRAFANA_PROXY_BASE_URL:
        logger.warning("AAGRAFANADASHBOARD_GRAFANA_BASE_URL is not configured")
        return []

    url = f"{app_settings.GRAFANA_PROXY_BASE_URL}/api/search"
    try:
        response = _grafana_session().get(
            url,
            params={"tag": app_settings.GRAFANA_DASHBOARD_TAG, "type": "dash-db"},
            timeout=app_settings.GRAFANA_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Failed to fetch dashboards from Grafana at %s", url)
        return []

    return response.json()


def dashboard_proxy_path(dashboard_url: str) -> str:
    """Convert a dashboard URL returned by Grafana into a path for our proxy.

    When Grafana is configured with `serve_from_sub_path = true`, the URLs it
    returns (e.g. from /api/search) already include its configured sub-path
    (= our GRAFANA_PROXY_PATH). The proxy URL adds that same prefix, so it
    must be stripped here first to avoid doubling it.
    """
    path = dashboard_url.lstrip("/")
    prefix = app_settings.GRAFANA_PROXY_PATH.strip("/")
    if prefix:
        prefix = f"{prefix}/"
        if path.startswith(prefix):
            path = path[len(prefix):]
    return path


def filter_proxy_request_headers(headers: dict) -> dict:
    """Strip hop-by-hop and host headers before forwarding a request to Grafana."""
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in _HOP_BY_HOP_HEADERS and key.lower() != "host"
    }


def filter_proxy_response_headers(headers: dict) -> dict:
    """Strip hop-by-hop headers before relaying a Grafana response to the browser."""
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in _HOP_BY_HOP_HEADERS
    }
