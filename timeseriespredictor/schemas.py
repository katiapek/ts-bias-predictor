# timeseriespredictor/schemas.py

from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional
from enum import Enum


class OHLCBase(BaseModel):
    ticker: str
    date: date
    open: float
    high: float
    low: float
    close: float


class PredictionBase(BaseModel):
    ticker: str
    date: date
    predicted_bias: float
    predicted_price: float


class OHLCResponse(OHLCBase):
    id: int

    class Config:
        from_attributes = True


class PredictionResponse(PredictionBase):
    id: int

    class Config:
        from_attributes = True


class AuthProvider(str, Enum):
    google = "google"
    facebook = "facebook"


class SubscriptionStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    canceled = "canceled"


class UserBase(BaseModel):
    email: str
    name: Optional[str] = None
    provider: AuthProvider
    provider_id: str
    picture: Optional[str] = None
    is_premium: bool = False


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionBase(BaseModel):
    provider: str
    status: SubscriptionStatus
    start_date: datetime
    end_date: Optional[datetime] = None


class SubscriptionCreate(BaseModel):
    provider: str


class SubscriptionResponse(SubscriptionBase):
    id: int
    user_id: int
    last_payment_id: Optional[str] = None

    class Config:
        from_attributes = True
