# timeseriespredictor/models.py

from timeseriespredictor.db import Base
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Float, Date
from sqlalchemy.orm import relationship
from datetime import datetime
import enum


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


# OAuth provider types
class AuthProvider(str, enum.Enum):
    google = "google"
    facebook = "facebook"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    provider = Column(Enum(AuthProvider), nullable=False)
    provider_id = Column(String, unique=True, nullable=False)
    picture = Column(String, nullable=True)
    is_premium = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    subscriptions = relationship("Subscription", back_populates="user")


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    canceled = "canceled"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String, default="stripe")  # can be 'stripe' or 'paddle'
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.inactive)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    last_payment_id = Column(String, nullable=True)

    user = relationship("User", back_populates="subscriptions")