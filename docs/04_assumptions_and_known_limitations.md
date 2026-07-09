# Assumptions and Known Limitations

## Purpose

This document records calculation assumptions, firm-specific conventions, and known limitations of the Portfolio Compliance Engine. The goal is to make the report reproducible and defensible in an audit review.

## Source of Truth

The supplied materials are treated as authoritative:

- `sample_docs/sample_fund_guidelines.pdf`
- `sample_docs/sample_holdings.csv`
- `sample_docs/firm_A_answer_key.xlsx`
- `sample_docs/firm_B_brief.md`
- `sample_docs/firm_B_answer_key.xlsx`

The system does not call external market-data, pricing, ratings, or LLM services to compute report figures.

## Calculation Basis

All exposure calculations use `market_value_sgd` from `sample_holdings.csv`.

Total NAV is computed as:

```text
sum(all position market_value_sgd)
```

Allocation percentage is computed as:

```text
asset_class_market_value / total_nav * 100
```

Portfolio modified duration is computed as:

```text
sum(market_value_sgd * modified_duration) / total_nav
```

Portfolio DV01 is computed as:

```text
sum(market_value_sgd * modified_duration * 0.0001)
```

## Firm A Conventions

Firm A computes aggregate non-investment-grade exposure as the sum of positions whose asset class contributes to the non-IG aggregate:

- High Yield Bonds
- Structured Credit

GRE concentration is tested by legal issuer.

Utilization is displayed as a one-decimal percentage.

## Firm B Conventions

Firm B uses the same engine but different configuration.

Firm B aggregate non-IG exposure includes:

- High Yield Bonds
- Structured Credit
- Current-rating below-investment-grade fallen angels, even if the asset class is Investment Grade Corporate Bonds

Blank or unrated cash positions are not treated as below investment grade.

GRE concentration is tested by parent issuer group.

Utilization is displayed as truncated basis points.

## Traceability Assumption

Every figure must include:

```text
figure -> graph_edges / graph_path -> citation -> source chunk
```

A figure without graph path, citation, source chunk, or validated component positions fails traceability validation.

## Audit Log Assumption

The audit log is append-only. The implementation permits INSERT events and blocks UPDATE / DELETE with SQLite triggers.

Each run logs:

- configuration load and checksum
- graph construction
- figure computation
- reconciliation
- traceability validation
- no-LLM-numbers validation
- report export

## Known Limitations

This is a take-home assessment implementation, not a production platform.

Known limitations:

1. Graph storage is JSON/in-memory rather than Neo4j or another persistent graph database.
2. Source chunks are seeded from approved configuration instead of an automated PDF extraction pipeline.
3. Human review is represented in documentation and approved seed data; no UI approval workflow is implemented.
4. The system is scoped to the supplied Meridian Fixed Income Fund sample.
5. Security, authentication, and production-grade secrets management are intentionally out of scope.

## Production Enhancements

Recommended production upgrades:

- Neo4j-backed graph store
- versioned configuration registry
- human graph-review and approval UI
- digital signatures for exported reports
- immutable audit storage
- regulatory report pack generation
- graph visualization / replay viewer
