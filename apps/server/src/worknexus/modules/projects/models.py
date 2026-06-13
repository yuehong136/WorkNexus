from typing import Any

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from worknexus.db import Base, EntityMixin


class Project(EntityMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (UniqueConstraint("tenant_id", "key"),)

    name: Mapped[str] = mapped_column(String(200))
    key: Mapped[str] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="active")
    owner_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    # Per-project work-item counter; bumped atomically to mint WorkItem.seq/key (work_items module).
    work_item_seq: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_by: Mapped[str | None] = mapped_column(String(32))
    updated_by: Mapped[str | None] = mapped_column(String(32))
