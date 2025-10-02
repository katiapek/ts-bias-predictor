# timeseriespredictor/schemas.py

from pydantic import BaseModel
from datetime import date

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