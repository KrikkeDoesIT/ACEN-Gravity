"""Deterministic BloodHound path detector + Finding generator.

D-0005: detection, ranking, scoring, correlation, and initial explanation are
**deterministic and template-based**. No AI. Every step is reproducible.

For the Stage 9 slice we detect the **shortest weighted attack path** to any
Tier 0 target. Caps are documented in `BLOODHOUND_ANALYZER_DESIGN.md` §11
(REVIEW_NOTES item 7 — defaults to confirm at Cycle 3):

  - max path length: 8 edges
  - top K paths per source: 3
  - top N considered overall: 50
  - top reported: 5
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import pairwise
from typing import cast

import networkx as nx

from modules.bloodhound.parsers.sharphound import ParsedGraph, SharpHoundNode

ANALYZER_VERSION = "0.1.0"

MAX_PATH_LENGTH = 8
TOP_K_PER_SOURCE = 3
TOP_N_CONSIDERED = 50
TOP_REPORTED = 5


@dataclass(frozen=True)
class PathStep:
    """One hop in an attack path."""

    from_sid: str
    from_label: str
    from_kind: str
    edge_type: str
    severity_weight: int
    to_sid: str
    to_label: str
    to_kind: str

    def as_dict(self) -> dict:
        return {
            "from_sid": self.from_sid,
            "from_label": self.from_label,
            "from_kind": self.from_kind,
            "edge_type": self.edge_type,
            "severity_weight": self.severity_weight,
            "to_sid": self.to_sid,
            "to_label": self.to_label,
            "to_kind": self.to_kind,
        }


@dataclass(frozen=True)
class AttackPath:
    """A complete deterministic path from a non-Tier-0 source to a Tier 0 target."""

    source_sid: str
    target_sid: str
    steps: tuple[PathStep, ...]
    category: str
    risk_score: int  # 0–100

    @property
    def length(self) -> int:
        return len(self.steps)

    @property
    def source_label(self) -> str:
        return self.steps[0].from_label

    @property
    def target_label(self) -> str:
        return self.steps[-1].to_label

    def as_dict(self) -> dict:
        return {
            "source_sid": self.source_sid,
            "target_sid": self.target_sid,
            "category": self.category,
            "risk_score": self.risk_score,
            "length": self.length,
            "steps": [s.as_dict() for s in self.steps],
        }


def detect_paths(
    parsed: ParsedGraph,
    *,
    max_length: int = MAX_PATH_LENGTH,
    top_k_per_source: int = TOP_K_PER_SOURCE,
    top_n: int = TOP_N_CONSIDERED,
    top_reported: int = TOP_REPORTED,
) -> list[AttackPath]:
    """Return up to `top_reported` deterministic attack paths to Tier 0.

    Algorithm:
      1. Treat the graph as weighted by 1/severity_weight (so high-severity
         edges are "shorter" → preferred).
      2. For every non-Tier-0 source identity, compute the shortest weighted
         path to every Tier 0 sink (Dijkstra). Cap by `max_length` edges.
      3. Keep top `top_k_per_source` per source by risk_score.
      4. Globally rank all candidates by risk_score descending; return the top
         `top_reported`.
    """
    graph = parsed.graph
    tier0 = parsed.tier0_sids
    nodes = parsed.nodes_by_sid

    # Re-weight: high severity → low distance, so Dijkstra prefers severe edges.
    # Also: avoid zero-weight edges by adding a small base distance.
    weighted: nx.DiGraph = nx.DiGraph()
    for u, v, edata in graph.edges(data=True):
        sev = max(int(edata.get("severity_weight", 1)), 1)
        # Distance: lower = preferred. 11 - sev keeps order, all positive.
        weighted.add_edge(u, v, distance=(11 - sev), **edata)
    for n in graph.nodes:
        if n not in weighted:
            weighted.add_node(n)

    sources = [
        sid
        for sid, node in nodes.items()
        # We seek paths *to* Tier 0 from anywhere that isn't itself Tier 0.
        # Exclude domain objects (not actors).
        if sid not in tier0 and node.kind in {"user", "computer", "group", "service_account"}
    ]

    candidates: list[AttackPath] = []
    for source in sources:
        per_source: list[AttackPath] = []
        for target in tier0:
            if target == source or target not in weighted:
                continue
            try:
                node_path = cast(
                    list[str],
                    nx.shortest_path(weighted, source=source, target=target, weight="distance"),
                )
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
            if len(node_path) - 1 > max_length:
                continue
            steps = tuple(_steps_from_nodes(node_path, weighted, nodes))
            if not steps:
                continue
            category = _categorise(steps)
            risk = _risk_score(steps, target_sid=target, nodes=nodes)
            per_source.append(
                AttackPath(
                    source_sid=source,
                    target_sid=target,
                    steps=steps,
                    category=category,
                    risk_score=risk,
                )
            )

        per_source.sort(key=lambda p: (-p.risk_score, p.length, p.target_sid))
        candidates.extend(per_source[:top_k_per_source])

    candidates.sort(key=lambda p: (-p.risk_score, p.length, p.source_sid, p.target_sid))
    return candidates[:top_n][:top_reported]


def _steps_from_nodes(
    node_path: list[str],
    graph: nx.DiGraph,
    nodes: dict[str, SharpHoundNode],
) -> list[PathStep]:
    out: list[PathStep] = []
    for u, v in pairwise(node_path):
        if not graph.has_edge(u, v):
            return []
        edata = graph.get_edge_data(u, v)
        u_node = nodes.get(u)
        v_node = nodes.get(v)
        if u_node is None or v_node is None:
            return []
        out.append(
            PathStep(
                from_sid=u,
                from_label=u_node.label,
                from_kind=u_node.kind,
                edge_type=edata.get("edge_type", "Unknown"),
                severity_weight=int(edata.get("severity_weight", 0)),
                to_sid=v,
                to_label=v_node.label,
                to_kind=v_node.kind,
            )
        )
    return out


def _categorise(steps: Iterable[PathStep]) -> str:
    """First-match priority order per REVIEW_NOTES item 8."""
    edges = [s.edge_type for s in steps]
    if any(e in {"GenericAll", "GenericWrite", "WriteDacl", "WriteOwner"} for e in edges):
        return "acl_abuse"
    if any(e in {"AllowedToDelegate", "AllowedToAct"} for e in edges):
        return "delegation"
    if any(e in {"DCSync", "GetChanges", "GetChangesAll"} for e in edges):
        return "dcsync"
    if all(e == "MemberOf" for e in edges):
        return "group_nesting_priv_esc"
    if any(e in {"ForceChangePassword", "AddMember"} for e in edges):
        return "privilege_escalation"
    return "privilege_escalation"


def _risk_score(
    steps: tuple[PathStep, ...],
    *,
    target_sid: str,
    nodes: dict[str, SharpHoundNode],
) -> int:
    """Deterministic risk score 0–100. Documented in
    `BLOODHOUND_ANALYZER_DESIGN.md` §13 (defaults to confirm at Cycle 3)."""
    if not steps:
        return 0
    # 1) Target criticality: well-known Tier 0 group RIDs → 100, others → 80.
    target_rid = target_sid.rsplit("-", 1)[-1]
    target_node = nodes.get(target_sid)
    target_kind = target_node.kind if target_node else "unknown"
    if target_rid in {"512", "519", "518"}:
        target_score = 100
    elif target_rid in {"500", "516", "517"}:
        target_score = 90
    elif target_kind == "computer":
        target_score = 80
    else:
        target_score = 70

    # 2) Edge severity contribution: max edge weight × 6, plus 2 per high-severity edge.
    max_weight = max(s.severity_weight for s in steps)
    high_count = sum(1 for s in steps if s.severity_weight >= 7)
    edge_score = max_weight * 6 + high_count * 2

    # 3) Path-length penalty: longer paths are slightly less severe.
    length_factor = max(0, 8 - (len(steps) - 1)) * 2  # 0..16 contribution

    # 4) Combine.
    raw = int(target_score * 0.6 + edge_score * 0.3 + length_factor * 0.1)
    return max(0, min(100, raw))
