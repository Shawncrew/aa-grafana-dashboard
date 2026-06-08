import logging

import requests
from django.contrib.auth.decorators import login_required, permission_required
from django.http import HttpRequest, HttpResponse, StreamingHttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from . import app_settings, helpers

logger = logging.getLogger(__name__)


@login_required
@permission_required("aagrafanadashboard.can_view_grafana_statistics")
def index(request: HttpRequest) -> HttpResponse:
    """Statistics tab landing page: lists dashboards tagged for Alliance Auth."""
    dashboards = [
        {
            "title": dashboard.get("title"),
            "proxy_path": helpers.dashboard_proxy_path(dashboard.get("url", "")),
        }
        for dashboard in helpers.get_tagged_dashboards()
    ]
    return render(
        request,
        "aagrafanadashboard/index.html",
        {
            "dashboards": dashboards,
            "proxy_path": app_settings.GRAFANA_PROXY_PATH,
        },
    )


@csrf_exempt
@login_required
@permission_required("aagrafanadashboard.can_view_grafana_statistics")
@require_http_methods(["GET", "POST", "HEAD"])
def grafana_proxy(request: HttpRequest, path: str = "") -> HttpResponse:
    """Transparently relay requests to the internal Grafana instance.

    Exempt from Django's CSRF protection: Grafana's frontend authenticates
    against this proxy via its own session/token model, not Django's CSRF
    token, so the middleware would otherwise reject every POST it sends
    (dashboard queries, feature-flag evaluation, frontend metrics, ...).

    Grafana is configured with `serve_from_sub_path = true` and a `root_url`
    matching `app_settings.GRAFANA_PROXY_PATH`, so it emits HTML/JS/API URLs
    that already point back through this proxy - no rewriting is required.
    """
    if not app_settings.GRAFANA_PROXY_BASE_URL:
        logger.warning("AAGRAFANADASHBOARD_GRAFANA_BASE_URL is not configured")
        return HttpResponse("Grafana proxy is not configured.", status=503)

    if path.startswith("api/live/"):
        # Grafana Live needs a WebSocket upgrade, which this synchronous
        # request-based relay cannot perform. Respond immediately so the
        # browser's reconnect loop fails fast client-side instead of being
        # forwarded to Grafana, rejected, and logged here as "Bad Request"
        # on every retry.
        return HttpResponse(status=204)

    target_url = f"{app_settings.GRAFANA_PROXY_BASE_URL}{request.get_full_path()}"

    headers = helpers.filter_proxy_request_headers(dict(request.headers))
    if app_settings.GRAFANA_API_TOKEN:
        headers["Authorization"] = f"Bearer {app_settings.GRAFANA_API_TOKEN}"

    try:
        upstream = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.body or None,
            stream=True,
            timeout=app_settings.GRAFANA_REQUEST_TIMEOUT,
        )
    except requests.RequestException:
        logger.exception("Failed to reach Grafana at %s", target_url)
        return HttpResponse("Unable to reach Grafana.", status=502)

    response = StreamingHttpResponse(
        upstream.iter_content(chunk_size=8192),
        status=upstream.status_code,
        content_type=upstream.headers.get("Content-Type"),
    )
    for key, value in helpers.filter_proxy_response_headers(upstream.headers).items():
        if key.lower() == "content-type":
            continue
        response[key] = value

    return response
