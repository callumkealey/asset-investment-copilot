from __future__ import annotations

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"


def load_portfolio(kind: str = "clean") -> pd.DataFrame:
    if kind not in {"clean", "dirty"}:
        raise ValueError("kind must be 'clean' or 'dirty'")
    path = DATA_DIR / f"investment_portfolio_{kind}.csv"
    df = pd.read_csv(path)
    if "mandatory" in df.columns:
        df["mandatory"] = df["mandatory"].astype(str).str.lower().map({"true": True, "false": False}).fillna(False)
    return df


def load_assets() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "assets.csv")
