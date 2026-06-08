from django.db import models


class GrafanaDashboardAccess(models.Model):
    """Meta-model used solely to anchor the plugin's permission."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("can_view_grafana_statistics", "Can view grafana statistics"),
        )
