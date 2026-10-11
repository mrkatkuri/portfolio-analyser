"""Cached Yahoo Finance prices. Close is split-adjusted but not dividend-adjusted."""
import pandas as pd
import streamlit as st
import yfinance as yf


@st.cache_data(ttl=3600, show_spinner=False)
def history(symbol, start, end):
    frame = yf.Ticker(symbol).history(start=start, end=end, auto_adjust=False, actions=True, timeout=15)
    if frame.empty or 'Close' not in frame:
        raise ValueError(f'No historical prices for {symbol}. Check the ticker and exchange.')
    frame.index = pd.to_datetime(frame.index).tz_localize(None).normalize()
    return frame[~frame.index.duplicated(keep='last')]


@st.cache_data(ttl=86400, show_spinner=False)
def metadata(symbol):
    try:
        return yf.Ticker(symbol).get_info()
    except Exception:
        return {}


def fx_series(currency, base, index):
    if currency == base:
        return pd.Series(1., index=index)
    frame = history(f'{currency}{base}=X', (index.min() - pd.Timedelta(days=10)).strftime('%Y-%m-%d'),
                    (index.max() + pd.Timedelta(days=1)).strftime('%Y-%m-%d'))
    result = frame.Close.reindex(frame.index.union(index)).sort_index().ffill().reindex(index)
    if result.isna().any() or (result <= 0).any():
        raise ValueError(f'Missing exchange rates for {currency}/{base}.')
    return result


def load_market(tx, base):
    start = tx.date.min() - pd.Timedelta(days=10)
    end = pd.Timestamp.now(tz='Europe/London').tz_localize(None).normalize() + pd.Timedelta(days=1)
    frames, info, warnings = {}, {}, []
    for symbol in tx.symbol.unique():
        frames[symbol] = history(symbol, start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d'))
        info[symbol] = metadata(symbol)
        if not info[symbol]:
            warnings.append(f'{symbol}: company metadata unavailable; unknown categories are shown.')
    # A shared as-of date avoids combining current and stale asset valuations.
    asof = min(f.Close.dropna().index.max() for f in frames.values())
    if asof < tx.date.max():
        raise ValueError('Some transactions are newer than the common available market-data date. Retry after prices update.')
    if (end - pd.Timedelta(days=1) - asof).days > 5:
        warnings.append(f'Market data is stale: common valuation date is {asof.date()}.')
    index = pd.date_range(start, asof, freq='D')
    prices, splits = {}, {}
    for symbol, f in frames.items():
        currency = tx.loc[tx.symbol.eq(symbol), 'currency'].iloc[0]
        quoted = info[symbol].get('currency')
        if not quoted:
            raise ValueError(f'{symbol}: quote currency unavailable; retry before valuing this stock.')
        scale = .01 if quoted in {'GBp', 'GBX'} else 1.
        actual = 'GBP' if scale == .01 else quoted.upper()
        if actual != currency:
            raise ValueError(f'{symbol}: transactions use {currency}, but Yahoo quotes {quoted}. Correct the file.')
        prices[symbol] = f.Close.reindex(index).ffill() * scale
        splits[symbol] = f.get('Stock Splits', pd.Series(dtype=float))
    fx = {c: fx_series(c, base, index) for c in tx.currency.unique()}
    return pd.DataFrame(prices), splits, fx, info, warnings
