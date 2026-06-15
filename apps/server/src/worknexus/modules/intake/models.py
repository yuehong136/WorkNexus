from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from worknexus.db import Base, EntityMixin


class IntakeRequest(EntityMixin, Base):
    """A project-level inbound request awaiting triage. Provenance to a converted work item
    is carried by `converted_work_item_id` here + `WorkItem.source/source_ref_id` there — never
    a `work_item_relations` row (that table's endpoints are both work_items FKs)."""

    __tablename__ = "intake_requests"
    __table_args__ = (
        Index("ix_intake_requests_project_status", "project_id", "status"),
        UniqueConstraint("converted_work_item_id", name="uq_intake_requests_converted_work_item"),
    )

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(20), default="manual")
    source_ref_id: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default="new")
    submitter_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_category: Mapped[str | None] = mapped_column(String(40))
    suggested_type: Mapped[str | None] = mapped_column(String(20))
    suggested_priority: Mapped[str | None] = mapped_column(String(10))
    suggested_assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    triage_meta: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    duplicate_work_item_id: Mapped[str | None] = mapped_column(ForeignKey("work_items.id"))
    converted_work_item_id: Mapped[str | None] = mapped_column(ForeignKey("work_items.id"))
    snooze_until: Mapped[datetime | None] = mapped_column()
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(32))
    updated_by: Mapped[str | None] = mapped_column(String(32))
    deleted_at: Mapped[datetime | None] = mapped_column()
