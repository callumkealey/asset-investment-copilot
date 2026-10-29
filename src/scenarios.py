from __future__ import annotations

SCENARIOS = {
    "Balanced": {
        "criticality": 0.20,
        "regulatory_driver": 0.20,
        "capacity_benefit": 0.15,
        "customer_impact": 0.10,
        "carbon_benefit": 0.10,
        "project_maturity": 0.10,
        "asset_condition_need": 0.15,
        "delivery_risk_penalty": 0.10,
    },
    "Reliability First": {
        "criticality": 0.30,
        "regulatory_driver": 0.15,
        "capacity_benefit": 0.10,
        "customer_impact": 0.10,
        "carbon_benefit": 0.05,
        "project_maturity": 0.10,
        "asset_condition_need": 0.20,
        "delivery_risk_penalty": 0.10,
    },
    "Net Zero": {
        "criticality": 0.15,
        "regulatory_driver": 0.15,
        "capacity_benefit": 0.15,
        "customer_impact": 0.10,
        "carbon_benefit": 0.25,
        "project_maturity": 0.10,
        "asset_condition_need": 0.10,
        "delivery_risk_penalty": 0.10,
    },
    "Regulatory Compliance": {
        "criticality": 0.15,
        "regulatory_driver": 0.35,
        "capacity_benefit": 0.10,
        "customer_impact": 0.10,
        "carbon_benefit": 0.05,
        "project_maturity": 0.10,
        "asset_condition_need": 0.15,
        "delivery_risk_penalty": 0.10,
    },
}


def scenario_names() -> list[str]:
    return list(SCENARIOS)
