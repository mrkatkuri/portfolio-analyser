"""FIFO accounting in a consistent split-adjusted share basis."""
from collections import deque
import numpy as np
import pandas as pd


def analyse(tx, prices, splits, fx, info):
    tx = tx.copy()
    tx['adjusted_quantity'] = tx.quantity.astype(float)
    for i, row in tx.iterrows():
        events = splits.get(row.symbol, pd.Series(dtype=float))
        factor = events[(events.index > row.date) & (events > 0)].prod() if not events.empty else 1.
        tx.loc[i, 'adjusted_quantity'] *= factor
    tx['base_amount'] = [r.gross_amount * fx[r.currency].loc[r.date] for r in tx.itertuples()]
    lots, realised, bought, sold = {}, {}, {}, {}
    for row in tx.itertuples():
        symbol, q = row.symbol, row.adjusted_quantity
        lots.setdefault(symbol, deque())
        realised.setdefault(symbol, 0.)
        bought.setdefault(symbol, 0.)
        sold.setdefault(symbol, 0.)
        if row.transaction_type == 'BUY':
            lots[symbol].append([q, row.base_amount / q])
            bought[symbol] += row.base_amount
        else:
            available = sum(lot[0] for lot in lots[symbol])
            if q > available + 1e-8:
                raise ValueError(f'{symbol}: sale on {row.date.date()} exceeds available shares ({available:g} split-adjusted).')
            cost, remaining = 0., q
            while remaining > 1e-9 and lots[symbol]:
                lot = lots[symbol][0]
                take = min(remaining, lot[0])
                cost += take * lot[1]
                remaining -= take
                lot[0] -= take
                if lot[0] < 1e-9:
                    lots[symbol].popleft()
            realised[symbol] += row.base_amount - cost
            sold[symbol] += row.base_amount
    rows = []
    for symbol, queue in lots.items():
        record = tx[tx.symbol.eq(symbol)].iloc[-1]
        quantity = sum(l[0] for l in queue)
        cost = sum(l[0] * l[1] for l in queue)
        price = prices[symbol].iloc[-1]
        value = quantity * price * fx[record.currency].iloc[-1] if quantity > 1e-9 else 0.
        if quantity > 1e-9 and (not np.isfinite(value) or value <= 0):
            raise ValueError(f'{symbol}: latest price is missing or invalid.')
        meta = info.get(symbol, {})
        rows.append(dict(symbol=symbol, company=record.company_name, sector=record.sector if record.sector != 'Unknown' else meta.get('sector', 'Unknown'),
                         industry=meta.get('industry', 'Unknown'), country=meta.get('country', 'Unknown'),
                         currency=record.currency, shares=quantity, price=price, cost_basis=cost,
                         purchases=bought[symbol], proceeds=sold[symbol], value=value,
                         realised=realised[symbol], unrealised=value-cost))
    holdings = pd.DataFrame(rows)
    holdings['total_gain'] = holdings.realised + holdings.unrealised
    holdings['gain_on_purchases_pct'] = holdings.total_gain / holdings.purchases * 100
    total = holdings.value.sum()
    holdings['weight_pct'] = holdings.value / total * 100 if total else 0.
    index = prices.index[prices.index >= tx.date.min()]
    values = pd.DataFrame(index=index)
    for symbol in tx.symbol.unique():
        trades = tx[tx.symbol.eq(symbol)]
        changes = trades.adjusted_quantity.where(trades.transaction_type.eq('BUY'), -trades.adjusted_quantity)
        daily = pd.Series(changes.values, index=trades.date).groupby(level=0).sum().reindex(index, fill_value=0).cumsum()
        converted = prices[symbol].reindex(index) * fx[trades.currency.iloc[0]].reindex(index)
        if (converted.isna() & (daily > 1e-8)).any():
            raise ValueError(f'{symbol}: price history missing while shares were held.')
        values[symbol] = (daily * converted).where(daily.abs() > 1e-8, 0.)
    flows = tx.base_amount.where(tx.transaction_type.eq('BUY'), -tx.base_amount)
    flows = pd.Series(flows.values, index=tx.date).groupby(level=0).sum().reindex(index, fill_value=0.)
    value = values.sum(axis=1)
    previous = value.shift(1)
    # End-of-day net flow convention preserves gains before a sale/withdrawal.
    returns = ((value - flows) / previous - 1).where(previous > 1e-8)
    opening = previous.fillna(0).abs() < 1e-8
    returns = returns.mask(opening & (flows > 1e-8), value / flows - 1)
    returns = returns.mask(opening & (flows.abs() < 1e-8) & (value.abs() < 1e-8), 0.)
    if returns.isna().any() or (returns < -1 - 1e-8).any():
        raise ValueError('Daily flow-adjusted returns cannot be computed reliably from these trades.')
    curve = (1 + returns).cumprod()
    timeline = pd.DataFrame({'Holdings value': value, 'Net invested': flows.cumsum(), 'Return index': curve, 'Daily return': returns})
    return holdings, timeline, values, tx
