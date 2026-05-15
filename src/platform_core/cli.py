"""ACEN Gravity CLI — `gravity ...` commands.

For now: just the `demo load` command that loads the Contoso Corp fixture
end-to-end (Customer → Engagement → AssessmentRun → AD evidence → SharpHound
evidence → path detection → Finding generation). Idempotent.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import typer
from rich.console import Console
from rich.table import Table

from modules.ad.parsers import PrivilegedGroupsParser
from modules.bloodhound.analyzer import detect_paths
from modules.bloodhound.findings import generate_finding
from modules.bloodhound.parsers import SharpHoundParser

# Registry import wires every model onto Base.metadata before we touch the database.
from platform_core.audit.models import AuditEvent
from platform_core.db import _session_factory
from platform_core.evidence.models import Evidence
from platform_core.findings.models import Finding
from platform_core.identity.models import Identity
from platform_core.models import registry as _model_registry  # noqa: F401
from platform_core.models.core import AssessmentRun, Customer, Engagement

CONTOSO_FIXTURE: Final[Path] = (
    Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "contoso"
)

app = typer.Typer(no_args_is_help=True, add_completion=False, help="ACEN Gravity CLI.")
demo_app = typer.Typer(no_args_is_help=True, help="Demo dataset commands.")
app.add_typer(demo_app, name="demo")

console = Console()


@demo_app.command("load")
def demo_load(
    fixture_path: Path = typer.Option(
        CONTOSO_FIXTURE,
        "--fixture",
        "-f",
        help="Fixture root folder (defaults to the bundled Contoso Corp dataset).",
    ),
) -> None:
    """Load the Contoso Corp demo fixture end-to-end. Idempotent."""
    if not fixture_path.is_dir():
        raise typer.BadParameter(f"Fixture folder not found: {fixture_path}")

    Session = _session_factory()
    with Session() as session, session.begin():
        # 1. Customer / engagement / run (idempotent on slug).
        meta = json.loads((fixture_path / "customer.json").read_text(encoding="utf-8"))
        customer = _upsert_customer(session, meta["customer"])
        engagement = _upsert_engagement(session, customer, meta["engagement"])
        run = _create_run(session, engagement, meta["assessment_run"])
        console.print(
            f"[bold]Loaded:[/] customer=[cyan]{customer.slug}[/] "
            f"engagement=[cyan]{engagement.slug}[/] run=[cyan]{run.id[:8]}[/]"
        )

        # 2. AD privileged-groups evidence → Identity rows.
        ad_result = PrivilegedGroupsParser().parse(
            path=fixture_path / "ad" / "privileged-groups.json",
            session=session,
            customer_id=customer.id,
            assessment_run_id=run.id,
        )
        console.print(
            f"[bold]AD parser:[/] +{ad_result.identities_created} created, "
            f"{ad_result.identities_updated} updated, "
            f"[red]{ad_result.tier0_count}[/] Tier 0 groups"
        )

        # 3. SharpHound → graph.
        parsed = SharpHoundParser().parse(folder=fixture_path / "sharphound")
        session.add(
            Evidence(
                assessment_run_id=run.id,
                module_id=SharpHoundParser.module_id,
                evidence_type=SharpHoundParser.evidence_type,
                parser_version=parsed.parser_version,
                source_path=str(fixture_path / "sharphound"),
                payload={
                    "node_count": parsed.node_count,
                    "edge_count": parsed.edge_count,
                    "tier0_count": len(parsed.tier0_sids),
                    "tier0_sids": sorted(parsed.tier0_sids),
                },
            )
        )
        console.print(
            f"[bold]BloodHound parser:[/] {parsed.node_count} nodes, "
            f"{parsed.edge_count} edges, [red]{len(parsed.tier0_sids)}[/] Tier 0 principals"
        )

        # 4. Path detection.
        paths = detect_paths(parsed)
        console.print(f"[bold]Path detector:[/] {len(paths)} critical path(s) found")

        # 5. Identity ref lookup (SID → Identity.id).
        identity_by_sid: dict[str, str] = dict(
            session.query(Identity.sid, Identity.id)
            .filter(Identity.customer_id == customer.id)
            .all()
        )

        # 6. Generate findings.
        findings_created: list[str] = []
        for path in paths:
            refs = [
                identity_by_sid[sid]
                for sid in [path.source_sid, path.target_sid]
                if sid in identity_by_sid
            ]
            result = generate_finding(
                path=path,
                session=session,
                assessment_run_id=run.id,
                identity_refs=refs,
            )
            findings_created.append(result.finding_id)
            console.print(
                f"  • [red]{result.severity.upper():<8}[/] {result.title}"
            )

        # 7. Audit log.
        session.add(
            AuditEvent(
                actor_role="cli",
                actor_label="gravity demo load",
                customer_id=customer.id,
                engagement_id=engagement.id,
                run_id=run.id,
                event_type="demo.load",
                target_kind="assessment_run",
                target_id=run.id,
                severity="info",
                payload={
                    "ad_identities_created": ad_result.identities_created,
                    "bh_node_count": parsed.node_count,
                    "bh_edge_count": parsed.edge_count,
                    "findings_created": findings_created,
                },
            )
        )

    _print_summary()


def _upsert_customer(session, data: dict) -> Customer:
    existing = session.query(Customer).filter(Customer.slug == data["slug"]).one_or_none()
    if existing is not None:
        existing.name = data.get("name", existing.name)
        existing.notes = data.get("notes", existing.notes)
        return existing
    customer = Customer(name=data["name"], slug=data["slug"], notes=data.get("notes"))
    session.add(customer)
    session.flush()
    return customer


def _upsert_engagement(session, customer: Customer, data: dict) -> Engagement:
    existing = (
        session.query(Engagement)
        .filter(Engagement.customer_id == customer.id, Engagement.slug == data["slug"])
        .one_or_none()
    )
    if existing is not None:
        existing.name = data.get("name", existing.name)
        return existing
    engagement = Engagement(
        customer_id=customer.id,
        name=data["name"],
        slug=data["slug"],
    )
    session.add(engagement)
    session.flush()
    return engagement


def _create_run(session, engagement: Engagement, data: dict) -> AssessmentRun:
    # New run on every load (we want fresh findings); the previous run remains.
    run = AssessmentRun(engagement_id=engagement.id, name=data["name"])
    session.add(run)
    session.flush()
    return run


def _print_summary() -> None:
    Session = _session_factory()
    with Session() as session:
        n_customers = session.query(Customer).count()
        n_engagements = session.query(Engagement).count()
        n_runs = session.query(AssessmentRun).count()
        n_evidence = session.query(Evidence).count()
        n_identities = session.query(Identity).count()
        n_findings = session.query(Finding).count()
        n_audit = session.query(AuditEvent).count()

    table = Table(title="Database state after load", show_header=True, header_style="bold")
    table.add_column("Entity", style="cyan")
    table.add_column("Count", justify="right", style="green")
    for label, n in [
        ("Customers", n_customers),
        ("Engagements", n_engagements),
        ("Assessment Runs", n_runs),
        ("Evidence rows", n_evidence),
        ("Identities", n_identities),
        ("Findings", n_findings),
        ("Audit events", n_audit),
    ]:
        table.add_row(label, str(n))
    console.print(table)


if __name__ == "__main__":  # pragma: no cover
    app()
