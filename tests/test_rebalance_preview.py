"""Initial examples for the experimental rebalance preview helpers."""

import pickle

import pytest

from src.rebalance_preview import (
    aggregate_position_values,
    build_rebalance_preview,
    load_target_weights,
    top_holdings,
)


def test_load_target_weights_normalizes_symbols():
    payload = pickle.dumps({" aapl ": 60, "msft": 40})
    assert load_target_weights(payload) == {"AAPL": 60.0, "MSFT": 40.0}


def test_rebalance_preview_increases_underweight_position():
    preview = build_rebalance_preview(
        {"AAPL": 400.0, "MSFT": 600.0}, {"AAPL": 60.0, "MSFT": 40.0}
    )
    apple = next(row for row in preview if row["symbol"] == "AAPL")
    assert apple["target_value"] == pytest.approx(600.0)
    assert apple["value_change"] == pytest.approx(200.0)


def test_rebalance_preview_keeps_balanced_positions_unchanged():
    preview = build_rebalance_preview(
        {"AAPL": 600.0, "MSFT": 400.0}, {"AAPL": 60.0, "MSFT": 40.0}
    )
    assert all(row["value_change"] == 0.0 for row in preview)


def test_aggregate_position_values_with_unique_symbols():
    values = aggregate_position_values([
        {"symbol": " aapl ", "value": 250.0},
        {"symbol": "msft", "value": 750.0},
    ])
    assert values == {"AAPL": 250.0, "MSFT": 750.0}


def test_top_holdings_with_one_position():
    assert top_holdings({"AAPL": 100.0}, limit=1) == ["AAPL"]


def test_top_holdings_limits_result_count():
    result = top_holdings({"AAPL": 800.0, "MSFT": 150.0, "GOOG": 50.0}, limit=2)
    assert len(result) == 2
