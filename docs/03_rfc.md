# 03 - RFC: Audit-Grade Compliance Report Engine

## Context

The system must produce regulatory-style compliance reports for a fixed-income portfolio. The core evaluation constraints are reproducibility, graph-based traceability, no LLM-produced numbers, Firm A reconciliation, and Firm B reconfiguration without engine-code edits.

## Decision 1 - Use deterministic computation for all figures

All reported values are computed in `interopera.compute`. The engine reads holdings, rule nodes, and firm configuration. It uses explicit formulas for allocation, non-IG exposure, concentration, liquidity, weighted modified duration, and DV01.

The LLM boundary is structural: the computation module has no LLM dependency and emits canonical figure objects before any narrative is produced. The narrative receives already-computed figures only. The firewall extracts numeric tokens from narrative and fails if any token is not present in the computed figure set.

## Decision 2 - Use a provenance-carrying graph as the rule substrate

The graph is not decorative. Figures include a graph path and citation. If either is absent, the computation layer raises an error instead of emitting the figure. Rule nodes are connected to source chunks with `SUPPORTED_BY`; positions connect to asset classes and issuers with `BELONGS_TO` and `ISSUED_BY`; GRE issuers roll up with `ROLLS_UP_TO`.

This supports the audit question: "Where did this number come from?" A replay command shows the figure, graph path, source chunk, components, and configuration rule.

## Decision 3 - Keep firm method as configuration

Firm A and Firm B differ in three places: non-IG definition, GRE concentration grouping, and utilization presentation. These are represented in YAML:

- `non_ig_method`
- `fallen_angel_include`
- `gre_concentration_method`
- `utilization_style`

The engine branches on configuration values, not on hardcoded firm names. A new firm can be added by creating a new config file if it uses the existing method vocabulary.

## Decision 4 - Reconcile after compute, before export approval

The report is not considered audit-ready until reconciliation passes. The reconciliation script compares every displayed figure against the answer key and reports deltas. Firm A is reconciled to the provided workbook. Firm B's markdown-provided answer key is materialized into the same workbook layout for a uniform comparison path.

## Decision 5 - Append-only audit storage

SQLite is used for the audit log because it is simple and runnable for a take-home assessment. The `audit_events` table has database triggers that abort `UPDATE` and `DELETE`, so rows cannot be edited or removed after insertion. Each event stores a hash and a chained hash to detect tampering.

## Production extensions

For production, I would add authenticated reviewer approval, immutable object storage for source files, stronger PDF extraction with dual control review, signed report exports, secrets management, and row-level audit-log replication to write-once storage.
