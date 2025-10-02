from fastapi import FastAPI, Depends
# from timeseriespredictor.routers import predictions
# from sqlalchemy.orm import Session
from timeseriespredictor import db, schemas, crud
import boto3
import csv

app = FastAPI(title="ClockTrades Bias Predictor")

# Config
BUCKET_NAME = "xlstm"
s3 = boto3.client("s3")  # uses credentials from aws configure

TICKERS = {"NQ=F": "Nasdaq 100 FUT",
           "ES=F": "S&P 500 FUT",
           "6E=F": "EUR/USD FUT",
           "6J=F": "JPY/USD FUT",
           "CL=F": "Crude Oil FUT",
           "GC=F": "Gold FUT",
           "BTC-USD": "Bitcoin SPOT"
           }
# def get_db():
#     db_session = db.SessionLocal()
#     try:
#         yield db_session
#     finally:
#         db_session.close()

@app.get("/")
def root():
    return {"message": "Welcome to Clocktrades Bias Predictor API"}

# @app.get("/ohlc/{ticker}", response_model=list[schemas.OHLCResponse])
# def read_ohlc(ticker: str, db_session: Session = Depends(get_db)):
#     return crud.get_ohlc_by_ticker(db_session, ticker)

# @app.get("/prediction/{ticker}", response_model=list[schemas.PredictionResponse])
# def read_prediction(ticker: str, db_session: Session = Depends(get_db)):
#     return crud.get_prediction_by_ticker(db_session, ticker)

@app.get("/predict/{ticker}")
def get_prediction(ticker: str):
    key = f"predictions/{ticker.replace("=","")}_prediction.csv"

    try:
        # Fetch object from S3
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        content = obj["Body"].read().decode("utf-8")

        # Parse CSV
        rows = list(csv.DictReader(content.splitlines()))
        if not rows:
            return {"ticker": ticker, "prediction": None, "message": "No data"}

        #latest = rows[-1]  # last row = latest prediction
        return {
            "ticker": ticker,
            "last_date_1": rows[-2]["Date"],
            "prediction_1": rows[-2]["Predicted Direction"],
            "last_date_2": rows[-1]["Date"],
            "prediction_2": rows[-1]["Predicted Direction"],
            "close_2": rows[-1]["Close"]
        }

    except s3.exceptions.NoSuchKey:
        return {"ticker": ticker, "prediction": None, "message": "No file in S3"}
    except Exception as e:
        return {"ticker": ticker, "prediction": None, "error": str(e)}

@app.get("/metrics/{ticker}")
def get_metrics(ticker: str):
    key = f"metrics/{ticker.replace("=","")}_data.csv"

    try:
        # Fetch object from S3
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        content = obj["Body"].read().decode("utf-8")

        # Parse CSV
        rows = list(csv.DictReader(content.splitlines()))
        if not rows:
            return {"ticker": ticker, "rise_pct": None,"fall_pct": None,"f1_score": None, "message": "No data"}

        latest = rows[-1]  # last row = latest prediction

        return {
            "ticker": ticker,
            "rise_pct": latest["Precision (Rise)"],
            "fall_pct": latest["Precision (Fall)"],
            "f1_score": latest["F1 Score"],
        }

    except s3.exceptions.NoSuchKey:
        return {"ticker": ticker, "rise_pct": None,"fall_pct": None,"f1_score": None, "message": "No file in S3"}
    except Exception as e:
        return {"ticker": ticker, "rise_pct": None,"fall_pct": None,"f1_score": None, "error": str(e)}

# @app.post("/ohlc/{ticker}", response_model=schemas.OHLCResponse)
# def add_dummy_ohlc(ticker: str, db_session: Session = Depends(get_db)):
#     return crud.create_dummy_ohlc(db_session, ticker)

# @app.post("prediction/{ticker}", response_model=schemas.PredictionResponse)
# def add_dummy_prediction(ticker: str, db_session: Session = Depends(get_db)):
#     return crud.create_dummy_prediction(db_session, ticker)
