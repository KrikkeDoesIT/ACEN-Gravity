"""Core platform entities for the POC V1 vertical slice.

Per `WORKING_APPROACH.md` §12 (simplified data model) and
`MODULE_ARCHITECTURE.md` §16 (slice scope). The full data model expands
in MVP — we don't over-normalise here.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from platform_core.db import Base
from platform_core.models.mixins import Timestamps, UuidPk


class Customer(UuidPk, Timestamps, Base):
    __tablename__ = "customer"

    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    engagements: Mapped[list[Engagement]] = relationship(
        back_populates="customer",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Customer {self.slug}>"


class Engagement(UuidPk, Timestamps, Base):
    __tablename__ = "engagement"

    customer_id: Mapped[str] = mapped_column(ForeignKey("customer.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(64), index=True)

    customer: Mapped[Customer] = relationship(back_populates="engagements")
    runs: Mapped[list[AssessmentRun]] = relationship(
        back_populates="engagement",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Engagement {self.customer.slug if self.customer else '?'} / {self.slug}>"


class AssessmentRun(UuidPk, Timestamps, Base):
    __tablename__ = "assessment_run"

    engagement_id: Mapped[str] = mapped_column(ForeignKey("engagement.id"), index=True)
    name: Mapped[str] = mapped_column(String(255))

    engagement: Mapped[Engagement] = relationship(back_populates="runs")

    def __repr__(self) -> str:
        return f"<AssessmentRun {self.name}>"
