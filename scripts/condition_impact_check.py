from dotenv import load_dotenv
load_dotenv(".env")

from src.data_loader import load_portfolio
from src.eam_client import fetch_assets
from src.scoring import enrich_with_assets, score_portfolio
from src.optimiser import optimise_portfolio

print("Loading portfolio and EAM assets...", flush=True)

portfolio = load_portfolio("clean")
assets = fetch_assets(timeout=10)

print(f"Retrieved {len(assets)} assets", flush=True)

modified_assets = assets.copy(deep=True)
mask = modified_assets["asset_id"] == "A133"

assert mask.sum() == 1, "A133 must appear exactly once"
assert float(assets.loc[mask, "condition_score"].iloc[0]) == 8, "Reset A133 to baseline first"

modified_assets.loc[mask, "condition_score"] = 5

def optimise(asset_data):
    enriched = enrich_with_assets(portfolio, asset_data)
    scored = score_portfolio(enriched, "Balanced")
    result = optimise_portfolio(scored, 250)
    funded = set(result["funded"]["project_id"])
    return result, funded

print("Running baseline optimisation...", flush=True)
before, baseline_ids = optimise(assets)

print("Running deteriorated-condition optimisation...", flush=True)
after, changed_ids = optimise(modified_assets)

print("\nBASELINE")
print("Funded capital:", before["funded_capex_m"])
print("Portfolio score:", before["portfolio_score"])

print("\nAFTER CONDITION CHANGE")
print("Funded capital:", after["funded_capex_m"])
print("Portfolio score:", after["portfolio_score"])

print("\nNewly funded:", sorted(changed_ids - baseline_ids))
print("Newly deferred:", sorted(baseline_ids - changed_ids))

assert changed_ids - baseline_ids == {"P033"}
assert baseline_ids - changed_ids == {"P022"}

print("\nPASS: Condition change reproduced funding switch")