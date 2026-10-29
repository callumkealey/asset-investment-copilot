from src.data_loader import load_portfolio
from src.optimiser import optimise_portfolio
from src.scoring import enrich_with_assets, score_portfolio


def test_portfolio_stays_within_budget():
    portfolio = enrich_with_assets(load_portfolio("clean"), None)
    scored = score_portfolio(portfolio, "Balanced")
    result = optimise_portfolio(scored, 250)
    assert result["funded_capex_m"] <= 250 + 1e-6


def test_mandatory_projects_are_selected():
    portfolio = enrich_with_assets(load_portfolio("clean"), None)
    scored = score_portfolio(portfolio, "Balanced")
    result = optimise_portfolio(scored, 400)
    selected = set(result["funded"]["project_id"])
    mandatory = set(scored.loc[scored["mandatory"], "project_id"])
    assert mandatory.issubset(selected)
