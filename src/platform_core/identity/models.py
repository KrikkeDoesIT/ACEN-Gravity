"""Canonical Identity entity — cross-module join key.

The deterministic identity linker per `MODULE_ARCHITECTURE.md` §8 lands
incrementally; the slice creates Identity rows by SID for AD users and by
ObjectGUID for AD principals. UPN / on-prem-immutable-id linking arrives
when Entra module work begins.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from platform_core.db import Base
from platform_core.models.core import Customer
from platform_core.models.mixins import Timestamps, UuidPk


class Identity(UuidPk, Timestamps, Base):
    __tablename__ = "identity"

    customer_id: Mapped[str] = mapped_column(ForeignKey("customer.id"), index=True)
    canonical_kind: Mapped[str] = mapped_column(String(32))  # user / computer / service_account / group / app / unknown
    canonical_label: Mapped[str] = mapped_column(String(255))

    sid: Mapped[str | None] = mapped_column(String(184), nullable=True, index=True)
    upn: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    sam_account_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    object_guid: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    azure_object_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    is_privileged: Mapped[bool] = mapped_column(Boolean, default=False)
    is_tier0: Mapped[bool] = mapped_column(Boolean, default=False)
    is_breakglass: Mapped[bool] = mapped_column(Boolean, default=False)

    customer: Mapped[Customer] = relationship()

    def __repr__(self) -> str:
        return f"<Identity {self.canonical_kind}:{self.canonical_label}>"
