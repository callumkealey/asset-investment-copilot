from src.data_loader import load_assets, load_portfolio
from src.scoring import enrich_with_assets, score_portfolio


def test_asset_condition_changes_some_rankings():
    portfolio = load_portfolio("clean")
    before = score_portfolio(enrich_with_assets(portfolio, None), "Reliability First").set_index("project_id")
    after = score_portfolio(enrich_with_assets(portfolio, load_assets()), "Reliability First").set_index("project_id")
    after_aligned = after.reindex(before.index)
    assert (before["rank"] != after_aligned["rank"]).any()
