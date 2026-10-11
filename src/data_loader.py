"""File parsing and transaction validation, independent of the UI."""
from io import BytesIO
from pathlib import Path
import numpy as np
import pandas as pd

REQUIRED = ['date', 'ticker', 'exchange', 'transaction_type', 'quantity', 'price', 'currency', 'gross_amount']


def read_file(data: bytes, name: str, sheet=0):
    ext = Path(name).suffix.lower()
    if ext == '.csv':
        return pd.read_csv(BytesIO(data), encoding='utf-8-sig')
    if ext in {'.xls', '.xlsx'}:
        return pd.read_excel(BytesIO(data), sheet_name=sheet, engine='xlrd' if ext == '.xls' else 'openpyxl')
    raise ValueError('Please upload a CSV, XLS or XLSX file.')


def sheets(data: bytes, name: str):
    return pd.ExcelFile(BytesIO(data), engine='xlrd' if name.lower().endswith('.xls') else 'openpyxl').sheet_names


def yahoo_symbol(ticker, exchange):
    ticker = ticker.upper().strip()
    if exchange in {'LSE', 'LONDON'}:
        return ticker if ticker.endswith('.L') else ticker.rstrip('.') + '.L'
    return ticker.replace('.', '-') if exchange in {'NYSE', 'NASDAQ'} else ticker


def validate(frame):
    df = frame.copy()
    df.columns = df.columns.astype(str).str.strip().str.lower()
    if df.columns.duplicated().any():
        raise ValueError('Duplicate column names are not supported.')
    missing = sorted(set(REQUIRED) - set(df.columns))
    if missing:
        raise ValueError('Missing columns: ' + ', '.join(missing))
    df = df.dropna(how='all')
    if df.empty:
        raise ValueError('No transactions found.')
    for col in ['ticker', 'exchange', 'transaction_type', 'currency']:
        if df[col].isna().any():
            raise ValueError(f'{col} contains empty values.')
        df[col] = df[col].astype(str).str.strip().str.upper()
        if df[col].eq('').any():
            raise ValueError(f'{col} contains empty values.')
    df['date'] = pd.to_datetime(df.date, errors='coerce', format='mixed').dt.normalize()
    if df.date.isna().any() or (df.date > pd.Timestamp.now(tz='Europe/London').tz_localize(None).normalize()).any():
        raise ValueError('Dates must be valid, unambiguous dates and cannot be in the future. Use YYYY-MM-DD.')
    if not df.transaction_type.isin(['BUY', 'SELL']).all():
        raise ValueError('transaction_type must be BUY or SELL.')
    if not df.currency.str.fullmatch('[A-Z]{3}').all():
        raise ValueError('Use three-letter currency codes, e.g. USD or GBP. Enter UK prices in pounds, not pence.')
    for col in ['quantity', 'price', 'gross_amount']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        if not (np.isfinite(df[col]) & (df[col] > 0)).all():
            raise ValueError(f'{col} must contain finite positive numbers.')
    if not np.isclose(df.quantity * df.price, df.gross_amount, atol=.02, rtol=1e-6).all():
        raise ValueError('gross_amount must equal quantity × price (within rounding tolerance); fees are not supported.')
    df['symbol'] = [yahoo_symbol(t, e) for t, e in zip(df.ticker, df.exchange)]
    if (df.groupby('symbol').currency.nunique() > 1).any():
        raise ValueError('Each stock must have a single transaction currency.')
    for col in ['company_name', 'sector']:
        if col not in df:
            df[col] = 'Unknown'
        df[col] = df[col].fillna('Unknown').astype(str)
    return df.sort_values('date', kind='stable').reset_index(drop=True)
