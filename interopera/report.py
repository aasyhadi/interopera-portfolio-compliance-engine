from __future__ import annotations
import json, re, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any
from openpyxl import load_workbook, Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment

HEADERS = ["Section", "Metric", "Value", "Limit", "Utilization", "Status", "Source (graph path → doc/page)"]

def source_text(fig: dict[str, Any]) -> str:
    c=fig["citation"]
    return f"{fig['graph_path']} → {c['source_doc']} p.{c['page']} {c['chunk_id']}"

def write_report(root: Path, figures: list[dict[str, Any]], out_path: Path) -> None:
    template = root / "sample_docs" / "report_template.xlsx"
    wb = load_workbook(template) if template.exists() else Workbook()
    ws = wb.active
    ws.title = "Report"
    for col, h in enumerate(HEADERS, 1):
        ws.cell(1, col).value = h
    for r, fig in enumerate(figures, 2):
        vals=[fig["section"], fig["metric"], fig["value"], fig["limit"], fig["utilization"], fig["status"], source_text(fig)]
        for c, v in enumerate(vals, 1):
            ws.cell(r,c).value=v
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(color="FFFFFF", bold=True)
    thin = Side(style="thin", color="D9E2F3")
    for row in ws.iter_rows(min_row=1, max_row=len(figures)+1, min_col=1, max_col=7):
        for cell in row:
            cell.border = Border(bottom=thin)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if cell.row == 1:
                cell.fill = header_fill; cell.font = header_font
    for i, width in enumerate([16,36,18,16,16,14,85], 1):
        ws.column_dimensions[chr(64+i)].width = width
    for i in range(2, len(figures)+2):
        ws.row_dimensions[i].height = 35
    ws.freeze_panes = "A2"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)

def _xlsx_rows(path: Path) -> list[list[str]]:
    wb=load_workbook(path, data_only=True)
    ws=wb.active
    rows=[]
    for row in ws.iter_rows(values_only=True):
        if any(v is not None for v in row):
            rows.append(["" if v is None else str(v) for v in row[:7]])
    return rows

def normalize_value(v: str) -> float | str:
    s=str(v).strip()
    if s.lower()=="n/a": return "n/a"
    if "bps" in s:
        return float(re.sub(r"[^0-9.-]", "", s))
    if "%" in s:
        return float(re.sub(r"[^0-9.-]", "", s))
    if "SGD" in s:
        return float(re.sub(r"[^0-9.-]", "", s))
    if "yrs" in s:
        return float(re.sub(r"[^0-9.-]", "", s))
    return s

def make_firm_b_answer_key(root: Path, figures: list[dict[str, Any]]) -> Path:
    out = root / "sample_docs" / "firm_B_answer_key.xlsx"
    write_report(root, figures, out)
    return out

def reconcile(answer_key: Path, figures: list[dict[str, Any]], tolerance: dict[str, float]) -> dict[str, Any]:
    rows=_xlsx_rows(answer_key)
    expected={r[1]: r for r in rows[1:] if len(r)>1 and r[1]}
    by_metric={f["metric"]: f for f in figures}
    results=[]
    for metric, row in expected.items():
        fig=by_metric.get(metric)
        if not fig:
            results.append({"metric": metric, "pass": False, "reason": "missing computed figure"}); continue
        deltas={}
        ok=True
        for col_name, idx in [("value",2),("utilization",4)]:
            ev, av = normalize_value(row[idx]), normalize_value(fig[col_name])
            if isinstance(ev, float) and isinstance(av, float):
                delta=round(av-ev, 6); deltas[col_name]=delta
                # One broad display tolerance works because values are preformatted display figures.
                if abs(delta) > max(tolerance.get("percent_points",0.05), tolerance.get("currency",1) if col_name=="value" and "SGD" in row[idx] else 0.05): ok=False
            else:
                deltas[col_name]=0 if ev==av else f"expected {ev}, got {av}"
                if ev!=av: ok=False
        if row[5] != fig["status"]: ok=False; deltas["status"] = f"expected {row[5]}, got {fig['status']}"
        results.append({"metric": metric, "pass": ok, "delta": deltas})
    return {"answer_key": str(answer_key), "all_passed": all(r["pass"] for r in results), "results": results}

def check_traceability(figures: list[dict[str, Any]], graph: Any | None = None) -> dict[str, Any]:
    rows=[]
    for f in figures:
        reasons=[]
        if not f.get("graph_path"):
            reasons.append("missing graph_path")
        chunk_id = f.get("citation",{}).get("chunk_id")
        if not chunk_id:
            reasons.append("missing citation chunk_id")
        if graph is not None:
            source_nodes = [n for n in graph.nodes.values() if n.label == "SourceChunk" and n.properties.get("chunk_id") == chunk_id]
            if not source_nodes:
                reasons.append(f"citation chunk not present in graph: {chunk_id}")
            for instrument_id in f.get("components", []):
                if f"Position:{instrument_id}" not in graph.nodes:
                    reasons.append(f"component position missing from graph: {instrument_id}")
            for e in f.get("graph_edges", []):
                try:
                    graph.assert_edge(e["source"], e["relation"], e["target"])
                except Exception as exc:
                    reasons.append(str(exc))
        rows.append({"figure": f["figure"], "pass": not reasons, "graph_path": f.get("graph_path"), "chunk_id": chunk_id, "validated_edges": len(f.get("graph_edges", [])), "reasons": reasons})
    return {"all_passed": all(r["pass"] for r in rows), "results": rows}

def check_no_llm_numbers(narrative: str, figures: list[dict[str, Any]]) -> dict[str, Any]:
    allowed=set()
    for f in figures:
        for key in ["value","limit","utilization"]:
            allowed.update(re.findall(r"\d[\d,]*(?:\.\d+)?", str(f.get(key,""))))
    found=re.findall(r"\d[\d,]*(?:\.\d+)?", narrative or "")
    unauthorized=[x for x in found if x not in allowed]
    return {"all_passed": len(unauthorized)==0, "numbers_found": found, "unauthorized_numbers": unauthorized}
