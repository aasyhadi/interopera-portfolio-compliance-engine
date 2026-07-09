# Reviewer Walkthrough

## Purpose

This document provides a short path to evaluate the repository against the take-home requirements.

## 1. Install

```bash
pip install -r requirements.txt
```

Optional virtual environment:

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / Mac
source venv/bin/activate
```

## 2. Run Everything

```bash
python run.py all
```

This builds both Firm A and Firm B outputs without code changes.

## 3. Expected Result

The command prints JSON. Expected checks:

```text
firm_A.reconciliation.all_passed = true
firm_A.traceability.all_passed = true
firm_A.no_llm_numbers_firewall.all_passed = true

firm_B.reconciliation.all_passed = true
firm_B.traceability.all_passed = true
firm_B.no_llm_numbers_firewall.all_passed = true
```

## 4. Inspect Outputs

Generated files:

```text
outputs/firm_A_graph.json
outputs/firm_A_figures.json
outputs/firm_A_evaluation.json
outputs/firm_A_report.xlsx

outputs/firm_B_graph.json
outputs/firm_B_figures.json
outputs/firm_B_evaluation.json
outputs/firm_B_report.xlsx

outputs/replay/firm_A/*.json
outputs/replay/firm_B/*.json
outputs/audit.sqlite
```

## 5. Verify Firm Reconfiguration

Compare:

```text
configs/firm_A.yml
configs/firm_B.yml
```

The engine code is unchanged. Firm method differences are configuration-only.

## 6. Replay One Figure

Example:

```bash
python run.py trace --firm firm_B --figure aggregate_non_ig_exposure
```

This returns:

- figure value
- formula
- source positions
- graph path
- validated graph edges
- citation
- config rule

This demonstrates the required audit path:

```text
figure -> graph path / edges -> source chunk
```

## 7. Verify No LLM Numbers

Open:

```text
outputs/firm_A_evaluation.json
outputs/firm_B_evaluation.json
```

Check:

```text
no_llm_numbers_firewall.all_passed = true
```

## 8. Verify Audit Log

Open:

```text
outputs/audit.sqlite
```

Expected event types include:

- CONFIG_LOADED
- GRAPH_CONSTRUCTED
- FIGURES_COMPUTED
- RECONCILIATION_COMPLETED
- TRACEABILITY_CHECK_COMPLETED
- NO_LLM_NUMBERS_CHECK_COMPLETED
- REPORT_EXPORTED

Append-only triggers block UPDATE and DELETE.

## 9. Fast Review Path

For a 5-minute review:

1. Run `python run.py all`
2. Confirm all pass flags are true
3. Run `python run.py trace --firm firm_B --figure aggregate_non_ig_exposure`
4. Inspect graph edges, source positions, formula, and citation
5. Open `outputs/audit.sqlite` and inspect `CONFIG_LOADED` checksums
