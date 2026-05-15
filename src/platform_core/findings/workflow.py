"""Finding workflow — state machine + visibility transitions + audit writes.

Slice scope per `WORKING_APPROACH.md` §6 / `TASKS.md` Stage 9 Chunk B:
  new → triaged → published → retest_requested → closed
                       │             │
                       └─ → triaged ─┘   (rollback / re-open)

All transitions are explicit (no silent allow-anything). All transitions
write an `AuditEvent`. Only the consultant persona may perform these
transitions — enforcement lives in the route layer; this module is
authority-agnostic.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from sqlalchemy.orm import Session

from platform_core.audit.models import AuditEvent
from platform_core.findings.models import (
    CustomerVisibility,
    Finding,
    FindingState,
)

# Allowed forward + rollback transitions for the slice.
ALLOWED_TRANSITIONS: Final[dict[str, frozenset[str]]] = {
    FindingState.NEW.value: frozenset(
        {FindingState.TRIAGED.value, FindingState.CLOSED.value}
    ),
    FindingState.TRIAGED.value: frozenset(
        {
            FindingState.NEW.value,
            FindingState.PUBLISHED.value,
            FindingState.CLOSED.value,
        }
    ),
    FindingState.PUBLISHED.value: frozenset(
        {
            FindingState.TRIAGED.value,
            FindingState.RETEST_REQUESTED.value,
            FindingState.CLOSED.value,
        }
    ),
    FindingState.RETEST_REQUESTED.value: frozenset(
        {FindingState.TRIAGED.value, FindingState.CLOSED.value}
    ),
    FindingState.CLOSED.value: frozenset({FindingState.TRIAGED.value}),
}


VISIBILITY_VALUES: Final[frozenset[str]] = frozenset(
    v.value for v in CustomerVisibility
)


@dataclass(frozen=True)
class TransitionError(Exception):
    """Raised on invalid state / visibility transitions. Carries an HTTP-friendly message."""

    message: str
    code: str = "invalid_transition"

    def __str__(self) -> str:  # pragma: no cover
        return self.message


def is_transition_allowed(current: str, target: str) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())


def transition_state(
    *,
    session: Session,
    finding: Finding,
    new_state: str,
    actor_role: str,
    actor_label: str,
    customer_id: str | None,
    engagement_id: str | None,
    run_id: str | None,
) -> Finding:
    """Move a Finding to `new_state`. Raises `TransitionError` if not allowed."""
    if new_state == finding.state:
        return finding
    if not is_transition_allowed(finding.state, new_state):
        raise TransitionError(
            message=(
                f"State transition not allowed: {finding.state} → {new_state}. "
                f"From {finding.state}, valid targets are: "
                f"{sorted(ALLOWED_TRANSITIONS.get(finding.state, []))}"
            )
        )
    previous = finding.state
    finding.state = new_state

    session.add(
        AuditEvent(
            actor_role=actor_role,
            actor_label=actor_label,
            customer_id=customer_id,
            engagement_id=engagement_id,
            run_id=run_id,
            event_type="finding.state_change",
            target_kind="finding",
            target_id=finding.id,
            severity="notable",
            payload={
                "from": previous,
                "to": new_state,
                "title": finding.title,
                "module_id": finding.module_id,
            },
        )
    )
    return finding


def set_visibility(
    *,
    session: Session,
    finding: Finding,
    new_visibility: str,
    actor_role: str,
    actor_label: str,
    customer_id: str | None,
    engagement_id: str | None,
    run_id: str | None,
) -> Finding:
    """Change customer_visibility. Always allowed for a consultant role; this
    function does NOT enforce role checks (caller does)."""
    if new_visibility not in VISIBILITY_VALUES:
        raise TransitionError(
            message=f"Unknown customer_visibility value: {new_visibility!r}",
            code="invalid_visibility",
        )
    if new_visibility == finding.customer_visibility:
        return finding
    previous = finding.customer_visibility
    finding.customer_visibility = new_visibility

    session.add(
        AuditEvent(
            actor_role=actor_role,
            actor_label=actor_label,
            customer_id=customer_id,
            engagement_id=engagement_id,
            run_id=run_id,
            event_type="finding.visibility_change",
            target_kind="finding",
            target_id=finding.id,
            severity="security",
            payload={
                "from": previous,
                "to": new_visibility,
                "title": finding.title,
                "module_id": finding.module_id,
            },
        )
    )
    return finding


@dataclass(frozen=True)
class PublishResult:
    finding: Finding
    state_changed: bool
    visibility_changed: bool


def publish_finding(
    *,
    session: Session,
    finding: Finding,
    visibility: str,
    actor_role: str,
    actor_label: str,
    customer_id: str | None,
    engagement_id: str | None,
    run_id: str | None,
) -> PublishResult:
    """Composite action — set visibility (if changed) AND mark state=published.

    The default UI sequence: consultant picks visibility (customer_summary or
    customer_full), clicks Publish. This function does both atomically and
    writes the corresponding audit events plus a `finding.publish` event.
    """
    if visibility not in {
        CustomerVisibility.CUSTOMER_SUMMARY.value,
        CustomerVisibility.CUSTOMER_FULL.value,
    }:
        raise TransitionError(
            message=(
                "Publishing requires customer_summary or customer_full "
                f"visibility; got {visibility!r}."
            ),
            code="cannot_publish_internal_only",
        )

    visibility_changed = finding.customer_visibility != visibility
    if visibility_changed:
        set_visibility(
            session=session,
            finding=finding,
            new_visibility=visibility,
            actor_role=actor_role,
            actor_label=actor_label,
            customer_id=customer_id,
            engagement_id=engagement_id,
            run_id=run_id,
        )

    state_changed = finding.state != FindingState.PUBLISHED.value
    if state_changed:
        transition_state(
            session=session,
            finding=finding,
            new_state=FindingState.PUBLISHED.value,
            actor_role=actor_role,
            actor_label=actor_label,
            customer_id=customer_id,
            engagement_id=engagement_id,
            run_id=run_id,
        )

    # Composite publish event so the audit log clearly records the intent.
    session.add(
        AuditEvent(
            actor_role=actor_role,
            actor_label=actor_label,
            customer_id=customer_id,
            engagement_id=engagement_id,
            run_id=run_id,
            event_type="finding.publish",
            target_kind="finding",
            target_id=finding.id,
            severity="security",
            payload={
                "visibility": visibility,
                "title": finding.title,
                "module_id": finding.module_id,
            },
        )
    )

    return PublishResult(
        finding=finding,
        state_changed=state_changed,
        visibility_changed=visibility_changed,
    )
