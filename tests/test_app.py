import pandas as pd
from streamlit.testing.v1 import AppTest
import src.market_data as market


def test_dashboard_with_sample_and_controlled_market(monkeypatch):
    def fake_market(tx, base):
        index = pd.date_range(tx.date.min()-pd.Timedelta(days=10), '2025-09-19')
        prices = pd.DataFrame({s: 100. for s in tx.symbol.unique()}, index=index)
        fx = {c: pd.Series(1., index=index) for c in tx.currency.unique()}
        return prices, {}, fx, {}, []
    def fake_history(symbol, start, end):
        return pd.DataFrame({'Close': 100.}, index=pd.date_range(start, pd.Timestamp(end)-pd.Timedelta(days=1)))
    monkeypatch.setattr(market, 'load_market', fake_market)
    monkeypatch.setattr(market, 'history', fake_history)
    monkeypatch.setattr(market, 'fx_series', lambda c, b, i: pd.Series(1., index=i))
    app = AppTest.from_file('../app.py').run(timeout=30)
    assert not app.exception
    app.sidebar.checkbox[0].check().run(timeout=30)
    assert not app.exception
    assert not app.error
    assert len(app.tabs) == 7
    assert len(app.metric) >= 12
