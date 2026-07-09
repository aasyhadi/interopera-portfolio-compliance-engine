from __future__ import annotations
from typing import Any

def deterministic_narrative(figures: list[dict[str, Any]]) -> str:
    # No LLM is used in this take-home implementation. A future LLM layer may only paraphrase this
    # computed figure set and must pass the firewall check before export.
    breaches = [f for f in figures if f["status"] == "BREACH"]
    if not breaches:
        return "All computed compliance figures are within their configured limits."
    return "Compliance review requires attention for: " + "; ".join(f"{f['metric']} {f['value']} versus {f['limit']}" for f in breaches) + "."
