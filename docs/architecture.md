# Architecture

ClaimLens AI is a synthetic insurance-claims decision-support system. It separates deterministic business logic from AI-facing retrieval so each output remains inspectable.

```text
React operations UI
        |
        v
FastAPI REST boundary
   |            |
   v            v
Claim service   Policy retrieval
   |            |
   v            v
SQLite store    Versioned policy clauses
   |
   v
Audit events + explainable risk factors
```

## Current decisions

- SQLite keeps the portfolio demo zero-cost and durable. The repository boundary allows a later PostgreSQL adapter without changing API contracts.
- The first risk engine is deterministic. Every score is accompanied by evidence, making it testable and suitable for human review.
- Policy answers use local retrieval and always expose citations. The API returns an explicit `grounded` flag when no relevant clause exists.
- All included data and policy text are synthetic. No employer, client, claimant, or production data is used.

## Planned production extensions

- PostgreSQL and object storage adapter.
- OCR and structured extraction worker for uploaded documents.
- Image damage classifier with a versioned evaluation set.
- Langfuse/OpenTelemetry tracing and service-level dashboards.
- Azure deployment with managed secrets and infrastructure as code.

