# 01 - Flow and Audit Events

## AS-IS flow

1. Analyst reads `sample_fund_guidelines.pdf`.
2. Analyst opens `sample_holdings.csv`.
3. Analyst calculates NAV allocation, concentration, liquidity, duration, and DV01 in a spreadsheet.
4. Analyst types values into `report_template.xlsx`.
5. A reviewer asks where a number came from; the answer depends on spreadsheet formulas and analyst memory.

## TO-BE flow

```text
Source documents
  -> deterministic ingestion
  -> provenance-carrying knowledge graph
  -> human graph verification gate
  -> deterministic computation engine
  -> reconciliation gate
  -> narrative firewall gate
  -> Excel report export
  -> append-only audit log
```

## Human and auto-pass gates

| Gate | Auto-pass criterion | Human review criterion |
|---|---|---|
| Source file validation | All required files exist and hashes are stable. | Missing file, unexpected schema, or hash mismatch. |
| Graph extraction verification | All required rule nodes and source chunks exist with confidence >= 0.95. | Missing rule, unresolved source chunk, or low confidence. |
| Traceability validation | Every figure has `figure -> graph path -> source chunk`. | Any figure lacks a graph path or citation. |
| Reconciliation | Each figure is exact or inside declared tolerance. | Any delta exceeds tolerance. |
| Narrative firewall | Every number in narrative appears in computed output. | Narrative introduces a new number. |
| Export approval | Reconciliation, traceability, and firewall all pass. | Any check fails. |

## LLM boundary

The LLM may only write commentary after figures are computed. It cannot compute, round, edit, or format any reported number. In this implementation, no LLM is used; the commentary is generated deterministically and still checked by the no-LLM-numbers firewall.

## Audit event catalogue

| Event | Trigger | Data captured | Retention |
|---|---|---|---|
| `CONFIG_SELECTED` | Firm run starts. | Firm ID and configuration settings. | Persistent append-only SQLite. |
| `GRAPH_CONSTRUCTED` | Knowledge graph created. | Node count, edge count, graph fingerprint, output path. | Persistent append-only SQLite. |
| `FIGURES_COMPUTED` | Computation engine emits figures. | Figure count and figures JSON path. | Persistent append-only SQLite. |
| `RECONCILIATION_COMPLETED` | Answer key comparison completes. | Firm ID, pass/fail, evaluation path. | Persistent append-only SQLite. |
| `TRACEABILITY_CHECK_COMPLETED` | Traceability validation completes. | Per-run pass/fail. | Persistent append-only SQLite. |
| `NO_LLM_NUMBERS_CHECK_COMPLETED` | Narrative firewall completes. | Pass/fail and unauthorized numbers in evaluation JSON. | Persistent append-only SQLite. |
| `REPORT_EXPORTED` | Excel report written. | Firm ID and report path. | Persistent append-only SQLite. |

The `audit_events` table has triggers that abort `UPDATE` and `DELETE`, making the log append-only.
