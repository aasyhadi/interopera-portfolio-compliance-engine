# Threat Model

## Purpose

This document identifies threats to deterministic, traceable, audit-ready compliance reporting and the controls implemented in this assessment.

## Trust Boundaries

Trusted components allowed to produce reported figures:

- Knowledge Graph
- Configuration loader
- Deterministic computation engine
- Reconciliation engine
- Audit engine

Untrusted or non-authoritative components:

- LLM narrative layer
- human-written commentary
- prompts or external text not approved as source data

The LLM is not part of the numerical computation path.

## Threat 1: LLM Generates or Alters Numbers

### Risk

A language model may invent, round, or alter figures, violating the no-LLM-numbers constraint.

### Control

The LLM/narrative layer receives already-computed figures and is not allowed to calculate values. The no-LLM-numbers firewall extracts numbers from narrative text and checks that every number already exists in computed figure fields.

### Evidence

Review:

```text
outputs/firm_A_evaluation.json
outputs/firm_B_evaluation.json
```

Look for:

```text
no_llm_numbers_firewall.all_passed = true
```

## Threat 2: Broken Figure Traceability

### Risk

A report figure is emitted without an auditable path back to source material.

### Control

Every figure includes:

- graph path
- validated graph edges
- component position IDs
- citation with source document, page, and chunk ID

The traceability check validates component positions and graph edges against the constructed graph.

## Threat 3: Configuration Tampering

### Risk

A firm method changes without audit evidence.

### Control

The system logs configuration path and SHA256 hash on every run.

Audit event:

```text
CONFIG_LOADED
```

Captured data includes:

- firm ID
- config path
- config SHA256
- source chunk config SHA256

## Threat 4: Audit Log Manipulation

### Risk

An operator updates or deletes audit rows after report generation.

### Control

SQLite triggers block UPDATE and DELETE on the audit table.

The audit log stores a hash chain using each event's data hash and the previous event chain hash.

## Threat 5: Non-Deterministic Re-Runs

### Risk

Identical inputs produce different figures.

### Control

The computation layer uses deterministic arithmetic and stable sorting. No randomness, sampling, or temperature-based model output is used for figures.

## Threat 6: Computation Bypasses the Graph

### Risk

The graph is built only for display while figures are computed directly from CSV rows.

### Control

The computation layer obtains positions, issuers, parent rollups, aggregate contributors, risk limits, and source citations through graph query methods such as:

- `positions_for_asset_class`
- `positions_contributing_to`
- `positions_below_ig_current_rating`
- `issuer_for_position`
- `parent_for_issuer`
- `limit_rule`
- `citation_for_supported_node`

Each figure also emits graph edges validated by the traceability checker.

## Residual Risks

Remaining production risks include incorrect guideline extraction, source document corruption, and human approval errors. In production these would be mitigated with graph-review workflow, document versioning, digital signatures, and immutable audit storage.
