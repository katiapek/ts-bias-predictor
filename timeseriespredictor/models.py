from sqlalchemy import Column, Integer, String, Float, Date
from timeseriespredictor.db import Base

class OHLC(Base):
    __tablename__ = "ohlc"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    date = Column(Date)
    timeframe = Column(String, index=True)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)


class Prediction(Base):
    __tablename__ = "predictions"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    date = Column(Date)
    timeframe = Column(String, index=True)
    predicted_bias = Column(Float)  # e.g., -1 to 1 for bearish/bullish
    predicted_price = Column(Float)

class Metrics(Base):
    __tablename__ = "metrics"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    date = Column(Date)
    timeframe = Column(String, index=True)
    mae = Column(Float)
    mse = Column(Float)
    rmse = Column(Float)
    rmsse = Column(Float)
    mape = Column(Float)
    mase = Column(Float)
    r2 = Column(Float)
    test_accuracy = Column(Float)
    recall = Column(Float)
    precision_rise = Column(Float)
    precision_fall = Column(Float)
    f1_score = Column(Float)
    validation_accuracy = Column(Float)
    train_accuracy = Column(Float)