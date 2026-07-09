# InterOpera Portfolio Compliance Engine

An audit-ready compliance reporting prototype. The system builds a provenance-carrying knowledge graph, computes figures deterministically through graph traversal, and reconciles Firm A and Firm B outputs against answer keys. It also validates traceability, ensures narrative texts introduce no LLM-generated numbers, exports Excel/JSON reports, and maintains an append-only audit log.

## One-command start

```bash
pip install -r requirements.txt && python run.py all
```

Expected result:

```text
firm_A.reconciliation.all_passed = true
firm_A.traceability.all_passed = true
firm_A.no_llm_numbers_firewall.all_passed = true

firm_B.reconciliation.all_passed = true
firm_B.traceability.all_passed = true
firm_B.no_llm_numbers_firewall.all_passed = true
```

## Run one firm

```bash
python run.py firm_A
python run.py firm_B
```

Equivalent explicit commands:

```bash
python run.py run --firm firm_A
python run.py run --firm firm_B
```

## Replay / trace one figure

```bash
python run.py trace --firm firm_B --figure aggregate_non_ig_exposure
python run.py trace --firm firm_B --figure largest_gre_issuer
```

The trace command returns the figure value, formula, graph path, validated graph edges, source positions, citation, and firm configuration rule.

## Generated artifacts

```text
outputs/
├── firm_A_graph.json
├── firm_A_figures.json
├── firm_A_evaluation.json
├── firm_A_report.xlsx
├── firm_B_graph.json
├── firm_B_figures.json
├── firm_B_evaluation.json
├── firm_B_report.xlsx
├── replay/
│   ├── firm_A/*.json
│   └── firm_B/*.json
└── audit.sqlite
```

## Key guarantees

| Requirement | Implementation |
|---|---|
| Deterministic figures | Computation uses deterministic Python arithmetic and stable ordering. |
| Traceability | Every figure includes graph path, validated graph edges, component positions, and source citation. |
| No LLM-generated numbers | Narrative is checked by a firewall; every number in narrative must exist in computed figures. |
| Firm A reconciliation | `firm_A_answer_key.xlsx` is used for reconciliation. |
| Firm B reconfiguration | Firm B method is controlled by `configs/firm_B.yml`, no engine-code edit required. |
| Append-only audit log | SQLite triggers block UPDATE and DELETE; event hashes form a chain. |

## Graph-first computation

The computation layer reads from the graph instead of reading source files directly. It uses graph query methods for:

- positions by asset class
- aggregate contributors
- below-investment-grade fallen angels
- issuer and parent issuer rollups
- limits and thresholds
- source citations

This ensures the report path is:

```text
source documents -> graph -> graph traversal -> deterministic computation -> report figure
```

## Firm method switching

Configuration files:

```text
configs/firm_A.yml
configs/firm_B.yml
configs/source_chunks.yml
```

Each run logs the SHA256 hash of the selected firm config and source-chunk config in `CONFIG_LOADED` audit events.

## Documentation

```text
docs/
├── 01_flow_and_audit_events.md
├── 02_architecture.md
├── 03_rfc.md
├── 04_assumptions_and_known_limitations.md
├── 05_threat_model.md
└── 06_reviewer_walkthrough.md
```

## Append-only audit log

`outputs/audit.sqlite` contains `audit_events`. The table is append-only:

- INSERT is allowed
- UPDATE is blocked
- DELETE is blocked

The evaluator JSON includes an append-only trigger check.

## Notes on scope

This is a one-week take-home implementation, not a production platform. Production upgrades would include Neo4j, a human graph-review UI, immutable object storage, digital report signatures, authentication, and a versioned configuration registry.
