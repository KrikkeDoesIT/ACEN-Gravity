"""SharpHound CE JSON parser.

Reads `users.json`, `groups.json`, `computers.json`, `domains.json` from a
folder (or extracted ZIP at MVP) and produces an in-memory `networkx`
DiGraph the analyzer can run path detection on.

Per D-0005, this is deterministic and template-based — no AI in the
parsing/detection critical path.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx

PARSER_VERSION = "0.1.0"

# Well-known RIDs for Tier 0 group SIDs (per AD_MODULE_DESIGN.md §10).
TIER0_RIDS: frozenset[str] = frozenset(
    {
        "512",  # Domain Admins
        "519",  # Enterprise Admins
        "518",  # Schema Admins
        "516",  # Domain Controllers
        "517",  # Cert Publishers
        "498",  # Enterprise Read-only Domain Controllers
        "521",  # Read-only Domain Controllers
        "500",  # Built-in Administrator
    }
)


@dataclass
class SharpHoundNode:
    sid: str
    kind: str  # user / computer / group / domain
    label: str
    highvalue: bool = False
    properties: dict = field(default_factory=dict)


@dataclass
class SharpHoundEdge:
    """Directed: `source` has a relationship that lets it act on `target`."""

    source_sid: str
    target_sid: str
    edge_type: str  # MemberOf / GenericAll / WriteDacl / GenericWrite / ...
    severity_weight: int  # 1..10 (per BLOODHOUND_ANALYZER_DESIGN.md §8)


# Edge severity weights for the slice. Documented in
# `BLOODHOUND_ANALYZER_DESIGN.md` §8; defaults are reasonable starting values
# (REVIEW_NOTES item 5 — confirm at Cycle 3 review).
EDGE_WEIGHTS: dict[str, int] = {
    "MemberOf": 1,
    "GenericAll": 9,
    "GenericWrite": 8,
    "WriteDacl": 8,
    "WriteOwner": 8,
    "Owns": 7,
    "ForceChangePassword": 7,
    "AddMember": 6,
    "AllowedToDelegate": 6,
    "AllowedToAct": 7,
    "DCSync": 10,
    "GetChanges": 9,
    "GetChangesAll": 10,
}


@dataclass
class ParsedGraph:
    """Output of the parser — a networkx DiGraph + Tier 0 SID set + node index."""

    graph: nx.DiGraph
    tier0_sids: set[str]
    nodes_by_sid: dict[str, SharpHoundNode]
    parser_version: str = PARSER_VERSION

    @property
    def node_count(self) -> int:
        return self.graph.number_of_nodes()

    @property
    def edge_count(self) -> int:
        return self.graph.number_of_edges()


class SharpHoundParser:
    """Reads a folder of SharpHound CE JSON files into a DiGraph."""

    evidence_type = "sharphound-folder"  # ZIP support arrives at MVP
    module_id = "bloodhound"

    EXPECTED_FILES: tuple[str, ...] = ("domains.json", "users.json", "groups.json", "computers.json")

    def parse(self, *, folder: Path) -> ParsedGraph:
        if not folder.is_dir():
            raise FileNotFoundError(f"SharpHound folder does not exist: {folder}")
        for fname in self.EXPECTED_FILES:
            if not (folder / fname).exists():
                raise FileNotFoundError(f"Missing expected SharpHound file: {folder / fname}")

        nodes_by_sid: dict[str, SharpHoundNode] = {}
        edges: list[SharpHoundEdge] = []

        # --- Domains ---
        domains = _load(folder / "domains.json")
        for d in domains.get("data", []):
            sid = d["ObjectIdentifier"]
            props = d.get("Properties", {})
            nodes_by_sid[sid] = SharpHoundNode(
                sid=sid,
                kind="domain",
                label=props.get("name", sid),
                highvalue=bool(props.get("highvalue")),
                properties=props,
            )

        # --- Users ---
        users = _load(folder / "users.json")
        for u in users.get("data", []):
            sid = u["ObjectIdentifier"]
            props = u.get("Properties", {})
            nodes_by_sid[sid] = SharpHoundNode(
                sid=sid,
                kind="user",
                label=props.get("samaccountname") or props.get("name") or sid,
                highvalue=bool(props.get("highvalue")) or bool(props.get("admincount")),
                properties=props,
            )
            # ACEs: principal → has-right-on → this user
            for ace in u.get("Aces", []):
                edges.extend(_ace_to_edges(target_sid=sid, ace=ace))

        # --- Computers ---
        computers = _load(folder / "computers.json")
        for c in computers.get("data", []):
            sid = c["ObjectIdentifier"]
            props = c.get("Properties", {})
            nodes_by_sid[sid] = SharpHoundNode(
                sid=sid,
                kind="computer",
                label=props.get("samaccountname") or props.get("name") or sid,
                highvalue=bool(props.get("highvalue")),
                properties=props,
            )
            for ace in c.get("Aces", []):
                edges.extend(_ace_to_edges(target_sid=sid, ace=ace))

        # --- Groups + their Members ---
        groups = _load(folder / "groups.json")
        for g in groups.get("data", []):
            sid = g["ObjectIdentifier"]
            props = g.get("Properties", {})
            nodes_by_sid[sid] = SharpHoundNode(
                sid=sid,
                kind="group",
                label=props.get("name", sid),
                highvalue=bool(props.get("highvalue")) or bool(props.get("admincount")),
                properties=props,
            )
            for member in g.get("Members", []):
                member_sid = member["ObjectIdentifier"]
                edges.append(
                    SharpHoundEdge(
                        source_sid=member_sid,
                        target_sid=sid,
                        edge_type="MemberOf",
                        severity_weight=EDGE_WEIGHTS["MemberOf"],
                    )
                )
            for ace in g.get("Aces", []):
                edges.extend(_ace_to_edges(target_sid=sid, ace=ace))

        # --- Build networkx DiGraph ---
        graph: nx.DiGraph = nx.DiGraph()
        for node in nodes_by_sid.values():
            graph.add_node(node.sid, kind=node.kind, label=node.label, highvalue=node.highvalue)
        for e in edges:
            # Skip dangling edges (principal not in the graph).
            if e.source_sid not in nodes_by_sid or e.target_sid not in nodes_by_sid:
                continue
            graph.add_edge(
                e.source_sid,
                e.target_sid,
                edge_type=e.edge_type,
                severity_weight=e.severity_weight,
            )

        # --- Tier 0 identification ---
        tier0_sids = _identify_tier0(nodes_by_sid, graph)

        return ParsedGraph(graph=graph, tier0_sids=tier0_sids, nodes_by_sid=nodes_by_sid)


def _load(path: Path) -> dict:
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _ace_to_edges(*, target_sid: str, ace: dict) -> Iterable[SharpHoundEdge]:
    """Convert a SharpHound ACE entry to a directed edge.

    ACE direction: `PrincipalSID` has `RightName` over `target_sid`.
    """
    right = ace.get("RightName")
    principal = ace.get("PrincipalSID")
    if not right or not principal:
        return ()
    weight = EDGE_WEIGHTS.get(right)
    if weight is None:
        # Unknown right — skip for the slice (don't pollute the graph).
        return ()
    return (
        SharpHoundEdge(
            source_sid=principal,
            target_sid=target_sid,
            edge_type=right,
            severity_weight=weight,
        ),
    )


def _identify_tier0(nodes: dict[str, SharpHoundNode], graph: nx.DiGraph) -> set[str]:
    """Tier 0 = well-known privileged SIDs + their transitive group members.

    Deterministic per D-0005. We do NOT use the SharpHound `highvalue` flag
    alone — well-known RIDs are the authoritative seed.
    """
    seed: set[str] = set()
    for sid in nodes:
        rid = sid.rsplit("-", 1)[-1]
        if rid in TIER0_RIDS:
            seed.add(sid)

    # Transitively expand: anything that is a member of a Tier 0 group is Tier 0.
    # Edge direction is `member -MemberOf-> group`, so we walk predecessors of
    # group nodes via MemberOf edges.
    tier0: set[str] = set(seed)
    changed = True
    while changed:
        changed = False
        for group_sid in list(tier0):
            for src, _, edata in graph.in_edges(group_sid, data=True):
                if edata.get("edge_type") != "MemberOf":
                    continue
                if src not in tier0:
                    tier0.add(src)
                    changed = True
    return tier0
