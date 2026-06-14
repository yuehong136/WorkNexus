"""skills: skill_invocations

Revision ID: c3a7f1b9d2e4
Revises: 35d6bb78933b
Create Date: 2026-06-14 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3a7f1b9d2e4"
down_revision: str | None = "35d6bb78933b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "skill_invocations",
        sa.Column("skill_code", sa.String(length=50), nullable=False),
        sa.Column("tool_name", sa.String(length=100), nullable=False),
        sa.Column("caller_type", sa.String(length=20), nullable=False),
        sa.Column("caller_id", sa.String(length=32), nullable=False),
        sa.Column("represented_user_id", sa.String(length=32), nullable=False),
        sa.Column("agent_id", sa.String(length=32), nullable=False),
        sa.Column("project_id", sa.String(length=32), nullable=True),
        sa.Column("conversation_id", sa.String(length=64), nullable=True),
        sa.Column("run_id", sa.String(length=64), nullable=True),
        sa.Column("input_summary", sa.Text(), nullable=False),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("requires_confirmation", sa.Boolean(), nullable=False),
        sa.Column("agent_action_id", sa.String(length=32), nullable=True),
        sa.Column("audit_log_id", sa.String(length=32), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tenant_id", sa.String(length=32), nullable=False),
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["agent_id"], ["ai_agents.id"], name=op.f("fk_skill_invocations_agent_id_ai_agents")
        ),
        sa.ForeignKeyConstraint(
            ["audit_log_id"], ["audit_logs.id"], name=op.f("fk_skill_invocations_audit_log_id_audit_logs")
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["projects.id"], name=op.f("fk_skill_invocations_project_id_projects")
        ),
        sa.ForeignKeyConstraint(
            ["represented_user_id"], ["users.id"], name=op.f("fk_skill_invocations_represented_user_id_users")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_skill_invocations")),
    )
    op.create_index(
        "ix_skill_invocations_tenant_created", "skill_invocations", ["tenant_id", "created_at"], unique=False
    )
    op.create_index(
        op.f("ix_skill_invocations_represented_user_id"),
        "skill_invocations",
        ["represented_user_id"],
        unique=False,
    )
    op.create_index(op.f("ix_skill_invocations_tenant_id"), "skill_invocations", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_skill_invocations_tool_name"), "skill_invocations", ["tool_name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_skill_invocations_tool_name"), table_name="skill_invocations")
    op.drop_index(op.f("ix_skill_invocations_tenant_id"), table_name="skill_invocations")
    op.drop_index(op.f("ix_skill_invocations_represented_user_id"), table_name="skill_invocations")
    op.drop_index("ix_skill_invocations_tenant_created", table_name="skill_invocations")
    op.drop_table("skill_invocations")
