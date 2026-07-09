from __future__ import annotations
import json
from pathlib import Path
from typing import Any


def figure_replay_payload(figure: dict[str, Any], firm: str) -> dict[str, Any]:
    calc = figure.get("calculation", {})
    return {
        "firm": firm,
        "figure": figure["figure"],
        "metric": figure["metric"],
        "value": figure["value"],
        "status": figure["status"],
        "limit": figure["limit"],
        "config_rule": figure.get("config_rule"),
        "formula": calc.get("formula"),
        "numerator": calc.get("numerator"),
        "denominator": calc.get("denominator"),
        "source_positions": calc.get("positions", []),
        "graph_path": figure.get("graph_path"),
        "graph_edges": figure.get("graph_edges", []),
        "citation": figure.get("citation"),
        "replay_statement": _statement(figure),
    }


def _statement(figure: dict[str, Any]) -> str:
    calc = figure.get("calculation", {})
    numerator = calc.get("numerator")
    denominator = calc.get("denominator")
    formula = calc.get("formula", "")
    if denominator:
        return f"{figure['metric']} = {numerator} / {denominator} using formula: {formula}; display value {figure['value']}."
    return f"{figure['metric']} = {numerator} using formula: {formula}; display value {figure['value']}."


def write_replays(root: Path, firm: str, figures: list[dict[str, Any]]) -> list[str]:
    out_dir = root / "outputs" / "replay" / firm
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for fig in figures:
        payload = figure_replay_payload(fig, firm)
        path = out_dir / f"{fig['figure']}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        written.append(str(path))
    return written


def load_replay(root: Path, firm: str, figure_name: str) -> dict[str, Any] | None:
    path = root / "outputs" / "replay" / firm / f"{figure_name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
