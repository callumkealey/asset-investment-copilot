from src.data_loader import load_portfolio
from src.validation import validate_portfolio


def test_clean_portfolio_is_valid():
    result = validate_portfolio(load_portfolio("clean"))
    assert result.valid is True
    assert result.errors == []


def test_dirty_portfolio_is_blocked():
    result = validate_portfolio(load_portfolio("dirty"))
    assert result.valid is False
    joined = " | ".join(result.errors)
    assert "Duplicate project_id" in joined
    assert "non-positive" in joined
    assert "outside the 1–10 range" in joined
