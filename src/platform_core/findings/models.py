"""Finding model — shared across all modules.

Single shape, per `MODULE_ARCHITECTURE.md` §10. Module-specific data goes
in `payload` (JSON). For the Stage 9 slice we use the
license-aware enum values from `LICENSE_MODEL.md` §3 directly.
"""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from platform_core.db import Base
from platform_core.models.core import AssessmentRun
from platform_core.models.mixins import Timestamps, UuidPk


class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class LicenseStatus(StrEnum):
    LICENSED_ENABLED = "licensed_enabled"
    LICENSED_DISABLED = "licensed_disabled"
    LICENSED_MISCONFIGURED = "licensed_misconfigured"
    NOT_LICENSED = "not_licensed"
    REQUIRES_ADD_ON = "requires_add_on"
    AVAILABLE_IN_HIGHER_TIER = "available_in_higher_tier"
    NOT_APPLICABLE = "not_applicable"
    UNKNOWN = "unknown"


class FindingState(StrEnum):
    NEW = "new"
    TRIAGED = "triaged"
    PUBLISHED = "published"
    RETEST_REQUESTED = "retest_requested"
    CLOSED = "closed"


class CustomerVisibility(StrEnum):
    INTERNAL_ONLY = "internal_only"
    CUSTOMER_SUMMARY = "customer_summary"
    CUSTOMER_FULL = "customer_full"


class Finding(UuidPk, Timestamps, Base):
    __tablename__ = "finding"

    assessment_run_id: Mapped[str] = mapped_column(ForeignKey("assessment_run.id"), index=True)
    module_id: Mapped[str] = mapped_column(String(64), index=True)
    category: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str] = mapped_column(String(512))

    severity: Mapped[str] = mapped_column(String(16), index=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    license_status: Mapped[str] = mapped_column(String(32), default=LicenseStatus.LICENSED_ENABLED.value)

    state: Mapped[str] = mapped_column(String(32), default=FindingState.NEW.value, index=True)
    customer_visibility: Mapped[str] = mapped_column(
        String(32), default=CustomerVisibility.INTERNAL_ONLY.value, index=True
    )

    summary_internal: Mapped[str] = mapped_column(Text)
    summary_customer: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    remediation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Module-specific payload (e.g., BloodHound path steps, AD account refs).
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    # Identity UUIDs this finding relates to (cross-module join keys).
    identity_refs: Mapped[list[str]] = mapped_column(JSON, default=list)

    run: Mapped[AssessmentRun] = relationship()

    def __repr__(self) -> str:
        return f"<Finding {self.module_id}:{self.category} sev={self.severity} state={self.state}>"
