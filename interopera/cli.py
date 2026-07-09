from __future__ import annotations
import argparse, json, uuid
from pathlib import Path
from .config import load_config
from .graph import build_graph
from .compute import compute_figures
from .report import write_report, reconcile, check_traceability, check_no_llm_numbers
from .narrative import deterministic_narrative
from .audit import AuditLog
from .replay import write_replays, load_replay

def run(root: Path, firm: str, export: bool=True) -> dict:
    cfg=load_config(root, firm)
    run_id=f"{firm}-{uuid.uuid4().hex[:12]}"
    audit=AuditLog(root / "outputs" / "audit.sqlite")
    public_cfg = {k:v for k,v in cfg.items() if k != "source_chunks"}
    audit.append("CONFIG_LOADED", run_id, {"firm": firm, "config_path": cfg["_config_path"], "config_sha256": cfg["_config_sha256"], "source_chunks_path": cfg["_source_chunks_path"], "source_chunks_sha256": cfg["_source_chunks_sha256"], "config": public_cfg})
    graph=build_graph(root, cfg)
    graph_path=root / "outputs" / f"{firm}_graph.json"
    graph.write_json(graph_path)
    audit.append("GRAPH_CONSTRUCTED", run_id, {"firm": firm, "node_count": len(graph.nodes), "edge_count": len(graph.edges), "fingerprint": graph.fingerprint(), "path": str(graph_path)})
    figures=compute_figures(root, graph, cfg)
    figures_path=root / "outputs" / f"{firm}_figures.json"
    figures_path.write_text(json.dumps(figures, indent=2, sort_keys=True), encoding="utf-8")
    replay_paths = write_replays(root, firm, figures)
    audit.append("FIGURES_COMPUTED", run_id, {"firm": firm, "figure_count": len(figures), "figures_path": str(figures_path), "replay_count": len(replay_paths)})
    answer_key=root / cfg["answer_key"]
    rec=reconcile(answer_key, figures, cfg["tolerance"])
    trace=check_traceability(figures, graph)
    narrative=deterministic_narrative(figures)
    firewall=check_no_llm_numbers(narrative, figures)
    eval_obj={"run_id": run_id, "firm": firm, "config_sha256": cfg["_config_sha256"], "source_chunks_sha256": cfg["_source_chunks_sha256"], "reconciliation": rec, "traceability": trace, "no_llm_numbers_firewall": firewall, "narrative": narrative, "audit_append_only_demo": audit.verify_append_only_triggers(), "replay_directory": str(root / "outputs" / "replay" / firm)}
    eval_path=root / "outputs" / f"{firm}_evaluation.json"
    eval_path.write_text(json.dumps(eval_obj, indent=2, sort_keys=True), encoding="utf-8")
    audit.append("RECONCILIATION_COMPLETED", run_id, {"firm": firm, "all_passed": rec["all_passed"], "path": str(eval_path)})
    audit.append("TRACEABILITY_CHECK_COMPLETED", run_id, {"firm": firm, "all_passed": trace["all_passed"]})
    audit.append("NO_LLM_NUMBERS_CHECK_COMPLETED", run_id, {"firm": firm, "all_passed": firewall["all_passed"]})
    if export:
        out=root / cfg["output_report"]
        write_report(root, figures, out)
        audit.append("REPORT_EXPORTED", run_id, {"firm": firm, "path": str(out)})
    return eval_obj

def trace(root: Path, firm: str, figure_name: str) -> dict:
    replay = load_replay(root, firm, figure_name)
    if replay is not None:
        return replay
    path=root / "outputs" / f"{firm}_figures.json"
    if not path.exists():
        run(root, firm)
    figures=json.loads(path.read_text(encoding="utf-8"))
    for f in figures:
        if f["figure"] == figure_name or f["metric"] == figure_name:
            replay = load_replay(root, firm, f["figure"])
            return replay or f
    raise SystemExit(f"Figure not found: {figure_name}")

def main() -> None:
    p=argparse.ArgumentParser(description="InterOpera audit-grade compliance reporting take-home")
    p.add_argument("command", choices=["run", "trace", "all", "firm_A", "firm_B"])
    p.add_argument("--firm", default="firm_A", choices=["firm_A", "firm_B"])
    p.add_argument("--figure", default="aggregate_non_ig_exposure")
    p.add_argument("--root", default=".")
    args=p.parse_args()
    root=Path(args.root).resolve()
    if args.command == "all":
        result={"firm_A": run(root,"firm_A"), "firm_B": run(root,"firm_B")}
    elif args.command in {"firm_A", "firm_B"}:
        result=run(root,args.command)
    elif args.command == "run":
        result=run(root,args.firm)
    else:
        result=trace(root,args.firm,args.figure)
    print(json.dumps(result, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
