# Stock Portfolio Analyser

An interactive Python application that turns stock transaction files into a
portfolio dashboard. Analyse holdings, profit and loss, allocation, historical
performance, risk and benchmark returns using Streamlit, Pandas, Plotly and
Yahoo Finance data.

## Contents

- [Features](#features)
- [Installation and startup](#installation-and-startup)
- [Using the application](#using-the-application)
- [Upload format](#upload-format)
- [Calculation methods](#calculation-methods)
- [Market data and caching](#market-data-and-caching)
- [Project structure](#project-structure)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Scope and limitations](#scope-and-limitations)

## Features

### Portfolio overview

View cumulative purchase cost, current holdings valuation, sale proceeds,
remaining cost basis, realised profit/loss, unrealised profit/loss and the
flow-adjusted portfolio return. The holdings table includes company information,
share quantities, prices, currency, valuation, gains and portfolio weights.
Download the table as `portfolio_holdings.csv`.

### Investment distribution

Explore interactive donut charts and allocation tables grouped by stock,
sector, industry or country. Allocation uses the current value of open holdings.
Country means company domicile, rather than geographic revenue exposure.
Unavailable company categories appear as `Unknown`.

### Portfolio performance

Track historical holdings value alongside cumulative net investment. View the
flow-adjusted return index, starting at inception, and filter the displayed date
range. The date filter crops the charts; it does not rebase the return index.
Export the complete daily history as `portfolio_performance.csv`.

### Individual stock analysis

Rank stocks by total gain, gain on cumulative purchases, unrealised gain or
realised gain. Select a stock to inspect its holding details, split-adjusted
price trend and price return over the displayed history. Rankings include stocks
that have been fully sold.

### Risk analysis

Review annualised volatility, maximum drawdown, effective number of holdings and
top-five concentration. Inspect a drawdown chart and a correlation heatmap of
stock price returns in the base currency. Correlations require at least 20
overlapping observations.

### Benchmark comparison

Compare the portfolio with the S&P 500 (`^GSPC`), FTSE 100 (`^FTSE`) or a custom
Yahoo Finance ticker. Comparisons use aligned dates, base-currency conversion
and a shared starting value. A stock comparison table identifies underperformance
through negative excess returns, measured in percentage points.

For a custom benchmark, select its quote currency correctly. The interface offers
USD, GBP and EUR and expects quotes in whole currency units.

### Portfolio insights and target weights

- Flag stock weights above a configurable limit of 5–60% (default: 20%).
- Highlight sectors exceeding 40% of portfolio value.
- Identify stocks with negative total realised plus unrealised gains.
- Edit target weights for open holdings and calculate the required change in
  exposure in the base currency.

Target weights start equal-weighted for exploration and must total 100% within
rounding tolerance. Positive value changes mean adding exposure; negative changes
mean reducing exposure. The application calculates amounts; it does not place trades.

### File and currency support

Upload CSV, XLS or XLSX transactions. For Excel workbooks, choose the worksheet
containing the transaction table. Load or download the included sample portfolio
of 48 transactions across 16 stocks. Select GBP, USD or EUR as the reporting
currency. Transaction currencies require available Yahoo exchange-rate data.

## Installation and startup

Requirements:

- Python 3.11 or newer.
- [uv](https://docs.astral.sh/uv/) for environment and dependency management.
- Internet access to retrieve market prices, exchange rates and company metadata.

From the repository directory:

```bash
uv sync
uv run streamlit run app.py
```

Open the local URL printed by Streamlit, normally `http://localhost:8501`.
Stop the application with `Ctrl+C` in the terminal.

`pyproject.toml` declares dependencies and `uv.lock` records resolved versions.
`uv sync` creates the local `.venv` environment.

## Using the application

1. Start the app and upload a transaction file, or enable **Load sample portfolio**.
2. For an Excel upload, select the transaction worksheet. An uploaded file takes
   precedence over the sample checkbox.
3. Choose the base currency, benchmark and concentration limit in the sidebar.
4. Expand **Imported transactions** to review the validated records.
5. Check the valuation date and any market-data warnings above the dashboard.
6. Explore the seven dashboard tabs and download holdings or performance data.
7. Use **Refresh market data** to clear cached market data and retry requests.

## Upload format

Each row represents one BUY or SELL transaction, rather than an aggregate holding.
Use the first row for column headings and one transaction per subsequent row.
A complete example is in [data/sample_stock_transactions.csv](data/sample_stock_transactions.csv).

```csv
date,ticker,exchange,transaction_type,quantity,price,currency,gross_amount
2025-01-15,AAPL,NASDAQ,BUY,10,190,USD,1900
2025-04-15,AAPL,NASDAQ,SELL,2,200,USD,400
```

### Required columns

| Column | Meaning | Example |
| --- | --- | --- |
| `date` | Trade date; use YYYY-MM-DD | `2025-01-15` |
| `ticker` | Stock ticker | `AAPL` |
| `exchange` | Exchange used for ticker mapping | `NASDAQ` |
| `transaction_type` | BUY or SELL | `BUY` |
| `quantity` | Positive number of shares | `10` |
| `price` | Positive price per share in the transaction currency | `190` |
| `currency` | Three-letter transaction currency code | `USD` |
| `gross_amount` | Positive quantity × price, excluding fees | `1900` |

### Optional columns

| Column | Use |
| --- | --- |
| `company_name` | Company label; defaults to `Unknown` when absent |
| `sector` | Sector label; Yahoo metadata is used when this is `Unknown` |
| `S.NO` | Source row identifier; retained in the imported table |

Additional columns are retained but are not used in accounting. Column headings
are stripped of surrounding spaces and converted to lowercase. Tickers,
exchanges, transaction types and currencies are normalised to uppercase.

### Validation and ticker mapping

- Required fields cannot be missing; completely blank rows are ignored.
- Dates must be valid and cannot be in the future.
- Quantities, prices and gross amounts must be finite positive numbers.
- Gross amounts must agree with quantity × price within rounding tolerance
  (absolute tolerance 0.02 plus a small relative tolerance).
- Each normalised stock symbol must have one transaction currency.
- Transactions are sorted by date, preserving input order within each day.
- FIFO processing rejects sales exceeding available split-adjusted shares.
- Duplicate column headings are rejected after normalisation. Duplicate trade
  rows are not automatically removed; check the source for repeated transactions.

LSE/LONDON tickers gain a `.L` suffix, for example `AZN` → `AZN.L` and `BA.` →
`BA.L`. US class-share dots become hyphens, for example NYSE `BRK.B` → `BRK-B`.
For other exchanges, provide the explicit Yahoo Finance symbol.

Enter UK transaction prices in **GBP pounds**, not pence. Yahoo quotes labelled
`GBp` or `GBX` are divided by 100 before valuation. The market quote currency
must match the transaction currency after this conversion.

## Calculation methods

### FIFO accounting

Sales consume the oldest available purchase lots first. Cost basis is maintained
in the selected base currency.

```text
Trade value in base currency = gross amount × trade-date FX rate
Current holding value = remaining adjusted shares × latest close × valuation-date FX
Realised P/L = sale proceeds − FIFO cost of shares sold
Unrealised P/L = current holding value − remaining FIFO cost basis
Total gain = realised P/L + unrealised P/L
Gain on purchases (%) = total gain / cumulative purchase cost × 100
Portfolio weight (%) = holding value / total holdings value × 100
```

Gain on purchases is a simple accounting ratio, not a time-weighted return.
Historical FX affects purchase cost and proceeds, while current FX affects
valuation, so currency movements contribute to reported gains.

### Splits and daily valuation

Yahoo Close prices are split-adjusted and are requested without dividend
adjustment. Trade quantities are converted to the corresponding latest split
basis using subsequent split events; recorded gross amounts remain unchanged.
Displayed share counts therefore use this split-adjusted basis.

Daily quantities are reconstructed from signed BUY/SELL quantities. Prices and
FX rates carry forward over dates without a quote; unavailable prices while a
stock is held block analysis. Portfolio history starts at the first trade.

### Flow-adjusted returns

Purchases are contributions to the invested portfolio; sales are withdrawals.
The daily calculation assumes flows occur at the end of the day:

```text
Net flow = purchase amounts − sale amounts
Daily return = (closing holdings value − net flow) / previous closing value − 1
Return index = cumulative product of (1 + daily return)
```

On the first investment day, return is closing value / net contribution − 1.
Periods without capital have zero return. Invalid calculations block analysis.
The Overview return is the final return index minus one.

This method approximates trade-day performance because intraday transaction
prices and timing can differ from closing prices. It measures the invested
portfolio, excluding idle cash and external account movements.

### Risk measures

| Measure | Method |
| --- | --- |
| Annualised volatility | Sample standard deviation of weekday index returns × √252 |
| Drawdown | Return index / running peak − 1 |
| Maximum drawdown | Lowest observed drawdown |
| Effective holdings | 1 / sum of squared current portfolio weights |
| Top-five concentration | Sum of the five largest current value weights |
| Stock correlation | Correlation of weekday stock price returns converted to base currency |

Fewer than two return observations produce an unavailable volatility estimate.
Risk calculations use weekdays, rather than individual exchange calendars;
holidays and stale prices can affect estimates. Effective holdings measures
weight concentration and does not account for correlations.

### Benchmark returns

Benchmark prices are converted into the base currency and aligned with the
portfolio history. Both series are rebased to zero percent on the first shared
date. Rebased benchmark and stock returns exclude dividends. The stock comparison
uses price returns over the matched period, independently of trade timing.

### Target-weight amounts

```text
Value change = (target weight − current weight) × total current holdings value
```

The editor covers existing open holdings and assumes a fully invested portfolio.
It does not add new stocks, reserve cash or calculate share quantities to trade.

## Market data and caching

Market data comes from Yahoo Finance through `yfinance`. No API key is configured.
Historical prices and FX requests cache for one hour; company metadata caches for
one day. Refresh clears Streamlit data caches, which may affect other sessions
on a shared server.

The common valuation date is the earliest last available close among imported
stocks. Transactions newer than this date block analysis. A common date more than
five calendar days old generates a warning. Closed positions are still included
in market-data retrieval and common-date selection.

Missing categories appear as `Unknown`. Missing quote currencies, mismatched
currencies, unavailable prices and missing FX rates block valuation instead of
silently treating a holding as worthless. A failed benchmark request displays a
warning while the other portfolio sections remain available.

Uploaded transaction files are processed in memory and are not saved by the app.
Stock/benchmark tickers and FX pair symbols are sent to Yahoo Finance for data
requests. Market responses are cached by Streamlit and yfinance may maintain its
own local connection caches. Downloads are created only when requested by the user.

## Project structure

```text
portfolio-analyser/
├── app.py                         # Streamlit interface and dashboard charts
├── src/
│   ├── __init__.py
│   ├── data_loader.py             # CSV/Excel readers, worksheet discovery, validation
│   ├── market_data.py             # Yahoo history, metadata, FX and caching
│   ├── portfolio.py               # FIFO lots, valuation and daily performance
│   ├── risk.py                    # Volatility, drawdowns and concentration metrics
│   └── insights.py                # Concentration and loss observations
├── data/
│   └── sample_stock_transactions.csv
├── tests/
│   ├── test_portfolio.py           # Accounting, validation and file-format tests
│   └── test_app.py                 # Dashboard test with controlled market data
├── .streamlit/config.toml          # Theme settings
├── .gitignore
├── pyproject.toml                 # Dependencies and test configuration
├── uv.lock                        # Resolved dependency versions
└── README.md
```

### Technology stack

| Technology | Role |
| --- | --- |
| Python | Application and calculations |
| Streamlit | Uploads, controls, tables and dashboard layout |
| Pandas / NumPy | Tabular data, time series and numerical calculations |
| Plotly | Interactive charts |
| yfinance | Yahoo Finance market data |
| xlrd / openpyxl | XLS / XLSX parsing |
| uv | Dependency and environment management |
| pytest / Streamlit AppTest | Calculation and dashboard verification |
| xlwt | Legacy XLS fixture generation in tests only |

## Testing

```bash
uv run pytest
```

The eight automated tests cover FIFO partial sales and reconciliation,
overselling, split handling, FX conversion, missing prices, flow adjustment,
CSV/XLS/XLSX imports, sample ticker mapping, invalid amounts, future dates and
sample dashboard rendering across all seven tabs.

Tests use controlled data and do not need market requests. Successful tests do
not guarantee Yahoo availability or the correctness of third-party market data.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| Missing columns | Match the required headings and select the correct Excel worksheet. |
| Invalid amounts | Use numeric cells and positive values; check quantity × price. |
| Future or invalid date | Use YYYY-MM-DD and remove future transactions. |
| Sale exceeds holdings | Include earlier purchases and check same-day row order and split quantities. |
| No history for a ticker | Verify the exchange and Yahoo Finance symbol; check the network and refresh. |
| Quote currency mismatch | Correct the transaction currency or ticker; enter UK trade prices in GBP. |
| Quote currency unavailable | Retry metadata retrieval with Refresh market data. |
| Transaction newer than market data | Wait for updated closes or correct the transaction date. |
| Benchmark unavailable | Check the benchmark ticker, quote currency and overlapping history. |
| Correlation unavailable | Supply enough history for 20 overlapping weekday return observations. |
| Target-weight warning | Ensure every target is present and the total is 100%. |

## Scope and limitations

The app supports long-only BUY/SELL stock transactions and price-based analysis.
It does not model fees, taxes, dividends, dividend reinvestment, idle cash,
external deposits/withdrawals, short sales or other corporate actions beyond
splits. It does not provide a full brokerage-account return or total-return
benchmark comparison.

There is no account login, database, saved-portfolio system or order execution.
Rebalancing outputs are calculations based on entered targets. Daily prices,
metadata and FX depend on Yahoo availability, quote conventions and data quality.
