from __future__ import annotations

from datetime import date
from pathlib import Path
import os
import pandas as pd
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[1]
ASSET_PATH = ROOT / "data" / "assets.csv"
SEED_PATH = ROOT / "data" / "assets_seed.csv"
API_KEY = os.getenv("EAM_API_KEY", "demo-secret-key")

app = FastAPI(
    title="Mock Enterprise Asset Management API",
    description="A deliberately small EAM-style API for the FDE portfolio prototype.",
    version="0.1.0",
)

class ConditionUpdate(BaseModel):
    condition_score: int = Field(ge=1, le=10)
    inspection_date: date

def _authorise(x_api_key: str | None) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")


def _assets() -> pd.DataFrame:
    df = pd.read_csv(ASSET_PATH)
    return df.where(pd.notnull(df), None)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/assets")
def list_assets(x_api_key: str | None = Header(default=None)) -> dict:
    _authorise(x_api_key)
    df = _assets()
    return {"count": len(df), "assets": df.to_dict(orient="records")}


@app.get("/assets/{asset_id}")
def get_asset(asset_id: str, x_api_key: str | None = Header(default=None)) -> dict:
    _authorise(x_api_key)
    df = _assets()
    match = df.loc[df["asset_id"] == asset_id]
    if match.empty:
        raise HTTPException(status_code=404, detail="Asset not found")
    return match.iloc[0].to_dict()


@app.get("/assets/{asset_id}/condition")
def get_asset_condition(asset_id: str, x_api_key: str | None = Header(default=None)) -> dict:
    asset = get_asset(asset_id, x_api_key)
    return {
        "asset_id": asset_id,
        "condition_score": asset.get("condition_score"),
        "inspection_date": asset.get("inspection_date"),
    }

@app.patch("/assets/{asset_id}/condition")
def update_asset_condition(
    asset_id: str,
    update: ConditionUpdate,
    x_api_key: str | None = Header(default=None),
) -> dict:
    _authorise(x_api_key)

    df = pd.read_csv(ASSET_PATH)

    match = df["asset_id"] == asset_id

    if not match.any():
        raise HTTPException(
            status_code=404,
            detail="Asset not found"
        )

    previous_score = df.loc[
        match,
        "condition_score"
    ].iloc[0]

    df.loc[
        match,
        "condition_score"
    ] = update.condition_score

    df.loc[
        match,
        "inspection_date"
    ] = update.inspection_date.isoformat()

    df.to_csv(
        ASSET_PATH,
        index=False
    )

    return {
        "asset_id": asset_id,
        "previous_condition_score": (
            None
            if pd.isna(previous_score)
            else int(previous_score)
        ),
        "condition_score": update.condition_score,
        "inspection_date": update.inspection_date.isoformat(),
        "status": "updated",
    }


@app.post("/admin/reset")
def reset_assets(
    x_api_key: str | None = Header(default=None),
) -> dict:
    _authorise(x_api_key)

    seed_df = pd.read_csv(SEED_PATH)
    seed_df.to_csv(ASSET_PATH, index=False)

    return {
        "status": "reset",
        "records_restored": len(seed_df),
    }