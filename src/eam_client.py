from __future__ import annotations

import os
import requests
import pandas as pd

DEFAULT_BASE_URL = os.getenv("EAM_API_URL", "http://127.0.0.1:8001")
HOSTED_DEMO = os.getenv("HOSTED_DEMO_MODE", "false").lower() == "true"
DEFAULT_API_KEY = os.getenv("EAM_API_KEY", "demo-secret-key")
DEFAULT_TIMEOUT = 60.0 if HOSTED_DEMO else 5.0
if HOSTED_DEMO and (not DEFAULT_API_KEY or DEFAULT_API_KEY == "demo-secret-key"):
    raise RuntimeError("Hosted demo requires a non-default EAM_API_KEY")


def fetch_assets(base_url: str = DEFAULT_BASE_URL, api_key: str = DEFAULT_API_KEY, timeout: float = DEFAULT_TIMEOUT) -> pd.DataFrame:
    response = requests.get(
        f"{base_url.rstrip('/')}/assets",
        headers={"X-API-Key": api_key},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    return pd.DataFrame(payload["assets"])


def fetch_asset(asset_id: str, base_url: str = DEFAULT_BASE_URL, api_key: str = DEFAULT_API_KEY, timeout: float = 2.0) -> dict:
    response = requests.get(
        f"{base_url.rstrip('/')}/assets/{asset_id}",
        headers={"X-API-Key": api_key},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()

def update_asset_condition(
    asset_id: str,
    condition_score: int,
    inspection_date: str,
    base_url: str = DEFAULT_BASE_URL,
    api_key: str = DEFAULT_API_KEY,
    timeout: float = 2.0,
) -> dict:
    response = requests.patch(
        f"{base_url.rstrip('/')}/assets/{asset_id}/condition",
        headers={"X-API-Key": api_key},
        json={
            "condition_score": condition_score,
            "inspection_date": inspection_date,
        },
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()


def reset_assets(
    base_url: str = DEFAULT_BASE_URL,
    api_key: str = DEFAULT_API_KEY,
    timeout: float = 2.0,
) -> dict:
    response = requests.post(
        f"{base_url.rstrip('/')}/admin/reset",
        headers={"X-API-Key": api_key},
        timeout=timeout,
    )
    response.raise_for_status()
    return response.json()