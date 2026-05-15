"""Import this module exactly once at process start (Alembic env.py, CLI, app
factory) to register every SQLAlchemy model on `Base.metadata`.

Do NOT import individual symbols from this module — that defeats the purpose.
Use the canonical module-local imports (e.g., `from platform_core.findings.models
import Finding`) elsewhere.
"""

from __future__ import annotations

from platform_core.audit.models import AuditEvent as _AuditEvent  # noqa: F401
from platform_core.evidence.models import Evidence as _Evidence  # noqa: F401
from platform_core.findings.models import Finding as _Finding  # noqa: F401
from platform_core.identity.models import Identity as _Identity  # noqa: F401
from platform_core.models.core import (  # noqa: F401
    AssessmentRun as _AssessmentRun,
)
