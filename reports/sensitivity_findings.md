# Asset condition and capital-budget sensitivity

Generated from the synthetic baseline assets and existing deterministic optimiser.
No EAM records are changed and no external AI service is called.

## Funding decision matrix

| Budget (£m) | A133 condition | P033 | P022 | Funded capex (£m) | Objective score | Decisions changed vs condition 8 |
| ---: | ---: | :---: | :---: | ---: | ---: | ---: |
| 200 | 8 | Deferred | Deferred | 199.8 | 76.650 | 0 |
| 200 | 7 | Deferred | Deferred | 199.8 | 76.650 | 0 |
| 200 | 6 | Deferred | Deferred | 199.8 | 76.650 | 0 |
| 200 | 5 | Deferred | Deferred | 199.8 | 76.650 | 0 |
| 200 | 4 | Deferred | Deferred | 199.8 | 76.650 | 0 |
| 250 | 8 | Deferred | Funded | 249.9 | 93.825 | 0 |
| 250 | 7 | Deferred | Funded | 249.9 | 93.825 | 0 |
| 250 | 6 | Deferred | Funded | 249.9 | 93.825 | 0 |
| 250 | 5 | Funded | Deferred | 243.2 | 93.900 | 2 |
| 250 | 4 | Funded | Deferred | 243.2 | 94.050 | 2 |
| 300 | 8 | Funded | Funded | 297.7 | 109.375 | 0 |
| 300 | 7 | Funded | Funded | 297.7 | 109.525 | 0 |
| 300 | 6 | Funded | Funded | 297.7 | 109.675 | 0 |
| 300 | 5 | Funded | Funded | 297.7 | 109.825 | 0 |
| 300 | 4 | Funded | Funded | 297.7 | 109.975 | 0 |

## Interpretation

- The condition score and budget are the only intentionally varied inputs.
- The model maximises a synthetic priority-score objective under the budget and mandatory-project constraints.
- A change in funded capex is a change in modelled capital allocation, **not** demonstrated real-world cost savings.
- Priority-score differences are **not** forecasts of risk reduction, cash flow or financial return.
- Funding decisions can change discontinuously in a mixed-integer model; a sampled threshold is not a universal engineering threshold.
- This does not validate the calibration of condition scores, project benefits, project cost estimates, uncertainty or regulatory obligations.
- Results depend on the checked-in synthetic data, scoring weights, constraints, and solver implementation.
