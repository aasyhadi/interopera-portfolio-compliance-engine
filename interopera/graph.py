from __future__ import annotations
import csv, json, hashlib
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

INVESTMENT_GRADE = {"AAA","AA+","AA","AA-","A+","A","A-","BBB+","BBB","BBB-"}

def is_below_ig_rating(rating: str) -> bool:
    rating = str(rating or "").strip()
    return bool(rating) and rating not in INVESTMENT_GRADE

@dataclass(frozen=True)
class Node:
    id: str
    label: str
    properties: dict[str, Any]
    provenance: dict[str, Any]

@dataclass(frozen=True)
class Edge:
    source: str
    target: str
    relation: str
    properties: dict[str, Any]
    provenance: dict[str, Any]

class ComplianceGraph:
    def __init__(self):
        self.nodes: dict[str, Node] = {}
        self.edges: list[Edge] = []

    def add_node(self, node_id: str, label: str, properties: dict[str, Any], provenance: dict[str, Any]) -> None:
        self.nodes[node_id] = Node(node_id, label, properties, provenance)

    def add_edge(self, source: str, relation: str, target: str, properties: dict[str, Any], provenance: dict[str, Any]) -> None:
        self.edges.append(Edge(source, target, relation, properties, provenance))

    def to_json(self) -> dict[str, Any]:
        return {"nodes": [asdict(n) for n in sorted(self.nodes.values(), key=lambda x: x.id)],
                "edges": [asdict(e) for e in self.edges]}

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_json(), indent=2, sort_keys=True), encoding="utf-8")

    def fingerprint(self) -> str:
        blob = json.dumps(self.to_json(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(blob.encode()).hexdigest()

    def node(self, node_id: str) -> Node:
        if node_id not in self.nodes:
            raise KeyError(f"Missing graph node: {node_id}")
        return self.nodes[node_id]

    def outgoing(self, source: str, relation: str | None = None) -> list[Edge]:
        return [e for e in self.edges if e.source == source and (relation is None or e.relation == relation)]

    def incoming(self, target: str, relation: str | None = None) -> list[Edge]:
        return [e for e in self.edges if e.target == target and (relation is None or e.relation == relation)]

    def assert_edge(self, source: str, relation: str, target: str) -> None:
        if not any(e.source == source and e.relation == relation and e.target == target for e in self.edges):
            raise ValueError(f"Missing graph edge: ({source})-[:{relation}]->({target})")

    def allocation_rule(self, asset_class: str) -> dict[str, Any]:
        return dict(self.node(f"Limit:allocation:{asset_class}").properties)

    def limit_rule(self, node_id: str) -> dict[str, Any]:
        return dict(self.node(node_id).properties)

    def positions_for_asset_class(self, asset_class: str) -> list[Node]:
        ac_id = f"AssetClass:{asset_class}"
        return sorted([self.node(e.source) for e in self.incoming(ac_id, "BELONGS_TO")], key=lambda n: n.id)

    def positions_contributing_to(self, aggregate_id: str) -> list[Node]:
        contributors = [e.source for e in self.incoming(aggregate_id, "CONTRIBUTES_TO")]
        out: list[Node] = []
        for ac_id in contributors:
            out.extend([self.node(e.source) for e in self.incoming(ac_id, "BELONGS_TO")])
        return sorted(out, key=lambda n: n.id)

    def positions_below_ig_current_rating(self) -> list[Node]:
        method_id = "FirmMethod:current_rating_below_ig"
        return sorted([self.node(e.source) for e in self.incoming(method_id, "CURRENT_RATING_BELOW_IG")], key=lambda n: n.id)

    def issuer_for_position(self, position: Node) -> Node:
        edges = self.outgoing(position.id, "ISSUED_BY")
        if not edges:
            raise ValueError(f"Position has no ISSUED_BY edge: {position.id}")
        return self.node(edges[0].target)

    def parent_for_issuer(self, issuer: Node) -> Node | None:
        edges = self.outgoing(issuer.id, "ROLLS_UP_TO")
        return self.node(edges[0].target) if edges else None

    def positions_by_issuer_type(self, issuer_type: str) -> list[Node]:
        out = []
        for n in self.nodes.values():
            if n.label == "Position" and self.issuer_for_position(n).properties.get("issuer_type") == issuer_type:
                out.append(n)
        return sorted(out, key=lambda n: n.id)

    def positions_for_issuer_name(self, issuer_name: str, issuer_type: str | None = None) -> list[Node]:
        out = []
        for n in self.nodes.values():
            if n.label != "Position":
                continue
            issuer = self.issuer_for_position(n)
            if issuer.properties.get("name") == issuer_name and (issuer_type is None or issuer.properties.get("issuer_type") == issuer_type):
                out.append(n)
        return sorted(out, key=lambda n: n.id)

    def positions_for_parent_issuer(self, parent_name: str, issuer_type: str | None = None) -> list[Node]:
        out = []
        for n in self.nodes.values():
            if n.label != "Position":
                continue
            issuer = self.issuer_for_position(n)
            parent = self.parent_for_issuer(issuer)
            name = parent.properties.get("name") if parent else issuer.properties.get("name")
            if name == parent_name and (issuer_type is None or issuer.properties.get("issuer_type") == issuer_type):
                out.append(n)
        return sorted(out, key=lambda n: n.id)

    def citation_for_supported_node(self, node_id: str) -> dict[str, Any]:
        edges = self.outgoing(node_id, "SUPPORTED_BY")
        if not edges:
            raise ValueError(f"Node has no provenance source chunk: {node_id}")
        source_node = self.node(edges[0].target)
        c = dict(source_node.properties)
        return {k: c[k] for k in ["source_doc", "page", "chunk_id", "passage_summary"]}

# In production this is extracted from sample_fund_guidelines.pdf and human-approved.
# For the take-home sample it is represented as approved graph seed data so the
# computation layer can read rules from the graph rather than Python constants.
APPROVED_GUIDELINE_RULES = {
    "allocation_limits": {
        "Singapore Government Securities": {"min": 20.0, "max": 60.0, "limit": "20–60%"},
        "MAS Bills": {"min": 0.0, "max": 40.0, "limit": "0–40%"},
        "Investment Grade Corporate Bonds": {"min": 10.0, "max": 50.0, "limit": "10–50%"},
        "High Yield Bonds": {"min": 0.0, "max": 15.0, "limit": "0–15%"},
        "Foreign Currency Bonds": {"min": 0.0, "max": 20.0, "limit": "0–20%"},
        "Structured Credit": {"min": 0.0, "max": 10.0, "display_name": "Structured Credit (ABS/MBS)", "limit": "0–10%"},
        "Cash & Cash Equivalents": {"min": 5.0, "max": 25.0, "limit": "min 5%"},
    },
    "limits": {
        "Aggregate:non_ig": {"cap": 20.0, "limit": "max 20%"},
        "Limit:single_corporate_issuer": {"cap": 8.0, "limit": "max 8%"},
        "Limit:gre_issuer": {"cap": 12.0, "limit": "max 12%"},
        "Limit:liquidity_normal": {"floor": 25.0, "limit": "min 25%"},
        "Limit:modified_duration": {"min": 2.0, "max": 6.5, "limit": "2.0–6.5 yrs"},
        "Limit:dv01": {"cap": 85000.0, "limit": "max 85,000"},
    },
}

def build_graph(root: Path, cfg: dict[str, Any]) -> ComplianceGraph:
    chunks = cfg["source_chunks"]
    g = ComplianceGraph()
    for key, data in chunks.items():
        g.add_node(f"SourceChunk:{key}", "SourceChunk", data, data)
    g.add_node("Fund:Meridian Fixed Income Fund", "Fund", {"base_currency": "SGD"}, chunks["allocation_limits"])
    for asset_class, rule in APPROVED_GUIDELINE_RULES["allocation_limits"].items():
        display = rule.get("display_name", asset_class)
        ac_id = f"AssetClass:{asset_class}"
        lim_id = f"Limit:allocation:{asset_class}"
        g.add_node(ac_id, "AssetClass", {"name": asset_class, "display_name": display}, chunks["allocation_limits"])
        g.add_node(lim_id, "Limit", {"kind": "allocation", **rule}, chunks["allocation_limits"])
        g.add_edge(lim_id, "APPLIES_TO", ac_id, {}, chunks["allocation_limits"])
        g.add_edge(lim_id, "SUPPORTED_BY", "SourceChunk:allocation_limits", {}, chunks["allocation_limits"])
    for node_id, props, prov_key in [
        ("Aggregate:non_ig", APPROVED_GUIDELINE_RULES["limits"]["Aggregate:non_ig"], "aggregate_non_ig"),
        ("Limit:single_corporate_issuer", APPROVED_GUIDELINE_RULES["limits"]["Limit:single_corporate_issuer"], "concentration"),
        ("Limit:gre_issuer", APPROVED_GUIDELINE_RULES["limits"]["Limit:gre_issuer"], "concentration"),
        ("Limit:liquidity_normal", APPROVED_GUIDELINE_RULES["limits"]["Limit:liquidity_normal"], "liquidity"),
        ("Limit:modified_duration", APPROVED_GUIDELINE_RULES["limits"]["Limit:modified_duration"], "market_risk"),
        ("Limit:dv01", APPROVED_GUIDELINE_RULES["limits"]["Limit:dv01"], "market_risk"),
    ]:
        g.add_node(node_id, "Limit" if node_id.startswith("Limit") else "Aggregate", props, chunks[prov_key])
        g.add_edge(node_id, "SUPPORTED_BY", f"SourceChunk:{prov_key}", {}, chunks[prov_key])
    for ac in ["High Yield Bonds", "Structured Credit"]:
        g.add_edge(f"AssetClass:{ac}", "CONTRIBUTES_TO", "Aggregate:non_ig", {}, chunks["aggregate_non_ig"])
    g.add_node("Aggregate:liquid_assets", "Aggregate", {"floor": 25.0, "limit": "min 25%"}, chunks["liquidity"])
    g.add_edge("Aggregate:liquid_assets", "SUPPORTED_BY", "SourceChunk:liquidity", {}, chunks["liquidity"])
    for ac in ["Singapore Government Securities", "MAS Bills", "Cash & Cash Equivalents"]:
        g.add_edge(f"AssetClass:{ac}", "CONTRIBUTES_TO", "Aggregate:liquid_assets", {}, chunks["liquidity"])
    for metric_id, limit_id in [("Metric:weighted_duration", "Limit:modified_duration"), ("Metric:dv01", "Limit:dv01")]:
        g.add_node(metric_id, "Metric", {"name": metric_id.split(":", 1)[1]}, chunks["market_risk"])
        g.add_edge(metric_id, "TESTED_AGAINST", limit_id, {}, chunks["market_risk"])
    if cfg.get("non_ig_method") == "current_rating_below_ig_or_asset_class":
        g.add_node("FirmMethod:current_rating_below_ig", "FirmMethod", {"method": cfg["non_ig_method"]}, chunks["firm_b_non_ig"])
        g.add_edge("FirmMethod:current_rating_below_ig", "SUPPORTED_BY", "SourceChunk:firm_b_non_ig", {}, chunks["firm_b_non_ig"])
    if cfg.get("gre_concentration_method") == "parent_issuer":
        g.add_node("FirmMethod:gre_parent_issuer", "FirmMethod", {"method": cfg["gre_concentration_method"]}, chunks["firm_b_gre"])
        g.add_edge("FirmMethod:gre_parent_issuer", "SUPPORTED_BY", "SourceChunk:firm_b_gre", {}, chunks["firm_b_gre"])
    holdings_path = root / "sample_docs" / "sample_holdings.csv"
    with open(holdings_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pos = f"Position:{row['instrument_id']}"
            issuer = f"Issuer:{row['issuer_name']}"
            ac = f"AssetClass:{row['asset_class']}"
            g.add_node(pos, "Position", row, chunks["holdings"])
            if issuer not in g.nodes:
                g.add_node(issuer, "Issuer", {"name": row["issuer_name"], "issuer_type": row["issuer_type"]}, chunks["holdings"])
            g.add_edge(pos, "BELONGS_TO", ac, {}, chunks["holdings"])
            g.add_edge(pos, "ISSUED_BY", issuer, {}, chunks["holdings"])
            g.add_edge(pos, "HAS_MARKET_VALUE_AND_DURATION", "Metric:weighted_duration", {}, chunks["holdings"])
            g.add_edge(pos, "HAS_MARKET_VALUE_AND_DURATION", "Metric:dv01", {}, chunks["holdings"])
            if cfg.get("non_ig_method") == "current_rating_below_ig_or_asset_class" and is_below_ig_rating(row.get("credit_rating", "")):
                g.add_edge(pos, "CURRENT_RATING_BELOW_IG", "FirmMethod:current_rating_below_ig", {}, chunks["firm_b_non_ig"])
            parent = row.get("parent_issuer") or ""
            if parent:
                pid = f"ParentIssuer:{parent}"
                if pid not in g.nodes:
                    g.add_node(pid, "ParentIssuer", {"name": parent}, chunks["holdings"])
                g.add_edge(issuer, "ROLLS_UP_TO", pid, {}, chunks["holdings"])
    return g
