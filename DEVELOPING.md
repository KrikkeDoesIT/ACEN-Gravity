# DEVELOPING.md — quickstart

> Stage 8.1 skeleton. No business logic yet. This file walks a fresh developer from "git clone" to "app running locally with persona switch".

---

## Prerequisites

| Tool | Minimum | Why |
|---|---|---|
| Python | 3.12+ | App runtime |
| pip | recent | Package install |
| podman | 5.x | Postgres container (Stage 8.1 T-6003 — wired up after WSL2 / Virtual Machine Platform is enabled) |
| Git | any | Source control |

> **Windows note.** Podman uses WSL2, which requires the **Virtual Machine Platform** Windows feature to be enabled. If `podman machine start` fails with `HCS_E_SERVICE_NOT_AVAILABLE`, run **PowerShell as Administrator** → `wsl.exe --install --no-distribution` → reboot. If still broken, enable virtualization in BIOS.

---

## First-time setup

```powershell
# 1. Clone (or open the existing folder)
cd "c:\Github\ACEN Gravity"

# 2. Create a virtualenv (recommended)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install in editable mode with dev tooling
pip install -e ".[dev]"

# 4. Copy env template (no real secrets needed for the skeleton)
copy .env.example .env

# 5. (After WSL is fixed) bring up Postgres
podman machine start
podman compose up -d
```

---

## Run the app

```powershell
uvicorn platform_core.app:app --reload --app-dir src
```

Open <http://127.0.0.1:8000>. You will be redirected to `/login`. Pick a persona; you land on the empty overview shell with the persona-appropriate side nav.

---

## Run the checks

```powershell
# Tests
pytest

# Lint
ruff check src tests

# Format (in place)
ruff format src tests

# Type-check
mypy src tests
```

---

## Folder layout (current)

```
ACEN Gravity/
├── README.md
├── DEVELOPING.md                  ← you are here
├── pyproject.toml
├── compose.yaml                   ← podman: Postgres only
├── .env.example
├── .gitignore
├── project-management/            ← design docs
└── src/
    ├── platform_core/
    │   ├── app.py                 ← FastAPI factory
    │   ├── settings.py
    │   ├── module_registry.py     ← stub; full manifests in Stage 9
    │   └── web/
    │       ├── routes/            ← login, home
    │       ├── templates/         ← Jinja shell
    │       ├── static/            ← Tailwind output (CDN for now)
    │       └── session.py         ← persona session helpers (no real auth)
    └── modules/{ad,bloodhound,silverfort,entra}/
        ├── manifest.py            ← stub
        ├── parsers/  models/  controls/  correlations/  reports/  ui/  tests/
```

---

## What's intentionally NOT in place yet

- **Database tables.** `pyproject.toml` pulls in SQLAlchemy + Alembic + psycopg, but no models exist and no Alembic baseline has been run. T-6003 lands the day Postgres can boot.
- **Real authentication.** POC uses a session-cookie persona picker only (A-0013).
- **Module business logic.** Parsers / controls / findings / reports are Stage 9.
- **Tailwind build pipeline.** Currently served from the official Play CDN. We swap to the standalone CLI (or a real build pipeline) before component-library work begins.
- **PDF reports.** Stretch goal in POC (HTML is enough for management review).

See `project-management/TASKS.md` for the full backlog.
