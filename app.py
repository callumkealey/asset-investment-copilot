from __future__ import annotations

import os
import time
import hmac
import threading
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.agent import CopilotAgent
from src.data_loader import load_assets, load_portfolio
from src.database import initialise_database
from src.eam_client import (
    fetch_assets,
    reset_assets,
    update_asset_condition,
)
from src.optimiser import optimise_portfolio
from src.retrieval import build_retriever
from src.scenarios import scenario_names
from src.scoring import enrich_with_assets, score_portfolio
from src.tools import ToolRuntime
from src.validation import validate_asset_reconciliation, validate_portfolio

load_dotenv()
ROOT = Path(__file__).resolve().parent
HOSTED_DEMO = os.getenv("HOSTED_DEMO_MODE", "false").lower() == "true"
AI_DEMO_PASSWORD = os.getenv("AI_DEMO_PASSWORD", "")
AI_DEMO_SESSION_LIMIT = 5
AI_DEMO_GLOBAL_LIMIT = 30

@st.cache_resource(show_spinner=False)
def demo_usage_counter():
    return {"lock": threading.Lock(), "count": 0}


st.set_page_config(page_title="AI Asset Investment Planning Copilot", layout="wide")
st.title("AI Asset Investment Planning Copilot")
st.caption(
    "Synthetic forward-deployed prototype: validate portfolio data, optimise constrained capital scenarios, "
    "integrate asset condition and interrogate the result with a tool-calling copilot."
)


@st.cache_resource(show_spinner=False)
def get_retriever():
    return build_retriever()


# ----- Sidebar: customer inputs -----
st.sidebar.header("Customer scenario")
data_mode = st.sidebar.radio("Portfolio data", ["Clean demo", "Dirty data test"], index=0)
budget_m = st.sidebar.slider("Capital budget (£m)", min_value=100, max_value=600, value=250, step=10)
scenario = st.sidebar.selectbox("Strategic scenario", scenario_names(), index=0)
use_eam = st.sidebar.toggle("Integrate mock EAM asset data", value=True)

portfolio = load_portfolio("clean" if data_mode == "Clean demo" else "dirty")
validation = validate_portfolio(portfolio)

# Attempt the REST integration first. Fall back locally for usability, but label it clearly.
assets = None
eam_status = "Not requested"
eam_via_api = False
if use_eam:
    try:
        assets = fetch_assets()
        eam_status = "Connected via REST API"
        eam_via_api = True
    except Exception as exc:
        assets = load_assets()
        eam_status = f"API unavailable — local fallback ({type(exc).__name__})"

portfolio_enriched = enrich_with_assets(portfolio, assets if use_eam else None)
initialise_database(portfolio_enriched)

if not validation.valid:
    st.error("The portfolio contains critical data-quality issues. Investment optimisation is intentionally blocked until they are resolved.")

# ----- Overview -----
tab_portfolio, tab_quality, tab_change, tab_impact, tab_copilot, tab_architecture = st.tabs(
    ["Portfolio", "Data quality", "FDE change request", "Asset impact", "Copilot", "Architecture"]
)

with tab_portfolio:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Candidate projects", len(portfolio_enriched))
    c2.metric("Total requested capex", f"£{pd.to_numeric(portfolio_enriched['capex_m'], errors='coerce').sum():,.1f}m")
    c3.metric("Available budget", f"£{budget_m}m")
    c4.metric("EAM integration", "REST" if eam_via_api else ("Fallback" if use_eam else "Off"))

    if validation.valid:
        start = time.perf_counter()
        scored = score_portfolio(portfolio_enriched, scenario)
        result = optimise_portfolio(scored, budget_m)
        elapsed_ms = (time.perf_counter() - start) * 1000

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Funded projects", result["selected_count"])
        m2.metric("Funded capex", f"£{result['funded_capex_m']:,.1f}m")
        m3.metric("Budget remaining", f"£{result['remaining_budget_m']:,.1f}m")
        m4.metric("Scenario runtime", f"{elapsed_ms:.0f} ms")

        st.subheader("Funded portfolio")
        show_cols = [
            "project_id", "project_name", "asset_type", "capex_m", "priority_score", "rank",
            "mandatory", "asset_condition_need", "asset_data_status"
        ]
        st.dataframe(result["funded"][[c for c in show_cols if c in result["funded"].columns]], use_container_width=True)

        st.subheader("Highest-priority deferred investments")
        st.dataframe(result["deferred"][[c for c in show_cols if c in result["deferred"].columns]].head(10), use_container_width=True)

        st.subheader("Scenario comparison")
        comparison_rows = []
        for name in scenario_names():
            s = score_portfolio(portfolio_enriched, name)
            r = optimise_portfolio(s, budget_m)
            comparison_rows.append({
                "scenario": name,
                "funded_projects": r["selected_count"],
                "funded_capex_m": r["funded_capex_m"],
                "portfolio_score": r["portfolio_score"],
            })
        comp = pd.DataFrame(comparison_rows).set_index("scenario")
        st.dataframe(comp, use_container_width=True)
        st.bar_chart(comp[["portfolio_score"]])

with tab_quality:
    st.subheader("Portfolio validation")
    st.json(validation.to_dict())

    if use_eam and assets is not None:
        st.subheader("Asset reconciliation")
        reconciliation = validate_asset_reconciliation(portfolio, assets)
        r1, r2, r3 = st.columns(3)
        r1.metric("Portfolio assets", reconciliation["portfolio_assets"])
        r2.metric("Matched", reconciliation["matched"])
        r3.metric("Asset records", reconciliation["asset_records"])
        st.write(f"**Integration status:** {eam_status}")
        st.json(reconciliation)

    st.info(
        "The dirty-data mode deliberately contains a duplicate project ID, missing fields, a negative capex value "
        "and an out-of-range score. The app blocks optimisation rather than silently producing a recommendation."
    )

with tab_change:
    st.subheader("Customer feedback → missing capability")

    st.markdown(
        """
**Initial prototype limitation:** asset condition was assumed to be supplied in the portfolio extract.

**Hypothetical customer feedback:** *“Our asset condition changes regularly and lives in our enterprise asset-management system. We do not want planners maintaining another spreadsheet.”*

**FDE response:** add an authenticated REST integration, reconcile `asset_id` across systems, surface exceptions and feed current condition into the deterministic investment model.
        """
    )

    st.write(f"**Current integration status:** {eam_status}")

    if "demo_message" in st.session_state:
        st.success(st.session_state.pop("demo_message"))

    if HOSTED_DEMO:
        st.info("Hosted demo is read-only. Use the Asset impact tab for in-memory what-if scenarios.")
    else:
        col_reset, col_inspection = st.columns(2)

        with col_reset:
            if st.button(
                "Reset demo to baseline",
                key="reset_eam_demo",
                use_container_width=True,
            ):
                try:
                    reset_response = reset_assets()

                    st.session_state["demo_message"] = (
                        f"EAM baseline restored: "
                        f"{reset_response['records_restored']} asset records."
                    )

                    st.rerun()

                except Exception as exc:
                    st.error(f"Could not reset the EAM demo: {exc}")

        with col_inspection:
            if st.button(
                "Simulate inspection: A133 condition 8 → 5",
                key="simulate_a133_deterioration",
                use_container_width=True,
            ):
                try:
                    update_response = update_asset_condition(
                        asset_id="A133",
                        condition_score=5,
                        inspection_date="2026-10-28",
                    )

                    st.session_state["demo_message"] = (
                        "New inspection recorded for A133: "
                        f"condition {update_response['previous_condition_score']} "
                        f"→ {update_response['condition_score']}."
                    )

                    st.rerun()

                except Exception as exc:
                    st.error(f"Could not update the EAM asset: {exc}")

    if validation.valid and use_eam and assets is not None:
        seed_assets = pd.read_csv(
            ROOT / "data" / "assets_seed.csv"
        )

        baseline_enriched = enrich_with_assets(
            portfolio,
            seed_assets,
        )

        baseline_scored = score_portfolio(
            baseline_enriched,
            scenario,
        )

        baseline_result = optimise_portfolio(
            baseline_scored,
            budget_m,
        )

        live_scored = score_portfolio(
            portfolio_enriched,
            scenario,
        )

        live_result = optimise_portfolio(
            live_scored,
            budget_m,
        )

        baseline_funded = set(
            baseline_result["funded"]["project_name"]
        )

        live_funded = set(
            live_result["funded"]["project_name"]
        )

        west_scada = "West SCADA / Control Upgrade 33"
        east_protection = "East Protection System Modernisation 22"

        def funding_status(project_name, funded_projects):
            if project_name in funded_projects:
                return "FUNDED"
            return "DEFERRED"

        baseline_a133 = baseline_scored.loc[
            baseline_scored["project_name"] == west_scada,
            "asset_condition_need",
        ].iloc[0]

        current_a133 = live_scored.loc[
            live_scored["project_name"] == west_scada,
            "asset_condition_need",
        ].iloc[0]

        st.subheader("Customer change → investment decision")

        d1, d2 = st.columns(2)

        with d1:
            st.markdown("**Baseline programme**")

            st.metric(
                "A133 investment need",
                f"{baseline_a133:g} / 10",
            )

            st.write(
                f"West SCADA 33: "
                f"**{funding_status(west_scada, baseline_funded)}**"
            )

            st.write(
                f"East Protection 22: "
                f"**{funding_status(east_protection, baseline_funded)}**"
            )

        with d2:
            st.markdown("**Current EAM programme**")

            st.metric(
                "A133 investment need",
                f"{current_a133:g} / 10",
                delta=f"{current_a133 - baseline_a133:+g}",
                delta_color="inverse",
            )

            st.write(
                f"West SCADA 33: "
                f"**{funding_status(west_scada, live_funded)}**"
            )

            st.write(
                f"East Protection 22: "
                f"**{funding_status(east_protection, live_funded)}**"
            )

    if validation.valid:
        base = enrich_with_assets(
            portfolio,
            None,
        )

        base_scored = score_portfolio(
            base,
            scenario,
        ).set_index("project_id")

        integrated_scored = score_portfolio(
            portfolio_enriched,
            scenario,
        ).set_index("project_id")

        change = pd.DataFrame(
            {
                "rank_before_eam": base_scored["rank"],
                "rank_after_eam": integrated_scored["rank"],
                "score_before_eam": base_scored["priority_score"],
                "score_after_eam": integrated_scored["priority_score"],
            }
        )

        change["rank_change"] = (
            change["rank_before_eam"]
            - change["rank_after_eam"]
        )

        change = change.join(
            integrated_scored[
                [
                    "project_name",
                    "asset_data_status",
                ]
            ]
        )

        change = change.sort_values(
            "rank_change",
            key=lambda s: s.abs(),
            ascending=False,
        )

        st.subheader(
            "Largest ranking changes after asset-condition integration"
        )

        st.dataframe(
            change.head(12),
            use_container_width=True,
        )

    st.markdown(
        """
**Why this matters:** the extension demonstrates the FDE pattern of proving an initial hypothesis quickly, discovering a customer-specific gap, integrating another system and then evaluating whether the additional capability changes the decision.
        """
    )

with tab_copilot:
    st.subheader("Tool-calling decision support")
    retriever = get_retriever()

    q = st.text_input(
        "Ask a portfolio question",
        value="With a £250m budget, what should we fund under Reliability First and what are the main trade-offs?",
    )

    col_a, col_b = st.columns(2)
    if col_a.button("Search supporting documents", use_container_width=True):
        st.session_state["retrieval"] = retriever.search(q, top_k=4)
    if "retrieval" in st.session_state:
        st.write("**Retrieved evidence**")
        for hit in st.session_state["retrieval"]:
            page = f", p.{hit['page']}" if hit.get("page") else ""
            st.markdown(f"**{hit['source']}{page}** — relevance {hit['score']}")
            st.write(hit["text"][:900] + ("…" if len(hit["text"]) > 900 else ""))

    has_key = bool(os.getenv("OPENAI_API_KEY"))
    ai_authorised = not HOSTED_DEMO
    if HOSTED_DEMO:
        if not has_key or not AI_DEMO_PASSWORD:
            st.info("Hosted AI Copilot is disabled until the owner configures restricted access.")
        elif not st.session_state.get("ai_demo_authorised", False):
            with st.form("copilot_unlock"):
                password = st.text_input("Reviewer access code", type="password")
                unlock = st.form_submit_button("Unlock AI Copilot")
            if unlock:
                if hmac.compare_digest(password, AI_DEMO_PASSWORD):
                    st.session_state["ai_demo_authorised"] = True
                    st.success("AI Copilot unlocked for this browser session.")
                    st.rerun()
                else:
                    st.error("Invalid access code.")
        else:
            ai_authorised = True
            if st.button("Lock AI Copilot"):
                st.session_state["ai_demo_authorised"] = False
                st.rerun()
            st.caption(
                f"AI requests this session: {st.session_state.get('ai_demo_requests', 0)}"
                f"/{AI_DEMO_SESSION_LIMIT}. Hosted demo usage is limited."
            )
    elif not has_key:
        st.warning(
            "Set OPENAI_API_KEY in your local .env file to enable the LLM agent. "
            "Portfolio optimisation, REST integration and document retrieval work without it."
        )

    can_ask = has_key and ai_authorised and (
        not HOSTED_DEMO or st.session_state.get("ai_demo_requests", 0) < AI_DEMO_SESSION_LIMIT
    )
    if col_b.button("Ask copilot", use_container_width=True, disabled=not can_ask):
        if not validation.valid:
            st.error("Fix critical portfolio validation errors before asking for a recommendation.")
        elif HOSTED_DEMO and len(q) > 600:
            st.error("Hosted demo questions must be 600 characters or fewer.")
        else:
            allowed = True
            if HOSTED_DEMO:
                counter = demo_usage_counter()
                with counter["lock"]:
                    if counter["count"] >= AI_DEMO_GLOBAL_LIMIT:
                        allowed = False
                    else:
                        counter["count"] += 1
                        st.session_state["ai_demo_requests"] = st.session_state.get("ai_demo_requests", 0) + 1
            if not allowed:
                st.error("The hosted AI demonstration's request allowance has been reached.")
            else:
                try:
                    with st.spinner("Copilot is selecting and executing trusted tools..."):
                        runtime = ToolRuntime(portfolio=portfolio_enriched, retriever=retriever)
                        agent = CopilotAgent(runtime)
                        response = agent.ask(q, max_rounds=3 if HOSTED_DEMO else 6)
                    st.markdown("### Answer")
                    st.write(response["answer"])
                    with st.expander("Tool trace — what the agent actually called"):
                        st.json(response["tool_trace"])
                except Exception:
                    st.error("The AI request failed. Please try again later.")

with tab_impact:
    st.subheader("Asset condition → investment impact")
    st.caption(
    "What-if simulation: asset conditions are modified in memory. "
    "No changes are sent to the EAM system of record."
)

    if not validation.valid:
        st.error("Fix portfolio data-quality errors before comparing scenarios.")
    elif not use_eam or assets is None:
        st.info("Enable mock EAM integration in the sidebar to compare asset conditions.")
    else:
        asset_id = "A133"
        asset_mask = assets["asset_id"].astype(str).eq(asset_id)

        if asset_mask.sum() != 1:
            st.error("Expected exactly one A133 asset record.")
        else:
            current_condition = int(assets.loc[asset_mask, "condition_score"].iloc[0])
            st.write(f"**Current A133 condition:** {current_condition} | **Data source:** {eam_status}")

            simulated_condition = st.number_input(
                "Simulated A133 condition score",
                min_value=0,
                max_value=10,
                value=5,
                step=1,
                key="simulated_a133_condition",
            )
            st.caption(f"Using the selected {scenario} scenario and £{budget_m}m budget.")

            if st.button("Compare funding decisions", key="compare_a133_funding"):
                simulated_assets = assets.copy(deep=True)
                simulated_assets.loc[asset_mask, "condition_score"] = simulated_condition
                simulated_portfolio = enrich_with_assets(portfolio, simulated_assets)

                baseline_scored = score_portfolio(portfolio_enriched, scenario)
                simulated_scored = score_portfolio(simulated_portfolio, scenario)
                baseline_result = optimise_portfolio(baseline_scored, budget_m)
                simulated_result = optimise_portfolio(simulated_scored, budget_m)

                left, right = st.columns(2)
                with left:
                    st.markdown("**Current asset data**")
                    st.metric("Funded capital", f"£{baseline_result['funded_capex_m']:.1f}m")
                    st.metric("Portfolio score", f"{baseline_result['portfolio_score']:.3f}")

                with right:
                    st.markdown("**Simulated asset condition**")
                    st.metric("Funded capital", f"£{simulated_result['funded_capex_m']:.1f}m")
                    st.metric("Portfolio score", f"{simulated_result['portfolio_score']:.3f}")

                before_ids = set(baseline_result["funded"]["project_id"])
                after_ids = set(simulated_result["funded"]["project_id"])
                before_scores = baseline_scored.set_index("project_id")
                after_scores = simulated_scored.set_index("project_id")

                changes = []
                for project_id in sorted(before_ids ^ after_ids):
                    changes.append({
                        "Project ID": project_id,
                        "Project": before_scores.at[project_id, "project_name"],
                        "Before": "Funded" if project_id in before_ids else "Deferred",
                        "After": "Funded" if project_id in after_ids else "Deferred",
                        "Capex (£m)": float(before_scores.at[project_id, "capex_m"]),
                        "Score before": float(before_scores.at[project_id, "priority_score"]),
                        "Score after": float(after_scores.at[project_id, "priority_score"]),
                    })

                st.markdown("#### Funding decisions that changed")
                if changes:
                    st.dataframe(pd.DataFrame(changes), hide_index=True, use_container_width=True)
                else:
                    st.info("No funding decisions changed under these inputs.")

                st.caption(
                    "Only the simulated asset DataFrame is modified; "
                    "the EAM system of record is unchanged."
                )

with tab_architecture:
    st.subheader("Architecture and design choices")
    st.code(
        """
Portfolio CSV ──> Validation ──> SQLite ──> Scoring / MILP optimiser ──┐
                                                                      │
Mock EAM system ── REST + API key ──> Reconciliation ─────────────────┤
                                                                      ├─> Tool layer ─> LLM Copilot
Policy / Ofgem docs ──> chunking ──> retrieval (TF-IDF or embeddings) ─┘
                                                                      │
                                                                  Streamlit UI
        """.strip()
    )
    st.markdown(
        """
- **Deterministic calculations:** Python/SQL/scenario engine owns numerical investment decisions.
- **RAG:** retrieves unstructured evidence; it does not perform the investment maths.
- **Single tool-calling agent:** chosen because the workflow does not justify multi-agent coordination overhead.
- **REST integration:** simulates a customer system of record and forces explicit data reconciliation.
- **Human-in-the-loop:** recommendations are decision support, not autonomous capital approvals.
        """
    )
