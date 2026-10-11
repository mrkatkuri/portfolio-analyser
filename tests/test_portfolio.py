from io import BytesIO
from pathlib import Path
import pandas as pd
import pytest
import xlwt
from src.data_loader import read_file, validate
from src.portfolio import analyse


def trades():
    return pd.DataFrame([
        ['2025-01-06', 'ABC', 'NYSE', 'BUY', 10, 10, 'USD', 100],
        ['2025-01-07', 'ABC', 'NYSE', 'BUY', 5, 20, 'USD', 100],
        ['2025-01-08', 'ABC', 'NYSE', 'SELL', 12, 30, 'USD', 360],
    ], columns=['date', 'ticker', 'exchange', 'transaction_type', 'quantity', 'price', 'currency', 'gross_amount'])


def run(frame, splits=None, prices=None, rate=1.):
    tx = validate(frame)
    index = pd.date_range('2025-01-06', '2025-01-09')
    prices = pd.DataFrame({'ABC': prices or [10., 20., 30., 40.]}, index=index)
    return analyse(tx, prices, {'ABC': splits if splits is not None else pd.Series(dtype=float)},
                   {'USD': pd.Series(rate, index=index)}, {})


def test_fifo_partial_sale_and_reconciliation():
    h, t, _, _ = run(trades())
    row = h.iloc[0]
    assert row.shares == 3
    assert row.cost_basis == 60
    assert row.realised == 220
    assert row.unrealised == 60
    assert row.total_gain == row.value + row.proceeds - row.purchases
    assert t['Holdings value'].iloc[-1] == row.value


def test_oversell():
    frame = trades()
    frame.loc[2, ['quantity', 'gross_amount']] = [16, 480]
    with pytest.raises(ValueError, match='exceeds available'):
        run(frame)


def test_split_and_fx():
    frame = trades().iloc[[0, 2]].copy()
    frame.loc[2, ['quantity', 'gross_amount']] = [12, 360]
    split = pd.Series([2.], index=pd.to_datetime(['2025-01-07']))
    h, _, _, _ = run(frame, splits=split, prices=[5., 10., 30., 40.], rate=.8)
    assert h.iloc[0].shares == 8
    assert h.iloc[0].cost_basis == pytest.approx(32)
    assert h.iloc[0].realised == pytest.approx(240)


def test_missing_price_rejected():
    with pytest.raises(ValueError, match='missing while'):
        run(trades(), prices=[float('nan'), 20., 30., 40.])


def test_flow_adjustment_flat_prices():
    frame = trades().copy()
    frame['price'] = 10
    frame['gross_amount'] = frame.quantity * 10
    _, timeline, _, _ = run(frame, prices=[10.] * 4)
    assert (timeline['Return index'] == 1).all()


def test_import_all_formats_and_sample():
    frame = trades()
    csv = frame.to_csv(index=False).encode()
    assert len(validate(read_file(csv, 'test.csv'))) == 3
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        frame.to_excel(writer, index=False, sheet_name='Trades')
    assert len(validate(read_file(buffer.getvalue(), 'test.xlsx', 'Trades'))) == 3
    workbook = xlwt.Workbook()
    sheet = workbook.add_sheet('Trades')
    for r, values in enumerate([frame.columns.tolist(), *frame.values.tolist()]):
        for c, value in enumerate(values):
            sheet.write(r, c, value)
    buffer = BytesIO()
    workbook.save(buffer)
    assert len(validate(read_file(buffer.getvalue(), 'test.xls'))) == 3
    sample = validate(pd.read_csv(Path('data/sample_stock_transactions.csv')))
    assert len(sample) == 48
    assert 'AZN.L' in sample.symbol.values
    assert 'BRK-B' in sample.symbol.values


def test_invalid_amount_and_future_date():
    frame = trades()
    frame.loc[0, 'gross_amount'] = 1
    with pytest.raises(ValueError, match='gross_amount'):
        validate(frame)
    frame = trades()
    frame.loc[0, 'date'] = '2099-01-01'
    with pytest.raises(ValueError, match='future'):
        validate(frame)
