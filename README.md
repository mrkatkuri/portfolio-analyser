# Stock Portfolio Analyser

A Python/Streamlit dashboard for transaction-based portfolios, with Pandas,
Plotly and yfinance. Upload CSV, XLS or XLSX files, choose an Excel worksheet,
or load the included 48-trade sample.

## Run

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```bash
uv sync
uv run streamlit run app.py
```

Internet access is required for Yahoo Finance prices, currency rates and company
metadata. Uploaded trades are processed in memory; ticker symbols are sent to
Yahoo Finance to request market data. The app does not save uploaded files.

## Input

See `data/sample_stock_transactions.csv`. Required columns:

```csv
date,ticker,exchange,transaction_type,quantity,price,currency,gross_amount
2025-01-15,AAPL,NASDAQ,BUY,10,190,USD,1900
```

Optional columns: `S.NO`, `company_name`, `sector`. Dates should use YYYY-MM-DD.
Transactions must have positive quantities, prices and gross amounts; gross amount
must equal quantity × price within rounding tolerance. Enter BUY or SELL. Rows
are sorted by date, preserving input order within a day. Each symbol must have a
single transaction currency. LSE ticker suffixes and US class-share symbols are
normalised automatically. Use explicit Yahoo symbols for other exchanges.
UK transaction prices must be in GBP, not pence. Yahoo GBp/GBX quotes are converted
to GBP. Future dates, overselling, invalid amounts and missing prices block analysis.

## Dashboard

- Overview: purchases, proceeds, remaining FIFO cost basis, valuation, realised
  and unrealised gains, and downloadable holdings.
- Allocation: stocks, sectors, industries and company domicile countries.
- Performance: historical holdings value, net investment, daily flow-adjusted
  returns and CSV export.
- Stocks: gain rankings, holding details and price trends.
- Risk: annualised volatility, drawdowns, effective holdings, top-five concentration
  and stock correlations.
- Benchmarks: S&P 500, FTSE 100 or custom Yahoo ticker in the selected base currency.
- Insights: configurable concentration alerts, loss observations and editable
  target weights showing value changes needed for rebalancing.

## Calculation assumptions

FIFO lots are maintained in the base currency, with trade-date FX applied to cost
and proceeds and valuation-date FX applied to current value. The FX portion of
gains is therefore included. Prices and shares use Yahoo's split-adjusted basis;
recorded trade amounts remain unchanged. Share quantities shown are on the latest
split basis returned by Yahoo. Latest valuation uses the common available date
across stocks; intervening non-trading days carry the last available close forward.
Prices cache for one hour and metadata for one day; use Refresh market data to retry.
Missing company categories appear as Unknown; an unknown quote currency blocks
valuation rather than guessing. Stale data generates a warning.

No fees, dividends, dividend reinvestment, taxes, cash balances, deposits or
withdrawals are modelled. Purchases count as contributions and sales as withdrawals.
The daily return is `(closing value - net purchases) / previous closing value - 1`,
assuming end-of-day flows. This is an approximation on trade days, not a full
brokerage account return. The first investment day uses closing value divided by the net contribution; periods
without capital have a zero return. Invalid return calculations block analysis. Gain divided by cumulative
purchases is labelled separately and is not a time-weighted return.

Benchmark comparisons use price returns, matched dates, FX conversion and a common
starting index. Custom benchmark currency must match its quote units; use benchmarks
quoted in whole currency units. Risk uses weekday observations and 252-day
annualisation; holidays, stale prices and short histories can affect estimates.
Correlation requires at least 20 overlapping observations. Country is company
domicile, not revenue exposure. Target weights start equal-weighted for exploration;
rebalancing estimates exclude trading costs and taxes.

## Tests

```bash
uv run pytest
```

Tests cover FIFO partial sales, split handling, FX, overselling, missing prices,
flow adjustment, validation and all three upload formats. Market requests are not
needed for the accounting tests.
