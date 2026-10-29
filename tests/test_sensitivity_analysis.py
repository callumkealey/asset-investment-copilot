"""Sensitivity analysis regression tests: no EAM server required."""
from pathlib import Path

import pandas as pd
import pytest

from src.data_loader import load_portfolio
from scripts.sensitivity_analysis import run_sensitivity_grid

ROOT = Path(__file__).resolve().parents[1]
SEED = ROOT / "data" / "assets_seed.csv"


def test_sensitivity_matrix_is_budget_feasible_and_does_not_mutate_seed():
    assets = pd.read_csv(SEED)
    original_assets = assets.copy(deep=True)
    grid = run_sensitivity_grid(
        load_portfolio("clean"), assets,
        budgets=(200, 250, 300), conditions=(8, 5),
    )
    assert len(grid) == 6
    assert (grid["funded_capex_m"] <= grid["budget_m"] + 1e-6).all()
    pd.testing.assert_frame_equal(assets, original_assets)


def test_sensitivity_reproduces_known_250m_switch():
    grid = run_sensitivity_grid(
        load_portfolio("clean"),
        pd.read_csv(SEED),
        budgets=(250,), conditions=(8, 5),
    ).set_index("a133_condition")

    assert not bool(grid.at[8, "p033_funded"])
    assert bool(grid.at[8, "p022_funded"])
    assert bool(grid.at[5, "p033_funded"])
    assert not bool(grid.at[5, "p022_funded"])
    assert grid.at[8, "funded_capex_m"] == pytest.approx(249.9)
    assert grid.at[5, "funded_capex_m"] == pytest.approx(243.2)
    assert grid.at[8, "portfolio_score"] == pytest.approx(93.825)
    assert grid.at[5, "portfolio_score"] == pytest.approx(93.900)


def test_sensitivity_rejects_missing_asset():
    assets = pd.read_csv(SEED)
    assets = assets.loc[assets["asset_id"].astype(str) != "A133"].copy()
    with pytest.raises(ValueError, match="exactly one A133"):
        run_sensitivity_grid(
            load_portfolio("clean"),
            assets,
            budgets=(250,),
            conditions=(8, 5),
        )
