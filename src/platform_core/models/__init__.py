"""Marker for the `platform_core.models` package.

Aggregating imports for Alembic autogenerate live in `platform_core.models.registry`
to avoid circular imports — submodules like `platform_core.evidence.models` legally
import from `platform_core.models.core`, and pulling all models in here would
trigger import cycles.
"""
