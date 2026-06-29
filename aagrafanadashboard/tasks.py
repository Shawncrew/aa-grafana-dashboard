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
            if "304" in str(e) or "NotModified" in type(e).__name__:
                logger.debug("ESI 304 for corp %s, skipping", corp_id)
                continue
            logger.warning("ESI member tracking failed for corp %s: %s", corp_id, e)
            failed += 1
            continue

        for member in result:
            char_id = getattr(member, "character_id", None)
            if not char_id:
                continue

            CorporationMemberTracking.objects.update_or_create(
                corporation_id=corp_id,
                character_id=char_id,
                defaults={
                    "logon_date": getattr(member, "logon_date", None),
                    "logoff_date": getattr(member, "logoff_date", None),
                    "ship_type_id": getattr(member, "ship_type_id", None),
                    "location_id": getattr(member, "location_id", None),
                    "start_date": getattr(member, "start_date", None),
                },
            )

        current_char_ids = [getattr(m, "character_id", None) for m in result if getattr(m, "character_id", None)]
        CorporationMemberTracking.objects.filter(
            corporation_id=corp_id
        ).exclude(
            character_id__in=current_char_ids
        ).delete()

        updated += 1

    logger.info("Member tracking updated for %d corps (%d failed)", updated, failed)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_character_affiliations(self):
    """Update corp/alliance for all characters using public ESI affiliation endpoint."""
    try:
        EveCharacter = apps.get_model("eveonline", "EveCharacter")
        EveCorporationInfo = apps.get_model("eveonline", "EveCorporationInfo")
        EveAllianceInfo = apps.get_model("eveonline", "EveAllianceInfo")
    except LookupError:
        logger.error("eveonline app not installed")
        return

    import requests as http_requests

    all_chars = list(
        EveCharacter.objects.values_list("character_id", flat=True)
    )

    CHUNK_SIZE = 1000
    updated = 0
    errors = 0

    for i in range(0, len(all_chars), CHUNK_SIZE):
        chunk = all_chars[i:i + CHUNK_SIZE]
        try:
            resp = http_requests.post(
                "https://esi.evetech.net/latest/characters/affiliation/",
                json=chunk,
                timeout=30,
            )
            resp.raise_for_status()
            result = resp.json()
        except Exception as e:
            logger.warning("ESI affiliation failed for chunk %d: %s", i, e)
            errors += 1
            continue

        corp_cache = {}
        alliance_cache = {}

        for entry in result:
            char_id = entry.get("character_id")
            corp_id = entry.get("corporation_id")
            alliance_id = entry.get("alliance_id")
            if not char_id or not corp_id:
                continue

            try:
                char = EveCharacter.objects.get(character_id=char_id)
            except EveCharacter.DoesNotExist:
                continue

            if char.corporation_id == corp_id:
                continue

            if corp_id not in corp_cache:
                corp_info = EveCorporationInfo.objects.filter(
                    corporation_id=corp_id
                ).first()
                corp_cache[corp_id] = corp_info

            corp_info = corp_cache[corp_id]
            corp_name = corp_info.corporation_name if corp_info else str(corp_id)
            corp_ticker = corp_info.corporation_ticker if corp_info else ""

            alliance_name = ""
            if alliance_id:
                if alliance_id not in alliance_cache:
                    alliance_info = EveAllianceInfo.objects.filter(
                        alliance_id=alliance_id
                    ).first()
                    alliance_cache[alliance_id] = alliance_info
                alliance_info = alliance_cache[alliance_id]
                alliance_name = alliance_info.alliance_name if alliance_info else ""

            logger.info(
                "Updating %s: corp %s -> %s, alliance %s -> %s",
                char.character_name,
                char.corporation_name, corp_name,
                char.alliance_name, alliance_name,
            )

            char.corporation_id = corp_id
            char.corporation_name = corp_name
            char.corporation_ticker = corp_ticker
            char.alliance_id = alliance_id
            char.alliance_name = alliance_name
            char.save()
            updated += 1

    logger.info("Character affiliations refreshed: %d updated, %d errors", updated, errors)
