"""M7 dashboard intake metrics owned by the intake domain: status counts (with the
read-time expired-snooze -> new reclassification), conversion count and rate."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from worknexus.core.deps import Actor, ActorType
from worknexus.modules.intake import service
from worknexus.modules.intake.models import IntakeRequest
from worknexus.modules.intake.schemas import IntakeAcceptIn, IntakeCreateIn, IntakeStatus

pytestmark = [pytest.mark.integration, pytest.mark.p1]


def _actor(initialized: SimpleNamespace) -> Actor:
    return Actor(id=initialized.owner.id, type=ActorType.USER, tenant_id=initialized.tenant.id)


async def _create(db: AsyncSession, initialized: SimpleNamespace, title: str) -> str:
    out = await service.create_intake_request(
        db, _actor(initialized), initialized.project.id, IntakeCreateIn(title=title, description=None)
    )
    return out.id


async def test_intake_metrics_counts_and_conversion(db: AsyncSession, initialized: SimpleNamespace) -> None:
    pid = initialized.project.id
    await _create(db, initialized, "stays new")
    converted = await _create(db, initialized, "to convert")
    await service.accept_intake_request(db, _actor(initialized), converted, IntakeAcceptIn())

    # An expired snooze must be virtually counted as `new` (no row mutation by metrics).
    expired = await _create(db, initialized, "expired snooze")
    row = await db.get(IntakeRequest, expired)
    assert row is not None
    row.status = IntakeStatus.SNOOZED
    row.snooze_until = datetime.now(UTC) - timedelta(hours=1)
    await db.flush()

    m = await service.get_project_intake_metrics(db, _actor(initialized), pid)

    assert m.request_count == 3
    assert set(m.status_counts) == {str(s) for s in IntakeStatus}
    assert m.status_counts["new"] == 2  # the untouched new + the expired snooze
    assert m.status_counts["snoozed"] == 0
    assert m.status_counts["converted"] == 1
    assert m.converted_count == 1
    assert m.conversion_rate == round(1 / 3, 4)


async def test_intake_metrics_empty_project(db: AsyncSession, initialized: SimpleNamespace) -> None:
    m = await service.get_project_intake_metrics(db, _actor(initialized), initialized.project.id)
    assert m.request_count == 0
    assert m.converted_count == 0
    assert m.conversion_rate == 0.0
