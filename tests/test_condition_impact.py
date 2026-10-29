"""Regression test: an A133 condition change alters the £250m Balanced portfolio.

Uses checked-in seed data only. No FastAPI server, API key, or EAM writes required.
"""

from pathlib import Path

import pandas as pd
import pytest

from src.data_loader import load_portfolio
from src.optimiser import optimise_portfolio
from src.scoring import enrich_with_assets, score_portfolio


ASSET_SEED = Path(__file__).resolve().parents[1] / "data" / "assets_seed.csv"


def _run_balanced(portfolio: pd.DataFrame, assets: pd.DataFrame) -> dict:
    enriched = enrich_with_assets(portfolio.copy(deep=True), assets.copy(deep=True))
    scored = score_portfolio(enriched, "Balanced")
    return optimise_portfolio(scored, 250)


def test_a133_condition_change_switches_funded_projects() -> None:
    """Changing only A133's condition from 8 to 5 swaps P022 for P033."""
    portfolio = load_portfolio("clean")
    baseline_assets = pd.read_csv(ASSET_SEED)

    a133 = baseline_assets["asset_id"].astype(str).eq("A133")
    assert a133.sum() == 1, "The seed must contain exactly one A133 asset"
    assert float(baseline_assets.loc[a133, "condition_score"].iloc[0]) == 8

    deteriorated_assets = baseline_assets.copy(deep=True)
    deteriorated_assets.loc[a133, "condition_score"] = 5

    baseline = _run_balanced(portfolio, baseline_assets)
    deteriorated = _run_balanced(portfolio, deteriorated_assets)

    baseline_funded = set(baseline["funded"]["project_id"])
    deteriorated_funded = set(deteriorated["funded"]["project_id"])

    assert deteriorated_funded - baseline_funded == {"P033"}
    assert baseline_funded - deteriorated_funded == {"P022"}

    assert baseline["funded_capex_m"] == pytest.approx(249.9)
    assert deteriorated["funded_capex_m"] == pytest.approx(243.2)
    assert baseline["portfolio_score"] == pytest.approx(93.825)
    assert deteriorated["portfolio_score"] == pytest.approx(93.9)

    # Neither the source DataFrame nor the seed CSV was modified by the test.
    assert float(baseline_assets.loc[a133, "condition_score"].iloc[0]) == 8
