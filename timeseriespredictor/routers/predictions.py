from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from timeseriespredictor.db import get_db, SessionLocal
from timeseriespredictor.models import Prediction

router = APIRouter()

@router.get("/predict/{ticker}")
def get_prediction(ticker: str, db: Session = Depends(get_db)):
    # Fetch latest prediction
    pred = db.query(Prediction).filter(Prediction.ticker == ticker).order_by(Prediction.date.desc()).first()
    if not pred:
        return {"ticker": ticker, "prediction": None, "message": "No prediction found."}
    return {"ticker": ticker, "prediction": pred.predicted_bias, "date": pred.date}