# ADR 0001: Explainable-first claim scoring

Status: accepted

## Context

Insurance claim decisions affect people and require an auditable basis. A portfolio demo should not imply that an opaque model can make final coverage decisions.

## Decision

The initial system uses deterministic, version-controlled risk rules. Each factor exposes a code, score contribution, and evidence. The system only supports human decisions and keeps an audit trail.

## Consequences

- Tests can verify every score contribution.
- Reviewers can challenge individual factors.
- Future ML models must remain advisory and publish evaluation, calibration, and drift evidence before integration.

