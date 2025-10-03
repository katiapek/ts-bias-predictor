from fastapi import FastAPI  # , Depends
# from timeseriespredictor.routers import predictions
# from sqlalchemy.orm import Session
# from timeseriespredictor import db, schemas, crud
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


def _prediction_payload_for(ticker: str):
    key = f"predictions/{ticker.replace('=', '')}_prediction.csv"
    try:
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        content = obj["Body"].read().decode("utf-8")
        rows = list(csv.DictReader(content.splitlines()))

        name = TICKERS.get(ticker, ticker)
        if len(rows) >= 2:
            return {
                "ticker": ticker,
                "name": name,
                "last_date_1": rows[-2]["Date"],
                "prediction_1": rows[-2]["Predicted Direction"],
                "last_date_2": rows[-1]["Date"],
                "prediction_2": rows[-1]["Predicted Direction"],
                "close_2": rows[-1].get("Close"),
            }
        elif len(rows) == 1:
            r = rows[-1]
            return {
                "ticker": ticker,
                "name": name,
                "last_date_2": r["Date"],
                "prediction_2": r["Predicted Direction"],
                "close_2": r.get("Close"),
                "message": "Only one row available",
            }
        else:
            return {"ticker": ticker, "name": name, "message": "No data"}
    except s3.exceptions.NoSuchKey:
        return {"ticker": ticker, "name": TICKERS.get(ticker, ticker), "message": "No file in S3"}
    except Exception as e:
        return {"ticker": ticker, "name": TICKERS.get(ticker, ticker), "error": str(e)}


def _metrics_payload_for(ticker: str):
    key = f"metrics/{ticker.replace("=", "")}_data.csv"

    try:
        # Fetch object from S3
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        content = obj["Body"].read().decode("utf-8")

        # Parse CSV
        rows = list(csv.DictReader(content.splitlines()))
        if not rows:
            return {"ticker": ticker, "rise_pct": None, "fall_pct": None, "f1_score": None, "message": "No data"}

        latest = rows[-1]  # last row = latest prediction
        name = TICKERS.get(ticker, ticker)

        return {
            "ticker": ticker,
            "name": name,
            "rise_pct": latest["Precision (Rise)"],
            "fall_pct": latest["Precision (Fall)"],
            "f1_score": latest["F1 Score"],
        }

    except s3.exceptions.NoSuchKey:
        return {"ticker": ticker, "rise_pct": None, "fall_pct": None, "f1_score": None, "message": "No file in S3"}
    except Exception as e:
        return {"ticker": ticker, "rise_pct": None, "fall_pct": None, "f1_score": None, "error": str(e)}

# @app.get("/")
# def root():
#     return {"message": "Welcome to Clocktrades Bias Predictor API"}

# @app.get("/ohlc/{ticker}", response_model=list[schemas.OHLCResponse])
# def read_ohlc(ticker: str, db_session: Session = Depends(get_db)):
#     return crud.get_ohlc_by_ticker(db_session, ticker)

# @app.get("/prediction/{ticker}", response_model=list[schemas.PredictionResponse])
# def read_prediction(ticker: str, db_session: Session = Depends(get_db)):
#     return crud.get_prediction_by_ticker(db_session, ticker)


@app.get("/predict/{ticker}")
def get_prediction(ticker: str):
    return _prediction_payload_for(ticker)


@app.get("/predict_all")
def get_all_predictions():
    tickers = list(TICKERS.keys())

    # sequential - simple
    return {"results": [_prediction_payload_for(t) for t in tickers]}

    # concurrent version (faster for network I/O)
    # results = []
    # with ThreadPoolExecutor(max_workers=min(8, len(tickers))) as pool:
    #   futures = [pool.submit(_prediction_payload_for, t) for t in tickers]
    #   for f in futures:
    #       results.append(f.result())
    # return {"results": results}


@app.get("/metrics/{ticker}")
def get_metrics(ticker: str):
    return _metrics_payload_for(ticker)


@app.get("/metrics_all")
def get_all_metrics():
    tickers = list(TICKERS.keys())

    return {"results": [_metrics_payload_for(t) for t in tickers]}
