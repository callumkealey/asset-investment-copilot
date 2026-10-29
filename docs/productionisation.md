# Productionisation Plan

The prototype is intentionally not presented as production-ready software. A regulated enterprise deployment would need at least the following work.

## Identity and security

- OAuth/OIDC or workload identity rather than a static demo API key.
- Secrets stored in a managed secrets service.
- Role-based access control and least privilege.
- Threat modelling, dependency scanning and security review.

## Reliability and integration

- Timeouts, retries with backoff, circuit breakers and idempotency where appropriate.
- Contract/version management for upstream systems.
- Queueing or streaming for asynchronous updates if near-real-time asset events are required.
- Explicit handling of stale, missing and conflicting source records.

## Observability

- Structured application logs and correlation IDs.
- Metrics for API latency, failure rate, retrieval quality, model latency and tool failures.
- Distributed traces across customer system, application services and LLM calls.
- Alerts and operational runbooks.

## Data governance

- Data lineage from system of record to investment recommendation.
- Data retention and classification rules.
- Audit trail of inputs, scenario weights, model/tool calls and final recommendation.
- Approval workflow for changes to investment logic.

## AI controls

- Offline and online evaluation sets.
- Retrieval quality evaluation and citation checks.
- Prompt-injection and untrusted-document controls.
- Output constraints for financial/numerical claims.
- Human approval before investment recommendations become decisions.

## Software delivery

- Containerisation.
- CI/CD with unit, integration and regression tests.
- Separate development/test/production environments.
- Performance and load testing.
- Infrastructure-as-code and rollback procedures.
