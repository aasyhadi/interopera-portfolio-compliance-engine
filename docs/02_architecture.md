# 02 - Architecture

```text
sample_fund_guidelines.pdf     sample_holdings.csv      firm_A.yml / firm_B.yml
           |                         |                         |
           v                         v                         v
   Source Chunk Catalogue ---> Knowledge Graph Builder ---> Config Resolver
           |                         |                         |
           |                         v                         |
           |                graph JSON + fingerprint            |
           |                         |                         |
           +-------------------------+-------------------------+
                                     v
                         Deterministic Computation Engine
                                     |
                                     v
                 Figure objects: value, limit, utilization,
                 status, graph_path, citation, config_rule
                                     |
                    +----------------+----------------+
                    |                                 |
                    v                                 v
              Reconciliation                    Traceability check
                    |                                 |
                    +----------------+----------------+
                                     v
                           Narrative Firewall
                                     |
                                     v
                              Excel Export
                                     |
                                     v
                         Append-only Audit Log
```

## Main modules

| Module | Responsibility |
|---|---|
| `interopera.config` | Loads firm configuration and source chunk catalogue. |
| `interopera.graph` | Builds the provenance-carrying graph of source chunks, limits, asset classes, issuers, parent issuers, and positions. |
| `interopera.compute` | Computes every figure deterministically by using graph-backed rules and holdings. |
| `interopera.report` | Exports reports, reconciles against answer keys, checks traceability, and validates narrative numbers. |
| `interopera.audit` | Writes append-only audit events and demonstrates no update/delete path. |
| `interopera.cli` | Provides runnable commands. |

## Graph model

Important node labels:

- `SourceChunk`
- `Fund`
- `AssetClass`
- `Limit`
- `Aggregate`
- `Position`
- `Issuer`
- `ParentIssuer`

Important relationships:

- `APPLIES_TO`
- `SUPPORTED_BY`
- `BELONGS_TO`
- `ISSUED_BY`
- `ROLLS_UP_TO`
- `CONTRIBUTES_TO`

Every node and edge carries source document, page, chunk, ingestion confidence, and passage summary.
