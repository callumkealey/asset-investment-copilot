from __future__ import annotations

from dataclasses import dataclass, asdict
import pandas as pd

SCORE_COLUMNS = [
    "criticality",
    "capacity_benefit",
    "regulatory_driver",
    "carbon_benefit",
    "customer_impact",
    "delivery_risk",
    "project_maturity",
]
REQUIRED_COLUMNS = [
    "project_id", "asset_id", "project_name", "asset_type", "capex_m", "mandatory", *SCORE_COLUMNS
]


@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]
    warnings: list[str]
    rows_checked: int

    def to_dict(self) -> dict:
        return asdict(self)


def validate_portfolio(df: pd.DataFrame) -> ValidationResult:
    errors: list[str] = []
    warnings: list[str] = []

    missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {', '.join(missing_cols)}")
        return ValidationResult(False, errors, warnings, len(df))

    duplicate_ids = df.loc[df["project_id"].duplicated(keep=False), "project_id"].dropna().unique().tolist()
    if duplicate_ids:
        errors.append(f"Duplicate project_id values: {', '.join(map(str, duplicate_ids))}")

    for col in ["project_id", "asset_id", "project_name", "capex_m"]:
        count = int(df[col].isna().sum())
        if count:
            errors.append(f"{col} has {count} missing value(s)")

    capex = pd.to_numeric(df["capex_m"], errors="coerce")
    bad_capex = int((capex <= 0).fillna(False).sum())
    if bad_capex:
        errors.append(f"capex_m has {bad_capex} non-positive value(s)")

    for col in SCORE_COLUMNS:
        values = pd.to_numeric(df[col], errors="coerce")
        missing = int(values.isna().sum())
        out_of_range = int(((values < 1) | (values > 10)).fillna(False).sum())
        if missing:
            errors.append(f"{col} has {missing} missing/non-numeric value(s)")
        if out_of_range:
            errors.append(f"{col} has {out_of_range} value(s) outside the 1–10 range")

    if len(df) < 10:
        warnings.append("Portfolio is very small; scenario comparisons may not be meaningful")
    if int(df["mandatory"].astype(bool).sum()) == 0:
        warnings.append("No mandatory projects are flagged")

    return ValidationResult(not errors, errors, warnings, len(df))


def validate_asset_reconciliation(portfolio: pd.DataFrame, assets: pd.DataFrame) -> dict:
    pids = set(portfolio["asset_id"].dropna().astype(str))
    aids = set(assets["asset_id"].dropna().astype(str))
    missing_assets = sorted(pids - aids)
    orphan_assets = sorted(aids - pids)

    asset_copy = assets.copy()
    asset_copy["inspection_date"] = pd.to_datetime(asset_copy["inspection_date"], errors="coerce")
    stale_cutoff = pd.Timestamp("2025-01-01")
    stale = asset_copy.loc[asset_copy["inspection_date"] < stale_cutoff, "asset_id"].dropna().astype(str).tolist()
    null_condition = asset_copy.loc[pd.to_numeric(asset_copy["condition_score"], errors="coerce").isna(), "asset_id"].dropna().astype(str).tolist()

    return {
        "portfolio_assets": len(pids),
        "asset_records": len(aids),
        "matched": len(pids & aids),
        "missing_assets": missing_assets,
        "orphan_assets": orphan_assets,
        "stale_inspections": stale,
        "missing_condition_scores": null_condition,
    }
