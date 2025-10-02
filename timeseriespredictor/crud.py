from sqlalchemy.orm import Session
from . import models

from datetime import date
import random


def get_ohlc_by_ticker(db:Session, ticker: str):
    return db.query(models.OHLC).filter(models.OHLC.ticker == ticker).all()


def get_prediction_by_ticker(db: Session, ticker: str):
    return db.query(models.Prediction).filter(models.Prediction.ticker == ticker).all()


def create_dummy_ohlc(db: Session, ticker: str):
    dummy = models.OHLC(
        ticker=ticker,
        date=date.today(),
        open=random.uniform(100, 200),
        high=random.uniform(200, 250),
        low=random.uniform(90, 150),
        close=random.uniform(100, 200),
        volume=random.uniform(1000, 5000)
    )
    db.add(dummy)
    db.commit()
    db.refresh(dummy)
    return dummy


def create_dummy_prediction(db: Session, ticker: str):
    dummy = models.Prediction(
        ticker=ticker,
        date=date.today(),
        predicted_bias=random.uniform(-1, 1),
        predicted_price=random.uniform(100, 200)
    )
    db.add(dummy)
    db.commit()
    db.refresh(dummy)
    return dummy