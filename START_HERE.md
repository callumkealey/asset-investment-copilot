# Start Here — Build Session

This repository is a self-directed technical portfolio project exploring asset investment planning, constrained optimisation, enterprise systems integration and AI-assisted decision support. The recommended approach is to run the application, examine each component and understand the reasoning behind its design.

## Recommended build sequence for today

### 1. Run the deterministic core first

```powershell
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

Then inspect, in this order:

1. `data/investment_portfolio_clean.csv`
2. `src/validation.py`
3. `src/scenarios.py`
4. `src/scoring.py`
5. `src/optimiser.py`

**Why:** this is the business decision engine. You should understand it before touching the LLM layer.

### 2. Run the mock EAM integration

Terminal 1:

```powershell
uvicorn api.mock_eam:app --host 127.0.0.1 --port 8001 --reload
```

Open `http://127.0.0.1:8001/docs` and try the `/assets` endpoint with the header:

```text
X-API-Key: demo-secret-key
```

Then inspect `src/eam_client.py` and `src/scoring.py`.

**Why:** this is the hypothetical customer-request extension. It demonstrates an external system of record, authentication, reconciliation and decision impact.

### 3. Run the app

Terminal 2:

```powershell
streamlit run app.py
```

First use **Clean demo**. Then switch to **Dirty data test** and observe that optimisation is blocked.

### 4. Add public regulatory documents

```powershell
python scripts\fetch_public_docs.py
```

Then inspect `src/retrieval.py`.

**Why:** this is the RAG layer. It is for unstructured evidence; it does not perform investment arithmetic.

### 5. Enable the LLM agent

Copy `.env.example` to `.env`, add your API key and restart Streamlit.

Read `src/tools.py` before `src/agent.py`.

**Why:** tools are the trusted capabilities; the agent's job is to decide which capability is needed and explain the returned evidence.

## Three things to be able to explain tonight

1. Why the LLM is not allowed to calculate the investment portfolio itself.
2. Why one tool-calling agent is more appropriate here than a multi-agent architecture.
3. Why the EAM integration is a meaningful second iteration rather than a decorative API call.

Once you understand the individual components, read docs/technical_walkthrough.md for a more detailed explanation of the architecture, engineering decisions, assumptions and limitations.
