from __future__ import annotations

from pathlib import Path
import random
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SEED = 42


def build_portfolio() -> pd.DataFrame:
    random.seed(SEED)
    asset_types = [
        ("Substation", "Substation Reinforcement"),
        ("Transformer", "Transformer Replacement"),
        ("Transmission Line", "Circuit Upgrade"),
        ("Protection", "Protection System Modernisation"),
        ("Control System", "SCADA / Control Upgrade"),
        ("Cable", "Cable Replacement"),
    ]
    regions = ["North", "Central", "East", "West", "Islands"]

    rows = []
    for i in range(1, 41):
        asset_type, project_type = random.choice(asset_types)
        criticality = random.randint(3, 10)
        regulatory = random.randint(2, 10)
        capacity = random.randint(2, 10)
        carbon = random.randint(1, 10)
        customer = random.randint(2, 10)
        risk = random.randint(2, 9)
        maturity = random.randint(3, 10)
        capex = round(random.uniform(6.0, 55.0), 1)
        mandatory = (i in {3, 11, 18, 29}) or (regulatory >= 10 and criticality >= 8)
        rows.append({
            "project_id": f"P{i:03d}",
            "asset_id": f"A{100+i:03d}",
            "project_name": f"{regions[i % len(regions)]} {project_type} {i:02d}",
            "asset_type": asset_type,
            "region": regions[i % len(regions)],
            "capex_m": capex,
            "criticality": criticality,
            "capacity_benefit": capacity,
            "regulatory_driver": regulatory,
            "carbon_benefit": carbon,
            "customer_impact": customer,
            "delivery_risk": risk,
            "project_maturity": maturity,
            "mandatory": mandatory,
        })
    return pd.DataFrame(rows)


def build_assets(portfolio: pd.DataFrame) -> pd.DataFrame:
    random.seed(SEED + 1)
    rows = []
    for idx, row in portfolio.iterrows():
        # Omit one asset to create a realistic unmatched record.
        if row["project_id"] == "P034":
            continue
        condition = random.randint(2, 9)
        inspection_year = 2026 if idx % 7 else 2023  # some stale inspections
        rows.append({
            "asset_id": row["asset_id"],
            "asset_type": row["asset_type"],
            "condition_score": condition,
            "inspection_date": f"{inspection_year}-{(idx % 12)+1:02d}-15",
            "age_years": random.randint(4, 48),
            "location": row["region"],
            "operational_criticality": random.randint(3, 10),
        })
    assets = pd.DataFrame(rows)
    # One incomplete record, deliberately retained to test reconciliation.
    assets.loc[assets["asset_id"] == "A122", "condition_score"] = None
    return assets


def make_dirty_portfolio(clean: pd.DataFrame) -> pd.DataFrame:
    dirty = clean.copy()
    dirty.loc[4, "capex_m"] = -12.5
    dirty.loc[7, "criticality"] = 12
    dirty.loc[12, "asset_id"] = None
    dirty.loc[15, "capex_m"] = None
    # Duplicate a project ID while retaining a distinct row.
    dirty.loc[23, "project_id"] = dirty.loc[22, "project_id"]
    return dirty


def main() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    clean = build_portfolio()
    assets = build_assets(clean)
    dirty = make_dirty_portfolio(clean)

    clean.to_csv(DATA / "investment_portfolio_clean.csv", index=False)
    dirty.to_csv(DATA / "investment_portfolio_dirty.csv", index=False)
    assets.to_csv(DATA / "assets.csv", index=False)
    print(f"Generated {len(clean)} projects and {len(assets)} asset records in {DATA}")


if __name__ == "__main__":
    main()
