"""AD module manifest stub (Stage 8.1).

The full ModuleManifest dataclass per MODULE_ARCHITECTURE.md §6 lands in Stage 9.
For now this only exposes the module id so the registry can list it.
"""

from __future__ import annotations

from typing import Final

MODULE_ID: Final[str] = "ad"
MODULE_TITLE: Final[str] = "Active Directory"
