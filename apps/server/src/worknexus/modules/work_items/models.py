from datetime import datetime
from typing import Any

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from worknexus.db import Base, EntityMixin


class WorkItem(EntityMixin, Base):
    __tablename__ = "work_items"
    __table_args__ = (
        UniqueConstraint("project_id", "seq", name="uq_work_items_project_seq"),
        UniqueConstraint("project_id", "key", name="uq_work_items_project_key"),
        Index("ix_work_items_project_status", "project_id", "status"),
    )

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    seq: Mapped[int] = mapped_column(Integer)
    key: Mapped[str] = mapped_column(String(40))
    type: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="backlog")
    priority: Mapped[str] = mapped_column(String(10), default="medium")
    assignee_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    reporter_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    due_at: Mapped[datetime | None] = mapped_column()
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    source: Mapped[str] = mapped_column(String(20), default="manual")
    source_ref_id: Mapped[str | None] = mapped_column(String(64))
    ai_summary: Mapped[str | None] = mapped_column(Text)
    acceptance_criteria: Mapped[str | None] = mapped_column(Text)
    custom_fields: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_by: Mapped[str | None] = mapped_column(String(32))
    updated_by: Mapped[str | None] = mapped_column(String(32))
    deleted_at: Mapped[datetime | None] = mapped_column()


class WorkItemComment(EntityMixin, Base):
    __tablename__ = "work_item_comments"

    work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.id", ondelete="CASCADE"), index=True)
    author_type: Mapped[str] = mapped_column(String(20))
    author_id: Mapped[str | None] = mapped_column(String(32))
    body: Mapped[str] = mapped_column(Text)


class WorkItemActivity(EntityMixin, Base):
    """In-app timeline — distinct from audit_logs (the security audit trail)."""

    __tablename__ = "work_item_activities"

    work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.id", ondelete="CASCADE"), index=True)
    actor_type: Mapped[str] = mapped_column(String(20))
    actor_id: Mapped[str | None] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(50))
    field: Mapped[str | None] = mapped_column(String(50))
    before: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after: Mapped[dict[str, Any] | None] = mapped_column(JSONB)


class WorkItemRelation(EntityMixin, Base):
    __tablename__ = "work_item_relations"
    __table_args__ = (
        UniqueConstraint(
            "source_work_item_id", "target_work_item_id", "type", name="uq_work_item_relations_src_tgt_type"
        ),
        CheckConstraint("source_work_item_id <> target_work_item_id", name="no_self_relation"),
    )

    source_work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.id", ondelete="CASCADE"), index=True)
    target_work_item_id: Mapped[str] = mapped_column(ForeignKey("work_items.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(30))
    created_by: Mapped[str | None] = mapped_column(String(32))
