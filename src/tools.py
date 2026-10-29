from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import pandas as pd

from .database import get_project
from .eam_client import fetch_asset
from .optimiser import optimise_portfolio
from .scoring import score_portfolio
from .validation import validate_portfolio


@dataclass
class ToolRuntime:
    portfolio: pd.DataFrame
    retriever: Any


def _records(df: pd.DataFrame, columns: list[str], limit: int = 20) -> list[dict]:
    out = df.loc[:, [c for c in columns if c in df.columns]].head(limit).copy()
    return json.loads(out.to_json(orient="records"))


def tool_get_project(runtime: ToolRuntime, project_id: str) -> dict:
    project = get_project(project_id)
    return project or {"error": f"Project {project_id} not found"}


def tool_get_asset(runtime: ToolRuntime, asset_id: str) -> dict:
    """Look up an asset in the mock EAM API and reconcile it to portfolio projects.

    This is strictly read-only: it does not change the EAM record or rerun optimisation.
    """
    asset_id = asset_id.strip()
    if not asset_id or any(char in asset_id for char in "/\\?#"):
        return {"error": "Invalid asset ID"}

    payload = fetch_asset(asset_id)
    if not isinstance(payload, dict):
        return {"error": "Unexpected EAM response format"}

    # Accept either a flat asset record or an {"asset": {...}} API envelope.
    asset = payload.get("asset", payload)
    if not isinstance(asset, dict):
        return {"error": "Unexpected EAM asset record format"}

    returned_id = asset.get("asset_id")
    if returned_id is not None and str(returned_id).strip().casefold() != asset_id.casefold():
        return {"error": "EAM returned a different asset ID"}

    if "asset_id" not in runtime.portfolio.columns:
        projects = []
        match_status = "portfolio_missing_asset_id_column"
    else:
        rows = runtime.portfolio.loc[
            runtime.portfolio["asset_id"].astype("string").str.strip().str.casefold()
            == asset_id.casefold()
        ]
        columns = [
            "project_id", "project_name", "asset_id",
            "asset_data_status", "asset_condition_need", "mandatory",
        ]
        projects = _records(rows, columns, limit=40)
        match_status = "matched" if len(rows) else "no_matching_project"

    return {
        "source": "mock_eam_rest_api",
        "requested_asset_id": asset_id,
        "asset": asset,
        "eam_metadata": (
            {key: value for key, value in payload.items() if key != "asset"}
            if "asset" in payload else {}
        ),
        "linked_projects": projects,
        "portfolio_match_status": match_status,
    }


def tool_run_budget_scenario(runtime: ToolRuntime, budget_m: float, scenario: str) -> dict:
    scored = score_portfolio(runtime.portfolio, scenario)
    result = optimise_portfolio(scored, budget_m)
    cols = ["project_id", "project_name", "capex_m", "priority_score", "mandatory", "rank"]
    return {
        "scenario": scenario,
        "budget_m": result["budget_m"],
        "funded_capex_m": result["funded_capex_m"],
        "remaining_budget_m": result["remaining_budget_m"],
        "selected_count": result["selected_count"],
        "deferred_count": result["deferred_count"],
        "portfolio_score": result["portfolio_score"],
        "funded": _records(result["funded"], cols, limit=40),
        "highest_priority_deferred": _records(result["deferred"], cols, limit=8),
    }


def tool_compare_scenarios(runtime: ToolRuntime, budget_m: float, scenario_a: str, scenario_b: str) -> dict:
    a = tool_run_budget_scenario(runtime, budget_m, scenario_a)
    b = tool_run_budget_scenario(runtime, budget_m, scenario_b)
    a_ids = {p["project_id"] for p in a["funded"]}
    b_ids = {p["project_id"] for p in b["funded"]}
    return {
        "budget_m": budget_m,
        "scenario_a": scenario_a,
        "scenario_b": scenario_b,
        "only_in_a": sorted(a_ids - b_ids),
        "only_in_b": sorted(b_ids - a_ids),
        "in_both": sorted(a_ids & b_ids),
        "a_summary": {k: a[k] for k in ["funded_capex_m", "selected_count", "portfolio_score"]},
        "b_summary": {k: b[k] for k in ["funded_capex_m", "selected_count", "portfolio_score"]},
    }


def tool_check_data_quality(runtime: ToolRuntime) -> dict:
    return validate_portfolio(runtime.portfolio).to_dict()


def tool_search_documents(runtime: ToolRuntime, query: str, top_k: int = 4) -> dict:
    hits = runtime.retriever.search(query, top_k=top_k)
    return {"query": query, "results": hits}


TOOLS = [
    {
        "type": "function",
        "name": "get_asset",
        "description": (
            "Read one asset from the live mock EAM REST API by asset ID "
            "(such as A133) and match it to portfolio projects. "
            "Return observed condition and inspection metadata when present; "
            "never invent missing values. This tool does not modify records."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "asset_id": {
                    "type": "string",
                    "description": "Asset identifier such as A133",
                },
            },
            "required": ["asset_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "get_project",
        "description": "Retrieve one investment project from the SQL-backed portfolio by project ID. Use this for project-specific facts and never guess project values.",
        "parameters": {
            "type": "object",
            "properties": {"project_id": {"type": "string", "description": "Project identifier such as P017"}},
            "required": ["project_id"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "run_budget_scenario",
        "description": "Run the deterministic capital-allocation optimiser for a named scenario and budget in GBP millions. Use for numerical portfolio recommendations.",
        "parameters": {
            "type": "object",
            "properties": {
                "budget_m": {"type": "number", "description": "Available capital budget in GBP millions"},
                "scenario": {"type": "string", "enum": ["Balanced", "Reliability First", "Net Zero", "Regulatory Compliance"]},
            },
            "required": ["budget_m", "scenario"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "compare_scenarios",
        "description": "Compare two deterministic portfolio scenarios at the same budget and report which projects enter or leave the funded portfolio.",
        "parameters": {
            "type": "object",
            "properties": {
                "budget_m": {"type": "number"},
                "scenario_a": {"type": "string", "enum": ["Balanced", "Reliability First", "Net Zero", "Regulatory Compliance"]},
                "scenario_b": {"type": "string", "enum": ["Balanced", "Reliability First", "Net Zero", "Regulatory Compliance"]},
            },
            "required": ["budget_m", "scenario_a", "scenario_b"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "type": "function",
        "name": "check_data_quality",
        "description": "Validate the current investment portfolio for missing fields, duplicates, invalid scores and invalid capital values.",
        "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        "strict": True,
    },
    {
        "type": "function",
        "name": "search_documents",
        "description": "Retrieve relevant passages from the supporting investment-policy and regulatory document corpus. Use for documentary evidence, not arithmetic.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 6},
            },
            "required": ["query", "top_k"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]


def execute_tool(runtime: ToolRuntime, name: str, arguments: dict) -> dict:
    mapping = {
        "get_project": tool_get_project,
        "get_asset": tool_get_asset,
        "run_budget_scenario": tool_run_budget_scenario,
        "compare_scenarios": tool_compare_scenarios,
        "check_data_quality": tool_check_data_quality,
        "search_documents": tool_search_documents,
    }
    if name not in mapping:
        return {"error": f"Unknown tool: {name}"}
    try:
        return mapping[name](runtime, **arguments)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}
