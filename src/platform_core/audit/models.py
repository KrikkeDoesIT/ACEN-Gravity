"""AuditEvent — append-only log of consequential platform actions.

Per `SECURITY_AND_GDPR.md` §6. Tamper-evident chain at MVP+ (D-0019 era).
Slice scope: capture upload, parse, evaluate, finding state changes,
visibility changes, publish events, role switches.
"""

from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from platform_core.db import Base
from platform_core.models.mixins import Timestamps, UuidPk


class AuditEvent(UuidPk, Timestamps, Base):
    __tablename__ = "audit_event"

    actor_role: Mapped[str] = mapped_column(String(64))
    actor_label: Mapped[str] = mapped_column(String(255))

    customer_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    engagement_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    event_type: Mapped[str] = mapped_column(String(64), index=True)
    target_kind: Mapped[str] = mapped_column(String(32))
    target_id: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(16), default="info")

    payload: Mapped[dict] = mapped_column(JSON, default=dict)

    def __repr__(self) -> str:
        return f"<AuditEvent {self.event_type} on {self.target_kind}:{self.target_id}>"
