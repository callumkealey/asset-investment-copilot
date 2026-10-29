# Sensitivity analysis — how to run and interpret

This self-directed portfolio exercise uses **synthetic** investment and asset records. It tests whether a deterministic capital-allocation model is sensitive to changes in asset condition and the available budget.

## Run from the project root (Windows PowerShell)

With the `.venv` activated:

```powershell
python -m scripts.sensitivity_analysis
python -m pytest -q
```

The script reads `data/assets_seed.csv` and the clean portfolio, then evaluates **15 combinations**: A133 conditions **8, 7, 6, 5, 4** against budgets **£200m, £250m, £300m** under the **Balanced** strategy.

It writes:

- `reports/sensitivity_analysis.csv`: machine-readable decision matrix, scores, funded capex, funded project flags, and projects entering/leaving the programme relative to condition 8 at the same budget.
- `reports/sensitivity_findings.md`: an automatically generated, reviewable summary based on actual optimiser outputs.

**No API key, EAM server, OpenAI call, asset update, or SQLite database write is required for the sensitivity script.** It writes only the two report files listed above.

## Known regression anchor

At **£250m / Balanced** with the checked-in baseline seed, changing only A133 from **8 to 5** has been observed to change P033 from deferred to funded, and P022 from funded to deferred. Allocated capex changes from **£249.9m to £243.2m**. The optimiser's synthetic objective increases from **93.825 to 93.900**.

## What the analysis does and does not show

**Shows:** The decision's sensitivity to two inputs while holding the dataset and scoring method fixed. It makes potential discontinuities in the binary fund/defer selection visible.

**Does not show:** Validated real-world risk, monetised benefits, optimal asset-intervention timing, financial savings, constraint dual values, or a causal estimate from external data. Conditions are synthetic model inputs; an actual regulated utility would need calibrated condition methodology, decision auditability, uncertainty quantification, and approval workflows.

## Portfolio project completion check

Before publishing the repository:

1. Run `python -m pytest -q` and keep the real result; do not claim tests passed unless they did.
2. Run `python -m scripts.sensitivity_analysis` and inspect the 15-row report.
3. Check the Streamlit **Asset impact** tab still reproduces the £250m condition-only funding switch.
4. Check `.env`, tokens, personal data, generated databases and temporary files are excluded from Git.
5. Ensure the README describes a **synthetic, independent technical project**, not a production customer deployment or an official vendor integration.
6. Capture a genuine Streamlit screenshot (hide secrets and personal paths), commit only intentional files, and review `git status`.
7. Publish to GitHub only once ready; a local commit is not an online publication.

### Suggested README addendum

```markdown
## Sensitivity analysis

Run `python -m scripts.sensitivity_analysis` to explore how A133 condition scores
8, 7, 6, 5 and 4 affect portfolio funding at £200m, £250m and £300m.
The script uses baseline synthetic assets, does not update the EAM API,
and generates `reports/sensitivity_analysis.csv` and
`reports/sensitivity_findings.md`. See `docs/sensitivity_analysis.md`
for interpretation and limitations.
```
