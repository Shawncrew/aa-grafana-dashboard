import logging

from celery import shared_task
from django.apps import apps
from django.utils import timezone

from esi.models import Token

logger = logging.getLogger(__name__)


def _get_director_token(corporation_id):
    """Find a valid ESI token with director roles for the given EVE corporation ID."""
    try:
        CharacterAudit = apps.get_model("corptools", "CharacterAudit")
        CharacterRoles = apps.get_model("corptools", "CharacterRoles")
    except LookupError:
        logger.warning("corptools not installed, cannot fetch member tracking")
        return None

    director_char_ids = CharacterRoles.objects.filter(
        director=True
    ).values_list("character_id", flat=True)

    active_audits = CharacterAudit.objects.filter(
        character_id__in=director_char_ids,
        active=True,
    ).select_related("character")

    for audit in active_audits:
        char = audit.character
        if char.corporation_id != corporation_id:
            continue
        try:
            token = Token.objects.filter(
                character_id=char.character_id,
            ).require_scopes(
                ["esi-corporations.track_members.v1"]
            ).first()
            if token:
                return token
        except Exception:
            continue
    return None


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def update_member_tracking(self):
    """Fetch member tracking from ESI for all corps with director tokens."""
    from .models import CorporationMemberTracking

    try:
        EveCharacter = apps.get_model("eveonline", "EveCharacter")
    except LookupError:
        logger.error("eveonline app not installed")
        return

    import esi as esi_module
    from esi.openapi_clients import ESIClientProvider
    esi = ESIClientProvider(
        compatibility_date=esi_module.__esi_compatibility_date__,
        ua_appname="aa-grafana-dashboard",
        ua_version="0.1.0",
        tags=["Corporation"],
    )

    corp_ids = list(
        EveCharacter.objects
        .filter(alliance_name__isnull=False)
        .exclude(alliance_name="")
        .values_list("corporation_id", flat=True)
        .distinct()
    )

    updated = 0
    failed = 0

    for corp_id in corp_ids:
        token = _get_director_token(corp_id)
        if not token:
            continue

        try:
            result = esi.client.Corporation.GetCorporationsCorporationIdMembertracking(
                corporation_id=corp_id,
                token=token,
            ).results()
        except Exception as e:
            logger.warning("ESI member tracking failed for corp %s: %s", corp_id, e)
            failed += 1
            continue

        for member in result:
            char_id = member.get("character_id")
            if not char_id:
                continue

            CorporationMemberTracking.objects.update_or_create(
                corporation_id=corp_id,
                character_id=char_id,
                defaults={
                    "logon_date": member.get("logon_date"),
                    "logoff_date": member.get("logoff_date"),
                    "ship_type_id": member.get("ship_type_id"),
                    "location_id": member.get("location_id"),
                    "start_date": member.get("start_date"),
                },
            )

        current_char_ids = [m["character_id"] for m in result if m.get("character_id")]
        CorporationMemberTracking.objects.filter(
            corporation_id=corp_id
        ).exclude(
            character_id__in=current_char_ids
        ).delete()

        updated += 1

    logger.info("Member tracking updated for %d corps (%d failed)", updated, failed)
