"""Deterministic, read-only asset-condition/budget sensitivity analysis.

Run from the asset-investment-copilot project root:
    python -m scripts.sensitivity_analysis

Uses data/assets_seed.csv; does not contact the mock EAM API, OpenAI, or SQLite.
Produces reports/sensitivity_analysis.csv and reports/sensitivity_findings.md.
"""
from __future__ import annotations

from pathlib import Path
import argparse

import pandas as pd

from src.data_loader import load_portfolio
from src.scoring import enrich_with_assets, score_portfolio
from src.optimiser import optimise_portfolio


ROOT = Path(__file__).resolve().parents[1]
ASSET_SEED = ROOT / "data" / "assets_seed.csv"
DEFAULT_CONDITIONS = (8, 7, 6, 5, 4)
DEFAULT_BUDGETS = (200, 250, 300)


def run_sensitivity_grid(
    portfolio: pd.DataFrame,
    baseline_assets: pd.DataFrame,
    *,
    conditions: tuple[int, ...] = DEFAULT_CONDITIONS,
    budgets: tuple[int, ...] = DEFAULT_BUDGETS,
    scenario: str = "Balanced",
    asset_id: str = "A133",
) -> pd.DataFrame:
    """Evaluate each condition/budget pairing with all other inputs unchanged.

    Neither caller-owned DataFrame is modified. All optimisation results are
    calculated through the existing project scoring and MILP optimiser.
    """
    if not conditions or not budgets:
        raise ValueError("Provide at least one condition and one budget.")
    if 8 not in conditions:
        raise ValueError("Conditions must include baseline score 8 for comparison.")
    if any(b <= 0 for b in budgets):
        raise ValueError("Budgets must be positive.")

    mask = baseline_assets["asset_id"].astype(str).eq(asset_id)
    if int(mask.sum()) != 1:
        raise ValueError(f"Expected exactly one {asset_id} asset in baseline seed.")
    actual_condition = float(baseline_assets.loc[mask, "condition_score"].iloc[0])
    if actual_condition != 8:
        raise ValueError(
            f"Expected seed condition 8 for {asset_id}, got {actual_condition}."
        )

    rows = []
    funded_sets = {}

    for budget_m in budgets:
        for condition in conditions:
            asset_copy = baseline_assets.copy(deep=True)
            asset_copy.loc[mask, "condition_score"] = int(condition)
            enriched = enrich_with_assets(portfolio.copy(deep=True), asset_copy)
            scored = score_portfolio(enriched, scenario)
            result = optimise_portfolio(scored, budget_m)

            funded_ids = set(result["funded"]["project_id"].astype(str))
            funded_sets[(budget_m, condition)] = funded_ids

            project_scores = scored.set_index("project_id")
            for required_project in ("P022", "P033"):
                if required_project not in project_scores.index:
                    raise ValueError(f"Missing project {required_project}.")

            capex = float(result["funded_capex_m"])
            if capex > float(budget_m) + 1e-6:
                raise AssertionError(
                    f"Optimiser exceeded £{budget_m}m budget at condition {condition}."
                )
            rows.append(
                {
                    "scenario": scenario,
                    "budget_m": int(budget_m),
                    "a133_condition": int(condition),
                    "funded_capex_m": capex,
                    "remaining_budget_m": float(result["remaining_budget_m"]),
                    "portfolio_score": float(result["portfolio_score"]),
                    "funded_count": int(result["selected_count"]),
                    "p033_funded": "P033" in funded_ids,
                    "p022_funded": "P022" in funded_ids,
                    "p033_priority_score": float(
                        project_scores.at["P033", "priority_score"]
                    ),
                    "p022_priority_score": float(
                        project_scores.at["P022", "priority_score"]
                    ),
                }
            )

    output = pd.DataFrame(rows)
    for budget_m in budgets:
        base_ids = funded_sets[(budget_m, 8)]
        for condition in conditions:
            key = (budget_m, condition)
            changed = funded_sets[key]
            row_mask = output["budget_m"].eq(budget_m) & output["a133_condition"].eq(condition)
            entered = sorted(changed - base_ids)
            left = sorted(base_ids - changed)
            output.loc[row_mask, "projects_newly_funded"] = ", ".join(entered)
            output.loc[row_mask, "projects_newly_deferred"] = ", ".join(left)
            output.loc[row_mask, "funding_decisions_changed"] = len(entered) + len(left)

    return output.sort_values(["budget_m", "a133_condition"], ascending=[True, False]).reset_index(drop=True)


def write_findings(grid: pd.DataFrame, path: Path) -> None:
    """Write only observed calculations, plus explicit interpretation limits."""
    lines = [
        "# Asset condition and capital-budget sensitivity",
        "",
        "Generated from the synthetic baseline assets and existing deterministic optimiser.",
        "No EAM records are changed and no external AI service is called.",
        "",
        "## Funding decision matrix",
        "",
        "| Budget (£m) | A133 condition | P033 | P022 | Funded capex (£m) | Objective score | Decisions changed vs condition 8 |",
        "| ---: | ---: | :---: | :---: | ---: | ---: | ---: |",
    ]
    for row in grid.itertuples(index=False):
        lines.append(
            f"| {row.budget_m} | {row.a133_condition} "
            f"| {'Funded' if row.p033_funded else 'Deferred'} "
            f"| {'Funded' if row.p022_funded else 'Deferred'} "
            f"| {row.funded_capex_m:.1f} | {row.portfolio_score:.3f} "
            f"| {int(row.funding_decisions_changed)} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The condition score and budget are the only intentionally varied inputs.",
            "- The model maximises a synthetic priority-score objective under the budget and mandatory-project constraints.",
            "- A change in funded capex is a change in modelled capital allocation, **not** demonstrated real-world cost savings.",
            "- Priority-score differences are **not** forecasts of risk reduction, cash flow or financial return.",
            "- Funding decisions can change discontinuously in a mixed-integer model; a sampled threshold is not a universal engineering threshold.",
            "- This does not validate the calibration of condition scores, project benefits, project cost estimates, uncertainty or regulatory obligations.",
            "- Results depend on the checked-in synthetic data, scoring weights, constraints, and solver implementation.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "reports",
        help="Output directory (default: project-root/reports)",
    )
    args = parser.parse_args()

    portfolio = load_portfolio("clean")
    baseline_assets = pd.read_csv(ASSET_SEED)
    grid = run_sensitivity_grid(portfolio, baseline_assets)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    csv_file = args.out_dir / "sensitivity_analysis.csv"
    markdown_file = args.out_dir / "sensitivity_findings.md"
    grid.to_csv(csv_file, index=False)
    write_findings(grid, markdown_file)

    print("\nAsset-condition / capital-budget sensitivity (synthetic data)")
    print(
        grid[
            [
                "budget_m", "a133_condition", "p033_funded",
                "p022_funded", "funded_capex_m", "portfolio_score",
                "funding_decisions_changed",
            ]
        ].to_string(index=False)
    )
    print(f"\nSaved: {csv_file}")
    print(f"Saved: {markdown_file}")


if __name__ == "__main__":
    main()
