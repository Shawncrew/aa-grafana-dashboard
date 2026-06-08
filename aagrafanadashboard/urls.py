from django.urls import re_path

from . import views

app_name = "aagrafanadashboard"

urlpatterns = [
    re_path(r"^$", views.index, name="index"),
    # Catches everything Grafana itself requests under the proxy sub-path
    # (HTML pages, static assets, JSON APIs, websockets-over-http, ...).
    re_path(r"^grafana/(?P<path>.*)$", views.grafana_proxy, name="grafana_proxy"),
]
