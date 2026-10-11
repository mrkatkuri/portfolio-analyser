from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from src.data_loader import read_file, sheets, validate
from src.market_data import load_market, history, fx_series
from src.portfolio import analyse
from src.risk import metrics
from src.insights import observations

st.set_page_config(page_title='Portfolio Analyser', page_icon='📈', layout='wide')
st.title('Stock Portfolio Analyser')
st.caption('Understand your holdings, performance and exposure in one place.')
SAMPLE = Path(__file__).parent / 'data/sample_stock_transactions.csv'
with st.sidebar:
    st.header('Your portfolio')
    upload = st.file_uploader('Upload transactions', type=['csv', 'xls', 'xlsx'])
    sample = st.checkbox('Load sample portfolio', value=False)
    base = st.selectbox('Base currency', ['GBP', 'USD', 'EUR'])
    benchmark_name = st.selectbox('Benchmark', ['S&P 500', 'FTSE 100', 'Custom'])
    benchmark = {'S&P 500': '^GSPC', 'FTSE 100': '^FTSE'}.get(benchmark_name)
    benchmark_currency = 'USD' if benchmark_name == 'S&P 500' else 'GBP'
    if benchmark_name == 'Custom':
        benchmark = st.text_input('Yahoo Finance benchmark ticker', '^GSPC').strip()
        benchmark_currency = st.selectbox('Benchmark quote currency', ['USD', 'GBP', 'EUR'])
    threshold = st.slider('Single-stock concentration limit (%)', 5, 60, 20)
    if st.button('Refresh market data'):
        st.cache_data.clear()
    st.download_button('Download sample CSV', SAMPLE.read_bytes(), 'sample_stock_transactions.csv', 'text/csv')
    st.caption('Prices refresh hourly; company information daily.')

with st.expander('File format and calculation assumptions'):
    st.write('Required columns: date, ticker, exchange, transaction_type, quantity, price, currency, gross_amount. Optional: company_name, sector, S.NO. Use YYYY-MM-DD dates and positive amounts. BUY and SELL are supported; each row is a trade. UK trade prices must be in GBP, not pence.')
    st.write('FIFO cost accounting. No fees, dividends, taxes, short sales or idle cash. Purchases are contributions and sales are withdrawals. Returns assume net flows occur at the end of each day; execution timing can affect trade-day returns. These are invested-portfolio price returns, not full brokerage-account returns. Company country means domicile.')
    st.write('Historical Yahoo Close prices and share quantities are put on a consistent split-adjusted basis. Shares shown may therefore be split-adjusted. Risk uses weekday closes and a 252-day annualisation; holidays can slightly affect estimates.')
if upload is None and not sample:
    st.info('Upload a CSV or Excel workbook, or select “Load sample portfolio” to begin.')
    st.dataframe(pd.read_csv(SAMPLE).head(), hide_index=True, width='stretch')
    st.stop()
try:
    if upload is not None:
        data, name = upload.getvalue(), upload.name
        sheet = st.selectbox('Transaction worksheet', sheets(data, name)) if name.lower().endswith(('.xls', '.xlsx')) else 0
        raw = read_file(data, name, sheet)
    else:
        raw = read_file(SAMPLE.read_bytes(), SAMPLE.name)
    tx = validate(raw)
except Exception as exc:
    st.error(f'Unable to import transactions: {exc}')
    st.stop()
with st.expander(f'Imported transactions · {len(tx)} trades · {tx.symbol.nunique()} stocks'):
    st.dataframe(tx, hide_index=True, width='stretch')
try:
    with st.spinner('Loading prices, exchange rates and company information…'):
        prices, splits, fx, info, warnings = load_market(tx, base)
        holdings, timeline, values, adjusted = analyse(tx, prices, splits, fx, info)
except Exception as exc:
    st.error(f'Analysis unavailable: {exc}')
    st.info('Check the file and your network connection, then refresh market data. Missing prices are never replaced with zero.')
    st.stop()
for warning in warnings:
    st.warning(warning)
st.caption(f'Valuation date: {timeline.index[-1].date()} · All monetary totals in {base} · Latest available daily closes')
tabs = st.tabs(['Overview', 'Allocation', 'Performance', 'Stocks', 'Risk', 'Benchmarks', 'Insights'])

def chart(fig):
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), legend_title_text='')
    st.plotly_chart(fig, width='stretch')

with tabs[0]:
    cols = st.columns(4)
    for col, label, val in zip(cols, ['Total purchase cost', 'Current valuation', 'Realised P/L', 'Unrealised P/L'],
                               [holdings.purchases.sum(), holdings.value.sum(), holdings.realised.sum(), holdings.unrealised.sum()]):
        col.metric(label, f'{base} {val:,.2f}')
    cols = st.columns(3)
    cols[0].metric('Sale proceeds', f'{base} {holdings.proceeds.sum():,.2f}')
    cols[1].metric('Remaining cost basis', f'{base} {holdings.cost_basis.sum():,.2f}')
    cols[2].metric('Flow-adjusted return', f'{(timeline["Return index"].iloc[-1]-1)*100:.2f}%')
    st.dataframe(holdings.round(3), hide_index=True, width='stretch')
    st.download_button('Export holdings CSV', holdings.to_csv(index=False), 'portfolio_holdings.csv', 'text/csv')
with tabs[1]:
    active = holdings[holdings.value > 0]
    if active.empty:
        st.info('No open holdings to allocate.')
    else:
        dimension = st.selectbox('Group allocation by', ['symbol', 'sector', 'industry', 'country'])
        allocation = active.groupby(dimension, as_index=False).value.sum()
        chart(px.pie(allocation, names=dimension, values='value', hole=.55, title=f'Allocation by {dimension}'))
        st.dataframe(allocation, hide_index=True, width='stretch')
with tabs[2]:
    dates = st.date_input('Performance date range', (timeline.index[0].date(), timeline.index[-1].date()),
                          min_value=timeline.index[0].date(), max_value=timeline.index[-1].date())
    if isinstance(dates, (tuple, list)) and len(dates) == 2:
        selected = timeline.loc[str(dates[0]):str(dates[1])]
        chart(px.line(selected, y=['Holdings value', 'Net invested'], labels={'value': base}))
        chart(px.line(selected, y='Return index', title='Flow-adjusted return index · inception = 1'))
    st.download_button('Export daily performance', timeline.to_csv(), 'portfolio_performance.csv', 'text/csv')
with tabs[3]:
    ranking = st.selectbox('Rank stocks by', ['total_gain', 'gain_on_purchases_pct', 'unrealised', 'realised'])
    chart(px.bar(holdings.sort_values(ranking), x='symbol', y=ranking, color=ranking, color_continuous_scale='Tealrose'))
    st.caption('Gain on purchases is total realised + unrealised gain divided by cumulative purchase cost; it is not a time-weighted return.')
    symbol = st.selectbox('Stock', holdings.symbol.tolist())
    st.dataframe(holdings[holdings.symbol.eq(symbol)].round(3), hide_index=True, width='stretch')
    currency = tx.loc[tx.symbol.eq(symbol), 'currency'].iloc[0]
    stock_prices = prices[symbol].loc[timeline.index].dropna()
    chart(px.line(stock_prices, title=f'{symbol} · split-adjusted close ({currency})', labels={'value': currency}))
    if not stock_prices.empty:
        st.metric('Stock price return over displayed history', f'{(stock_prices.iloc[-1]/stock_prices.iloc[0]-1)*100:.2f}%')
with tabs[4]:
    risk = metrics(timeline, holdings)
    cols = st.columns(4)
    cols[0].metric('Annualised volatility', f'{risk["volatility"]*100:.2f}%')
    cols[1].metric('Maximum drawdown', f'{risk["max_drawdown"]*100:.2f}%')
    cols[2].metric('Effective holdings', f'{risk["effective_holdings"]:.1f}')
    cols[3].metric('Top-five concentration', f'{risk["top_five"]*100:.1f}%')
    chart(px.area(risk['drawdown'] * 100, title='Flow-adjusted drawdown (%)'))
    st.caption('Effective holdings = 1 / sum of squared value weights. Equal weights increase this measure. Estimates need sufficient history.')
    converted = pd.DataFrame({s: prices[s] * fx[tx.loc[tx.symbol.eq(s), 'currency'].iloc[0]] for s in prices})
    returns = converted.loc[timeline.index]
    returns = returns[returns.index.dayofweek < 5].pct_change(fill_method=None)
    corr = returns.corr(min_periods=20)
    if corr.notna().any().any():
        chart(px.imshow(corr, zmin=-1, zmax=1, color_continuous_scale='RdBu_r', title='Stock return correlations · base currency'))
    else:
        st.info('At least 20 overlapping return observations are needed for correlations.')
with tabs[5]:
    try:
        with st.spinner('Loading benchmark…'):
            bench = history(benchmark, (timeline.index[0]-pd.Timedelta(days=10)).strftime('%Y-%m-%d'),
                            (timeline.index[-1]+pd.Timedelta(days=1)).strftime('%Y-%m-%d')).Close
            bench = bench.reindex(bench.index.union(timeline.index)).sort_index().ffill().reindex(timeline.index)
            bench *= fx_series(benchmark_currency, base, timeline.index)
            comparison = pd.DataFrame({'Portfolio': timeline['Return index'], benchmark: bench}).dropna()
            if len(comparison) < 2:
                raise ValueError('Not enough overlapping benchmark data.')
            comparison = (comparison / comparison.iloc[0] - 1) * 100
        chart(px.line(comparison, title=f'Price returns in {base} · aligned start = 0%', labels={'value': 'Return (%)'}))
        st.dataframe(comparison.tail(1).T.rename(columns={comparison.index[-1]: 'Return (%)'}).round(2), width='stretch')
        st.caption('Benchmarks exclude dividends. Portfolio curve is rebased to the same start date; foreign benchmark returns include FX changes.')
        stock_comparison = []
        for stock in holdings.symbol:
            currency = tx.loc[tx.symbol.eq(stock), 'currency'].iloc[0]
            series = (prices[stock] * fx[currency]).reindex(comparison.index).dropna()
            if len(series) >= 2 and series.index[0] == comparison.index[0]:
                price_return = (series.iloc[-1] / series.iloc[0] - 1) * 100
                stock_comparison.append({'Stock': stock, 'Price return (%)': price_return,
                                         'Excess vs benchmark (pp)': price_return - comparison[benchmark].iloc[-1]})
        if stock_comparison:
            st.subheader('Stock returns against the benchmark')
            st.dataframe(pd.DataFrame(stock_comparison).sort_values('Excess vs benchmark (pp)').round(2), hide_index=True, width='stretch')
            st.caption('Negative excess identifies underperformance over the matched period. Stock returns exclude your transaction timing.')

    except Exception as exc:
        st.warning(f'Benchmark comparison unavailable: {exc}')
with tabs[6]:
    for message in observations(holdings, threshold):
        st.write('• ' + message)
    st.subheader('Explore target weights')
    active = holdings[holdings.value > 0][['symbol', 'weight_pct']].copy()
    if not active.empty:
        active['target_pct'] = 100 / len(active)
        targets = st.data_editor(active, disabled=['symbol', 'weight_pct'], hide_index=True,
                                 column_config={'target_pct': st.column_config.NumberColumn('Target (%)', min_value=0., max_value=100.)})
        if targets.target_pct.isna().any() or abs(targets.target_pct.sum()-100) > .01:
            st.warning('Target weights must total 100%.')
        else:
            targets['value_change'] = (targets.target_pct-targets.weight_pct)/100 * holdings.value.sum()
            st.dataframe(targets.round(2), hide_index=True, width='stretch')
            st.caption(f'Positive value change means add exposure; negative means reduce exposure ({base}). Targets start equal-weighted for exploration. Costs and taxes are excluded.')
