import yfinance as yf
import pandas as pd
from db import SessionLocal
from models import OHLC
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

TICKER = "NQ=F"
TIMEFRAME = "1d"
START_DATE = "2000-01-01"
END_DATE = None  # None = up to today


def get_last_date(ticker: str, timeframe: str = "1d"):
    session: Session = SessionLocal()
    try:
        last_row = session.query(OHLC).filter_by(
            ticker=ticker,
            timeframe=timeframe
        ).order_by(OHLC.date.desc()).first()
        if last_row:
            return last_row.date
        return None
    finally:
        session.close()


def download_ohlc(ticker: str, timeframe: str = "1d"):
    last_date = get_last_date(ticker, timeframe)  # this is a date

    # Start from the day after the last date, or a default start
    start = last_date + timedelta(days=1) if last_date else datetime(2000, 9, 18).date()
    end = datetime.today().date()  # convert to date

    if start >= end:
        print("No new data to download")
        return pd.DataFrame()  # nothing to download

    df = yf.download(ticker, start=start, end=end, interval=timeframe)
    if df.empty:
        return df

    df = df.reset_index()  # 'Date' becomes a column
    df.rename(columns={col: col.lower() for col in df.columns}, inplace=True)
    return df


def save_to_db(df: pd.DataFrame, ticker: str, timeframe: str = "1d"):
    if df.empty:
        return

    session: Session = SessionLocal()
    try:
        for _, row in df.iterrows():
            # check if row already exists
            exists = session.query(OHLC).filter_by(
                ticker=ticker,
                date=row["date"].date(),
                timeframe=timeframe
            ).first()

            if not exists:
                ohlc = OHLC(
                    ticker=ticker,
                    date=row["date"].date(),
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=row["volume"],
                    timeframe=timeframe
                )
                session.add(ohlc)

        session.commit()
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    df = download_ohlc(TICKER, TIMEFRAME)
    save_to_db(df, TICKER, TIMEFRAME)
