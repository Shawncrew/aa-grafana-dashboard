# AA Grafana Dashboard

Adds a **Statistics** tab to Alliance Auth that lists Grafana dashboards
tagged `alliance-auth` and lets permitted users open them through a
server-side proxy to an internally-hosted Grafana instance.

Grafana stays on the internal Docker network (not publicly reachable). The
Django backend, which *can* reach it internally, relays requests on behalf of
authenticated, permitted AA users.

## Installation

1. Install the package into your Alliance Auth virtual environment:

   ```
   pip install -e /path/to/aa-grafana-dashboard
   ```

2. Add `"aagrafanadashboard"` to `INSTALLED_APPS` in `myauth/settings/local.py`.

3. Add the settings described below to `local.py`.

4. Run migrations and restart Alliance Auth (gunicorn/supervisor, etc.):

   ```
   python manage.py migrate aagrafanadashboard
   ```

5. Grant the `aagrafanadashboard | grafana dashboard access | Can view grafana
   statistics` permission to the states/groups that should see the tab.

## Settings (`local.py`)

```python
# Internal URL the AA backend uses to reach Grafana (same Docker network)
AAGRAFANADASHBOARD_GRAFANA_BASE_URL = "http://grafana:3000"

# Must match Grafana's root_url sub-path (see below)
AAGRAFANADASHBOARD_PROXY_PATH = "/statistics/grafana/"

# Grafana service-account token (Viewer role is sufficient)
AAGRAFANADASHBOARD_GRAFANA_API_TOKEN = "glsa_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Optional - defaults shown
AAGRAFANADASHBOARD_DASHBOARD_TAG = "alliance-auth"
AAGRAFANADASHBOARD_REQUEST_TIMEOUT = 30
```

Generate the service-account token in Grafana under **Administration → Users
and access → Service accounts**. A `Viewer` role is enough to browse and
render dashboards.

## Required Grafana configuration

The proxy is *transparent*: it forwards whatever path the browser requests
straight through to Grafana, byte for byte. For that to work, Grafana must be
told it is being served from the `/statistics/grafana/` sub-path so that every
link, asset and API call it emits already points back through the proxy - no
HTML/JS rewriting needed on the AA side.

In `grafana.ini` (or the equivalent environment variables):

```ini
[server]
domain = your-auth-domain.example.com
root_url = %(protocol)s://%(domain)s/statistics/grafana/
serve_from_sub_path = true
```

Because every AA user reaches Grafana as the same service account, also
restrict Grafana so it can't be reached directly from outside the Docker
network (firewall rule / not publishing the port / reverse-proxy ACL) - access
control for end users is enforced entirely by the
`can_view_grafana_statistics` permission in Alliance Auth.

Tag every dashboard you want to expose with `alliance-auth` (or whatever tag
you set via `AAGRAFANADASHBOARD_DASHBOARD_TAG`) so it appears on the
Statistics tab.

## Permissions

| Permission                      | Admin Site               | Description                         |
|---------------------------------|--------------------------|-------------------------------------|
| `can_view_grafana_statistics`   | Grafana Dashboard Access | Can access the Statistics tab and open proxied Grafana dashboards |
