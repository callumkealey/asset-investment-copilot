"""Regression tests for the read-only asset lookup agent tool."""
import pandas as pd

from src.tools import TOOLS, ToolRuntime, execute_tool


def test_get_asset_registers_strict_schema():
    tool = next(t for t in TOOLS if t["name"] == "get_asset")
    assert tool["strict"] is True
    assert tool["parameters"]["required"] == ["asset_id"]


def test_get_asset_matches_existing_project(monkeypatch):
    def fake_fetch_asset(asset_id):
        assert asset_id == "A133"
        return {
            "asset": {
                "asset_id": "A133",
                "condition_score": 8,
                "inspection_date": "2026-10-01",
            },
            "source_system": "mock_eam",
        }

    monkeypatch.setattr("src.tools.fetch_asset", fake_fetch_asset)
    portfolio = pd.DataFrame([
        {
            "project_id": "P033",
            "project_name": "West SCADA / Control Upgrade 33",
            "asset_id": "A133",
            "asset_data_status": "matched",
        },
        {"project_id": "P001", "project_name": "Other", "asset_id": "A101"},
    ])
    runtime = ToolRuntime(portfolio=portfolio, retriever=None)
    result = execute_tool(runtime, "get_asset", {"asset_id": "A133"})

    assert result["source"] == "mock_eam_rest_api"
    assert result["asset"]["condition_score"] == 8
    assert result["eam_metadata"]["source_system"] == "mock_eam"
    assert result["portfolio_match_status"] == "matched"
    assert [p["project_id"] for p in result["linked_projects"]] == ["P033"]


def test_get_asset_no_project_match(monkeypatch):
    monkeypatch.setattr(
        "src.tools.fetch_asset", lambda asset_id: {"asset_id": asset_id, "condition_score": 5}
    )
    runtime = ToolRuntime(
        portfolio=pd.DataFrame([{"project_id": "P001", "asset_id": "A101"}]),
        retriever=None,
    )
    result = execute_tool(runtime, "get_asset", {"asset_id": "A133"})
    assert result["portfolio_match_status"] == "no_matching_project"
    assert result["linked_projects"] == []


def test_get_asset_invalid_id_does_not_call_api(monkeypatch):
    def forbidden_fetch(_):
        raise AssertionError("Should not call API with path-like ID")

    monkeypatch.setattr("src.tools.fetch_asset", forbidden_fetch)
    runtime = ToolRuntime(portfolio=pd.DataFrame(), retriever=None)
    assert execute_tool(runtime, "get_asset", {"asset_id": "../A133"}) == {
        "error": "Invalid asset ID"
    }
