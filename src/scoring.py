from __future__ import annotations

import pandas as pd
from .scenarios import SCENARIOS


def enrich_with_assets(portfolio: pd.DataFrame, assets: pd.DataFrame | None) -> pd.DataFrame:
    df = portfolio.copy()
    if assets is None or assets.empty:
        df["condition_score"] = 5.5
        df["asset_condition_need"] = 5.5
        df["asset_data_status"] = "not integrated"
        return df

    cols = ["asset_id", "condition_score", "inspection_date", "operational_criticality"]
    merged = df.merge(assets[cols], on="asset_id", how="left")
    cond = pd.to_numeric(merged["condition_score"], errors="coerce")
    # Asset condition: 1 = very poor, 10 = excellent. Investment need is the inverse.
    merged["asset_condition_need"] = 11 - cond
    merged["asset_condition_need"] = merged["asset_condition_need"].fillna(5.5).clip(1, 10)
    merged["asset_data_status"] = cond.apply(lambda x: "matched" if pd.notna(x) else "missing/neutral fallback")
    return merged


def score_portfolio(portfolio: pd.DataFrame, scenario: str = "Balanced") -> pd.DataFrame:
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario}")
    df = portfolio.copy()
    if "asset_condition_need" not in df.columns:
        df["asset_condition_need"] = 5.5

    weights = SCENARIOS[scenario]
    positive = [
        "criticality", "regulatory_driver", "capacity_benefit", "customer_impact",
        "carbon_benefit", "project_maturity", "asset_condition_need"
    ]
    score = sum(pd.to_numeric(df[col], errors="coerce").fillna(0) * weights[col] for col in positive)
    risk = pd.to_numeric(df["delivery_risk"], errors="coerce").fillna(0) * weights["delivery_risk_penalty"]
    df["priority_score"] = (score - risk).round(3)
    df["scenario"] = scenario
    df["rank"] = df["priority_score"].rank(method="min", ascending=False).astype(int)
    return df.sort_values(["priority_score", "mandatory"], ascending=[False, False]).reset_index(drop=True)
