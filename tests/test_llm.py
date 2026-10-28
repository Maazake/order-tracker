import pytest

from app.llm import estimate_cost_usd


def test_estimate_cost_usd():
    assert estimate_cost_usd("claude-haiku-5-5", 121, 852) == pytest.approx(0.0004381)


def test_not_known_model_returns_none():
    assert estimate_cost_usd("mine-own-model", 121, 852) is None
