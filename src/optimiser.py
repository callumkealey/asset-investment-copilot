from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import Bounds, LinearConstraint, milp


def optimise_portfolio(scored: pd.DataFrame, budget_m: float) -> dict:
    if budget_m <= 0:
        raise ValueError("budget_m must be positive")

    df = scored.reset_index(drop=True).copy()
    costs = pd.to_numeric(df["capex_m"], errors="raise").to_numpy(dtype=float)
    values = pd.to_numeric(df["priority_score"], errors="raise").to_numpy(dtype=float)
    mandatory = df["mandatory"].astype(bool).to_numpy()

    mandatory_cost = float(costs[mandatory].sum())
    if mandatory_cost > budget_m:
        raise ValueError(
            f"Mandatory projects cost £{mandatory_cost:.1f}m, exceeding the £{budget_m:.1f}m budget"
        )

    # Binary decision variables x_i. milp minimises, so negate value to maximise it.
    c = -values
    integrality = np.ones(len(df), dtype=int)
    lb = mandatory.astype(float)  # mandatory projects are fixed on via lower bound = 1
    ub = np.ones(len(df), dtype=float)
    budget_constraint = LinearConstraint(costs.reshape(1, -1), -np.inf, budget_m)

    result = milp(
        c=c,
        integrality=integrality,
        bounds=Bounds(lb, ub),
        constraints=[budget_constraint],
        options={"time_limit": 5},
    )
    if not result.success or result.x is None:
        raise RuntimeError(f"Optimisation failed: {result.message}")

    selected_mask = result.x >= 0.5
    df["selected"] = selected_mask
    funded = df.loc[selected_mask].copy().sort_values("priority_score", ascending=False)
    deferred = df.loc[~selected_mask].copy().sort_values("priority_score", ascending=False)

    return {
        "budget_m": round(float(budget_m), 2),
        "funded_capex_m": round(float(funded["capex_m"].sum()), 2),
        "remaining_budget_m": round(float(budget_m - funded["capex_m"].sum()), 2),
        "selected_count": int(len(funded)),
        "deferred_count": int(len(deferred)),
        "portfolio_score": round(float(funded["priority_score"].sum()), 3),
        "funded": funded,
        "deferred": deferred,
    }
