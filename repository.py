from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from crm.models import Prospect

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ACTIVITY_PREFIX = "[AI_OUTREACH]"


@dataclass(frozen=True, slots=True)
class ProspectData:
    id: int
    company_name: str
    contact_name: str
    contact_email: str
    segment: str
    team_size: str
    region: str
    source: str
    notes: str


def setup_django() -> None:
    if str(PROJECT_ROOT) not in sys.path:
        sys.path.insert(0, str(PROJECT_ROOT))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django
    from django.apps import apps

    if not apps.ready:
        django.setup()


def _to_data(prospect: "Prospect") -> ProspectData:
    return ProspectData(
        id=prospect.pk,
        company_name=prospect.company_name.strip(),
        contact_name=prospect.contact_name.strip(),
        contact_email=prospect.contact_email.strip(),
        segment=prospect.segment.strip(),
        team_size=prospect.get_team_size_display() if prospect.team_size else "",
        region=prospect.region.strip(),
        source=prospect.source.strip(),
        notes=prospect.notes.strip()[:2000],
    )


def get_candidates(*, limit: int, prospect_id: int | None = None) -> list[ProspectData]:
    setup_django()
    from django.db.models import Exists, OuterRef

    from crm.models import Activity, Prospect

    prior_ai_email = Activity.objects.filter(
        prospect_id=OuterRef("pk"),
        type=Activity.Type.EMAIL,
        notes__startswith=ACTIVITY_PREFIX,
    )
    queryset = (
        Prospect.objects.filter(status=Prospect.Status.NEW)
        .exclude(contact_email="")
        .annotate(has_ai_email=Exists(prior_ai_email))
        .filter(has_ai_email=False)
        .order_by("created_at")
    )

    if prospect_id is not None:
        queryset = queryset.filter(pk=prospect_id)

    return [_to_data(prospect) for prospect in queryset[:limit]]


def count_sent_today() -> int:
    setup_django()
    from django.utils import timezone

    from crm.models import Activity

    today = timezone.localdate()
    return Activity.objects.filter(
        type=Activity.Type.EMAIL,
        notes__startswith=ACTIVITY_PREFIX,
        occurred_at__date=today,
    ).count()


def record_sent(prospect_id: int, subject: str) -> None:
    setup_django()
    from django.db import transaction
    from django.utils import timezone

    from crm.models import Activity, Prospect

    with transaction.atomic():
        prospect = Prospect.objects.select_for_update().get(pk=prospect_id)
        Activity.objects.create(
            prospect=prospect,
            type=Activity.Type.EMAIL,
            occurred_at=timezone.now(),
            notes=f"{ACTIVITY_PREFIX} Sent. Subject: {subject[:100]}",
        )
        if prospect.status == Prospect.Status.NEW:
            prospect.status = Prospect.Status.CONTACTED
            prospect.save(update_fields=["status", "updated_at"])
