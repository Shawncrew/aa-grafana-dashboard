from django.db import models


class GrafanaDashboardAccess(models.Model):
    """Meta-model used solely to anchor the plugin's permission."""

    class Meta:
        managed = False
        default_permissions = ()
        permissions = (
            ("can_view_grafana_statistics", "Can view grafana statistics"),
        )


class CorporationMemberTracking(models.Model):
    corporation_id = models.IntegerField(db_index=True)
    character_id = models.IntegerField()
    character_name = models.CharField(max_length=64, blank=True)
    logon_date = models.DateTimeField(null=True, blank=True)
    logoff_date = models.DateTimeField(null=True, blank=True)
    ship_type_id = models.IntegerField(null=True, blank=True)
    ship_type_name = models.CharField(max_length=64, blank=True)
    location_id = models.BigIntegerField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("corporation_id", "character_id")

    def __str__(self):
        return f"{self.character_name} ({self.corporation_id})"
