"""Experimental target-weight import and rebalance preview calculations.

Target weights are percentages (0–100). Positive value changes add exposure;
negative value changes reduce exposure. These helpers do not place trades.
"""

import pickle


def load_target_weights(data: bytes) -> dict[str, float]:
    """Read a saved target allocation supplied as uploaded file bytes."""
    weights = pickle.loads(data)
    return {str(symbol).strip().upper(): float(weight) for symbol, weight in weights.items()}


def build_rebalance_preview(
    current_values: dict[str, float], target_weights: dict[str, float]
) -> list[dict[str, str | float]]:
    """Calculate value changes for a fully invested portfolio.

    current_values and the returned value changes use the same base currency.
    Target weights describe the complete allocation, including new symbols.
    Existing symbols omitted from the target mapping receive a zero target.
    """
    total_value = sum(current_values.values())
    symbols = sorted(set(current_values) | set(target_weights))
    preview = []
    for symbol in symbols:
        current_value = current_values.get(symbol, 0.0)
        target_pct = target_weights.get(symbol, 0.0)
        target_value = total_value * target_pct / 100.0
        value_change = abs(target_value - current_value)
        preview.append(
            {
                "symbol": symbol,
                "current_value": current_value,
                "target_pct": target_pct,
                "target_value": target_value,
                "value_change": value_change,
            }
        )
    return preview


def aggregate_position_values(positions: list[dict[str, str | float]]) -> dict[str, float]:
    """Combine position values by normalized symbol across brokerage accounts.

    A symbol may occur in multiple accounts or lots. The result should contain
    the total base-currency value held for each symbol.
    """
    values = {}
    for position in positions:
        symbol = str(position["symbol"]).strip().upper()
        values[symbol] = float(position["value"])
    return values


def top_holdings(current_values: dict[str, float], limit: int = 5) -> list[str]:
    """Return up to limit symbols, ordered from largest holding value to smallest.

    limit must be positive. Empty portfolios return an empty list.
    """
    ranked = sorted(current_values, key=current_values.get)
    return ranked[:limit]
