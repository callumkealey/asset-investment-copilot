# Integration Case Study: Live Asset Condition

## Initial prototype

The first prototype accepts an investment portfolio, validates it, scores projects against strategic criteria and optimises the funded portfolio within a capital constraint.

## Hypothetical requirement

> *Fictional stakeholder statement:* “Asset condition changes regularly and is maintained in our enterprise asset-management system. We do not want investment planners maintaining a separate condition field in the portfolio spreadsheet.”

## Hypothesis

Integrating current condition records could improve the credibility of prioritisation, reduce manual reconciliation and make ranking changes traceable to the simulated system of record. This is a design hypothesis, not a measured operational benefit.

## Smallest safe prototype

1. Expose synthetic EAM records through an authenticated REST API.
2. Match `portfolio.asset_id` to `eam.asset_id`.
3. Surface missing, stale and incomplete records.
4. Convert condition to an explicit `asset_condition_need` input.
5. Re-run the deterministic scoring and capital allocation.
6. Show which rankings changed and why.

## Scope and limitations

The mock API is not a production enterprise asset-management product or an official integration. It is a small integration boundary designed to demonstrate authentication, retrieval, reconciliation, exception handling and downstream decision impact.
