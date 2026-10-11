import numpy as np


def metrics(timeline, holdings):
    # Calendar alignment is used for valuations; risk uses weekday observations.
    curve = timeline['Return index'][timeline.index.dayofweek < 5]
    returns = curve.pct_change().dropna()
    drawdown = curve / curve.cummax() - 1
    weights = holdings.weight_pct / 100
    hhi = (weights ** 2).sum()
    return {'volatility': returns.std(ddof=1) * np.sqrt(252) if len(returns) > 1 else np.nan,
            'max_drawdown': drawdown.min(), 'effective_holdings': 1 / hhi if hhi > 0 else 0,
            'top_five': weights.nlargest(5).sum(), 'drawdown': drawdown}
