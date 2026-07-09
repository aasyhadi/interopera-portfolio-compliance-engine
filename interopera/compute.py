from __future__ import annotations
import math, re
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any
from .graph import ComplianceGraph, Node

INVESTMENT_GRADE = {"AAA","AA+","AA","AA-","A+","A","A-","BBB+","BBB","BBB-"}


def pct(n: float, d: float) -> float:
    return n / d * 100.0


def round1(x: float) -> str:
    return f"{Decimal(str(x)).quantize(Decimal('0.1'), rounding=ROUND_HALF_UP)}%"


def round2_num(x: float) -> str:
    return f"{Decimal(str(x)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def money0(x: float) -> str:
    return f"SGD {int(Decimal(str(x)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)):,} / bp"


def util(value: float, limit: float, cfg: dict[str, Any]) -> str:
    ratio = value / limit * 100.0
    if cfg.get("utilization_style") == "truncated_bps":
        return f"{math.trunc(ratio * 100)} bps"
    return round1(ratio)


def mv(position: Node) -> float:
    return float(position.properties["market_value_sgd"])


def duration(position: Node) -> float:
    return float(position.properties["modified_duration"])


def status_range(value: float, mn: float | None, mx: float | None) -> str:
    if mn is not None and value < mn:
        return "BREACH"
    if mx is not None and value > mx:
        return "BREACH"
    if mx is not None and abs(value - mx) < 1e-9:
        return "AT LIMIT"
    if mn is not None and abs(value - mn) < 1e-9:
        return "AT LIMIT"
    return "OK"


def citation(graph: ComplianceGraph, node_id: str) -> dict[str, Any]:
    return graph.citation_for_supported_node(node_id)


def edge(source: str, relation: str, target: str) -> dict[str, str]:
    return {"source": source, "relation": relation, "target": target}


def figure(
    name: str,
    section: str,
    metric: str,
    value: str,
    limit: str,
    utilization: str,
    status: str,
    graph_path: str,
    citation_obj: dict[str, Any],
    components: list[str] | None = None,
    rule_id: str | None = None,
    graph_edges: list[dict[str, str]] | None = None,
    calculation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not graph_path or not citation_obj:
        raise ValueError(f"Figure {name} is not traceable")
    return {
        "figure": name,
        "section": section,
        "metric": metric,
        "value": value,
        "limit": limit,
        "utilization": utilization,
        "status": status,
        "graph_path": graph_path,
        "graph_edges": graph_edges or [],
        "citation": citation_obj,
        "components": components or [],
        "config_rule": rule_id,
        "calculation": calculation or {},
    }


def position_rows(positions: list[Node]) -> list[dict[str, Any]]:
    return [
        {
            "instrument_id": p.properties["instrument_id"],
            "instrument_name": p.properties.get("instrument_name", ""),
            "market_value_sgd": mv(p),
            "asset_class": p.properties.get("asset_class", ""),
            "issuer_name": p.properties.get("issuer_name", ""),
            "credit_rating": p.properties.get("credit_rating", ""),
            "modified_duration": duration(p),
        }
        for p in positions
    ]


def compute_figures(root: Path, graph: ComplianceGraph, cfg: dict[str, Any]) -> list[dict[str, Any]]:
    del root  # the computation layer reads from graph nodes/edges, not source files directly
    positions = sorted([n for n in graph.nodes.values() if n.label == "Position"], key=lambda n: n.id)
    nav = sum(mv(p) for p in positions)
    figs: list[dict[str, Any]] = []

    report_rows = [
        ("Singapore Government Securities", "Singapore Government Securities"),
        ("MAS Bills", "MAS Bills"),
        ("Investment Grade Corporate Bonds", "Investment Grade Corporate Bonds"),
        ("High Yield Bonds", "High Yield Bonds"),
        ("Foreign Currency Bonds", "Foreign Currency Bonds (hedged)"),
        ("Structured Credit", "Structured Credit (ABS/MBS)"),
        ("Cash & Cash Equivalents", "Cash & Cash Equivalents"),
    ]

    for ac, metric in report_rows:
        limit_id = f"Limit:allocation:{ac}"
        ac_id = f"AssetClass:{ac}"
        rule = graph.allocation_rule(ac)
        graph.assert_edge(limit_id, "APPLIES_TO", ac_id)
        ac_positions = graph.positions_for_asset_class(ac)
        numerator = sum(mv(p) for p in ac_positions)
        val = pct(numerator, nav)
        st = status_range(val, rule.get("min"), rule.get("max"))
        utilization = "n/a" if ac == "Cash & Cash Equivalents" else util(val, float(rule["max"]), cfg)
        figs.append(figure(
            f"allocation_{re.sub('[^a-z0-9]+','_', ac.lower()).strip('_')}",
            "Allocation",
            metric,
            round1(val),
            rule["limit"],
            utilization,
            st,
            f"({limit_id})-[:APPLIES_TO]->({ac_id})<-[:BELONGS_TO]-(Position:{','.join(p.properties['instrument_id'] for p in ac_positions)})",
            citation(graph, limit_id),
            [p.properties["instrument_id"] for p in ac_positions],
            "allocation_limits",
            [edge(limit_id, "APPLIES_TO", ac_id)] + [edge(p.id, "BELONGS_TO", ac_id) for p in ac_positions],
            {"formula": "sum(asset_class_market_value) / total_nav * 100", "numerator": numerator, "denominator": nav, "positions": position_rows(ac_positions)},
        ))

    # Aggregate non-IG from graph aggregate contributors. Firm B adds graph edges to current-rating fallen angels.
    base_non_ig = graph.positions_contributing_to("Aggregate:non_ig")
    contributors_by_id = {p.id: p for p in base_non_ig}
    graph_edges = [edge("AssetClass:High Yield Bonds", "CONTRIBUTES_TO", "Aggregate:non_ig"), edge("AssetClass:Structured Credit", "CONTRIBUTES_TO", "Aggregate:non_ig")]
    src_node = "Aggregate:non_ig"
    rule_id = "firm_A.non_ig.asset_class_contributors"
    path = "(AssetClass:High Yield Bonds)-[:CONTRIBUTES_TO]->(Aggregate:non_ig)<-[:CONTRIBUTES_TO]-(AssetClass:Structured Credit)"
    if cfg["non_ig_method"] == "current_rating_below_ig_or_asset_class":
        for p in graph.positions_below_ig_current_rating():
            contributors_by_id[p.id] = p
            graph_edges.append(edge(p.id, "CURRENT_RATING_BELOW_IG", "FirmMethod:current_rating_below_ig"))
        src_node = "SourceChunk:firm_b_non_ig"
        rule_id = "firm_B.non_ig.current_rating_below_ig_or_asset_class"
        path = "(Position:*)-[:BELONGS_TO]->(AssetClass:High Yield Bonds|Structured Credit)-[:CONTRIBUTES_TO]->(Aggregate:non_ig); plus (Position:*)-[:CURRENT_RATING_BELOW_IG]->(FirmMethod:current_rating_below_ig)"
    contributors = sorted(contributors_by_id.values(), key=lambda p: p.id)
    non_ig_rule = graph.limit_rule("Aggregate:non_ig")
    numerator = sum(mv(p) for p in contributors)
    val = pct(numerator, nav)
    cit = citation(graph, "Aggregate:non_ig") if src_node == "Aggregate:non_ig" else dict(graph.node(src_node).properties)
    cit = {k: cit[k] for k in ["source_doc", "page", "chunk_id", "passage_summary"]}
    figs.append(figure(
        "aggregate_non_ig_exposure",
        "Aggregate",
        "Aggregate non-IG exposure",
        round1(val),
        non_ig_rule["limit"],
        util(val, float(non_ig_rule["cap"]), cfg),
        "BREACH" if val > float(non_ig_rule["cap"]) else "OK",
        path,
        cit,
        [p.properties["instrument_id"] for p in contributors],
        rule_id,
        graph_edges,
        {"formula": "sum(non_ig_position_market_value) / total_nav * 100", "numerator": numerator, "denominator": nav, "positions": position_rows(contributors)},
    ))

    # Corporate concentration by graph traversal Position -> ISSUED_BY -> Issuer.
    corp_positions = graph.positions_by_issuer_type("corporate")
    corp_by_issuer: dict[str, float] = {}
    for p in corp_positions:
        issuer = graph.issuer_for_position(p)
        name = issuer.properties["name"]
        corp_by_issuer[name] = corp_by_issuer.get(name, 0.0) + mv(p)
    issuer_name, issuer_mv = max(corp_by_issuer.items(), key=lambda kv: (kv[1], kv[0]))
    issuer_positions = graph.positions_for_issuer_name(issuer_name, issuer_type="corporate")
    single_rule = graph.limit_rule("Limit:single_corporate_issuer")
    val = pct(issuer_mv, nav)
    figs.append(figure(
        "largest_single_corporate_issuer",
        "Concentration",
        "Largest single corporate issuer",
        round1(val),
        single_rule["limit"],
        util(val, float(single_rule["cap"]), cfg),
        status_range(val, None, float(single_rule["cap"])),
        f"(Position:{','.join(p.properties['instrument_id'] for p in issuer_positions)})-[:ISSUED_BY]->(Issuer:{issuer_name}); (Limit:single_corporate_issuer)-[:SUPPORTED_BY]->(SourceChunk:concentration)",
        citation(graph, "Limit:single_corporate_issuer"),
        [p.properties["instrument_id"] for p in issuer_positions],
        "single_corporate_issuer",
        [edge(p.id, "ISSUED_BY", f"Issuer:{issuer_name}") for p in issuer_positions],
        {"formula": "max(sum(corporate_issuer_market_value)) / total_nav * 100", "numerator": issuer_mv, "denominator": nav, "issuer": issuer_name, "positions": position_rows(issuer_positions)},
    ))

    # GRE concentration by graph traversal, configurable issuer vs parent issuer.
    gre_positions = graph.positions_by_issuer_type("GRE")
    groups: dict[str, float] = {}
    group_edges: list[dict[str, str]] = []
    if cfg["gre_concentration_method"] == "parent_issuer":
        for p in gre_positions:
            issuer = graph.issuer_for_position(p)
            parent = graph.parent_for_issuer(issuer)
            key = parent.properties["name"] if parent else issuer.properties["name"]
            groups[key] = groups.get(key, 0.0) + mv(p)
        rule_id = "firm_B.gre.parent_issuer"
        path = "(Position:GRE*)-[:ISSUED_BY]->(Issuer:GRE*)-[:ROLLS_UP_TO]->(ParentIssuer:*)-[:TESTED_AGAINST]->(Limit:gre_issuer)"
        cit = dict(graph.node("SourceChunk:firm_b_gre").properties)
        cit = {k: cit[k] for k in ["source_doc", "page", "chunk_id", "passage_summary"]}
    else:
        for p in gre_positions:
            issuer = graph.issuer_for_position(p)
            groups[issuer.properties["name"]] = groups.get(issuer.properties["name"], 0.0) + mv(p)
        rule_id = "firm_A.gre.issuer"
        path = "(Position:*)-[:ISSUED_BY]->(Issuer:GRE*)-[:TESTED_AGAINST]->(Limit:gre_issuer)"
        cit = citation(graph, "Limit:gre_issuer")
    gre_name, gre_mv = max(groups.items(), key=lambda kv: (kv[1], kv[0]))
    gre_positions_in_group = graph.positions_for_parent_issuer(gre_name, issuer_type="GRE") if cfg["gre_concentration_method"] == "parent_issuer" else graph.positions_for_issuer_name(gre_name, issuer_type="GRE")
    for p in gre_positions_in_group:
        issuer = graph.issuer_for_position(p)
        group_edges.append(edge(p.id, "ISSUED_BY", issuer.id))
        parent = graph.parent_for_issuer(issuer)
        if cfg["gre_concentration_method"] == "parent_issuer" and parent is not None:
            group_edges.append(edge(issuer.id, "ROLLS_UP_TO", parent.id))
    gre_rule = graph.limit_rule("Limit:gre_issuer")
    val = pct(gre_mv, nav)
    figs.append(figure(
        "largest_gre_issuer",
        "Concentration",
        "Largest GRE issuer",
        round1(val),
        gre_rule["limit"],
        util(val, float(gre_rule["cap"]), cfg),
        status_range(val, None, float(gre_rule["cap"])),
        path,
        cit,
        [p.properties["instrument_id"] for p in gre_positions_in_group],
        rule_id,
        group_edges,
        {"formula": "max(sum(gre_group_market_value)) / total_nav * 100", "numerator": gre_mv, "denominator": nav, "issuer_or_parent": gre_name, "positions": position_rows(gre_positions_in_group)},
    ))

    # Liquidity from graph contributors.
    liquid = graph.positions_contributing_to("Aggregate:liquid_assets")
    liq_rule = graph.limit_rule("Limit:liquidity_normal")
    numerator = sum(mv(p) for p in liquid)
    val = pct(numerator, nav)
    figs.append(figure(
        "liquid_assets_ratio",
        "Liquidity",
        "Liquid assets ratio",
        round1(val),
        liq_rule["limit"],
        util(val, float(liq_rule["floor"]), cfg),
        status_range(val, float(liq_rule["floor"]), None),
        "(AssetClass:SGS|MAS Bills|Cash)-[:CONTRIBUTES_TO]->(Aggregate:liquid_assets)-[:SUPPORTED_BY]->(SourceChunk:liquidity); (Limit:liquidity_normal)-[:SUPPORTED_BY]->(SourceChunk:liquidity)",
        citation(graph, "Limit:liquidity_normal"),
        [p.properties["instrument_id"] for p in liquid],
        "liquidity.normal_floor",
        [edge("AssetClass:Singapore Government Securities", "CONTRIBUTES_TO", "Aggregate:liquid_assets"), edge("AssetClass:MAS Bills", "CONTRIBUTES_TO", "Aggregate:liquid_assets"), edge("AssetClass:Cash & Cash Equivalents", "CONTRIBUTES_TO", "Aggregate:liquid_assets")],
        {"formula": "sum(liquid_asset_market_value) / total_nav * 100", "numerator": numerator, "denominator": nav, "positions": position_rows(liquid)},
    ))

    dur_num = sum(mv(p) * duration(p) for p in positions)
    dur = dur_num / nav
    dur_rule = graph.limit_rule("Limit:modified_duration")
    figs.append(figure(
        "portfolio_modified_duration",
        "Market risk",
        "Portfolio modified duration",
        f"{round2_num(dur)} yrs",
        dur_rule["limit"],
        "n/a",
        status_range(dur, float(dur_rule["min"]), float(dur_rule["max"])),
        "(Position:*)-[:HAS_MARKET_VALUE_AND_DURATION]->(Metric:weighted_duration)-[:TESTED_AGAINST]->(Limit:modified_duration)",
        citation(graph, "Limit:modified_duration"),
        [p.properties["instrument_id"] for p in positions],
        "market_risk.modified_duration_weighted_average",
        [edge(p.id, "HAS_MARKET_VALUE_AND_DURATION", "Metric:weighted_duration") for p in positions] + [edge("Metric:weighted_duration", "TESTED_AGAINST", "Limit:modified_duration")],
        {"formula": "sum(market_value * modified_duration) / total_nav", "numerator": dur_num, "denominator": nav, "positions": position_rows(positions)},
    ))

    dv01 = sum(mv(p) * duration(p) * 0.0001 for p in positions)
    dv01_rule = graph.limit_rule("Limit:dv01")
    figs.append(figure(
        "portfolio_dv01",
        "Market risk",
        "Portfolio DV01",
        money0(dv01),
        dv01_rule["limit"],
        util(dv01, float(dv01_rule["cap"]), cfg),
        status_range(dv01, None, float(dv01_rule["cap"])),
        "(Position:*)-[:HAS_MARKET_VALUE_AND_DURATION]->(Metric:dv01)-[:TESTED_AGAINST]->(Limit:dv01)",
        citation(graph, "Limit:dv01"),
        [p.properties["instrument_id"] for p in positions],
        "market_risk.dv01=sum(market_value*duration*0.0001)",
        [edge(p.id, "HAS_MARKET_VALUE_AND_DURATION", "Metric:dv01") for p in positions] + [edge("Metric:dv01", "TESTED_AGAINST", "Limit:dv01")],
        {"formula": "sum(market_value * modified_duration * 0.0001)", "numerator": dv01, "denominator": None, "positions": position_rows(positions)},
    ))
    return figs
