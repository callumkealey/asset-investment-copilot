"""Ensure the restricted Copilot access logic remains syntactically valid and gated."""
from pathlib import Path

def test_app_compiles():
    source = Path("app.py").read_text(encoding="utf-8")
    compile(source, "app.py", "exec")

def test_hosted_ai_access_gate_is_present():
    source = Path("app.py").read_text(encoding="utf-8")
    assert 'hmac.compare_digest(password, AI_DEMO_PASSWORD)' in source
    assert 'not HOSTED_DEMO or st.session_state.get("ai_demo_requests", 0) < AI_DEMO_SESSION_LIMIT' in source
    assert 'counter["count"] >= AI_DEMO_GLOBAL_LIMIT' in source
