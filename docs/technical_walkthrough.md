# Technical Walkthrough — Architecture, Decisions and Trade-offs

## 60-second project explanation

I built a synthetic asset-investment-planning prototype because it mirrors the customer problem in the Forward Deployed Engineer role. The application validates an infrastructure capital portfolio, scores projects under different strategic priorities and uses a mixed-integer optimisation model to select a portfolio within a fixed budget while protecting mandatory projects. I then added a retrieval and tool-calling LLM layer so natural-language questions are answered using deterministic analytical functions and supporting documents rather than asking the model to invent calculations. Finally, I treated the first version as an FDE engagement: a hypothetical customer told me asset condition actually lived in an EAM system, so I added an authenticated REST integration, reconciliation checks and showed how fresh condition data changes project rankings.

## Why deterministic maths instead of letting the LLM calculate?

Investment allocation is a controlled numerical process. The scoring logic and budget constraints should be reproducible, testable and auditable. The LLM is used for orchestration and explanation, not as the source of truth for arithmetic.

## Why RAG?

Some evidence is unstructured: policy, regulatory guidance and customer documents. Retrieval finds relevant passages at query time so the model can ground explanations in the supplied corpus rather than relying on general model knowledge.

## Why one agent rather than multiple agents?

The workflow is small and the tools have clear responsibilities. A multi-agent design would add coordination, latency, state-management and failure modes without enough benefit. One tool-calling agent is easier to reason about and evaluate.

## Why SQLite?

It gives the prototype a real relational persistence/query layer without introducing infrastructure that is unnecessary for an MVP. The same repository/service boundary could be moved to PostgreSQL or another enterprise database later.

## Why a REST API?

The customer change request says asset condition belongs to another system of record. A REST boundary creates a realistic integration point and lets the prototype demonstrate authentication, system separation, reconciliation and failure handling.

## What is not production ready?

Authentication, secrets, RBAC, observability, robust retries, data lineage, formal evaluation, deployment architecture, security controls and enterprise integration contracts. The prototype makes those gaps explicit rather than pretending a Streamlit app is production software.

## What did I learn?

The AI layer is not the hardest part of the workflow. Data quality, reconciliation, transparent decision logic and clear boundaries between probabilistic and deterministic components are at least as important for a credible enterprise solution.
