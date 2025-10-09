from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import boto3
import csv
from datetime import datetime, timedelta
import os
from pydantic import BaseModel, EmailStr

app = FastAPI(title="ClockTrades Bias Predictor")

# Config
s3 = boto3.client("s3")  # uses credentials from aws configure
ses = boto3.client("ses", region_name="us-east-1")
# Get secrets from env vars
API_KEY = os.getenv("API_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")
# CORS setup - allow your front-end domain only
# For testing: allow_origins=["*"]
# For production: replace "*" with your actual front-end URL, e.g., "https://myapp.com"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # <-- update this for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FeedbackRequest(BaseModel):
    email: EmailStr
    subject: str
    message: str

TICKERS = {
    "NQ=F": "NQ 100",
    "ES=F": "S&P 500",
    "6E=F": "EUR/USD",
    "6J=F": "JPY/USD",
    "CL=F": "CRUDE OIL",
    "GC=F": "GOLD",
    "BTC-USD": "BITCOIN"
}

# In-memory cache
cache_predictions = {}
cache_metrics = {}
CACHE_TTL = timedelta(minutes=10)


def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _get_cached(cache_dict, ticker):
    """Check cache and return data if not expired"""
    entry = cache_dict.get(ticker)
    if entry:
        data, timestamp = entry
        if datetime.utcnow() - timestamp < CACHE_TTL:
            return data
    return None


def _set_cache(cache_dict, ticker, data):
    cache_dict[ticker] = (data, datetime.utcnow())


def _prediction_payload_for(ticker: str):
    # Check cache first
    cached = _get_cached(cache_predictions, ticker)
    if cached:
        return cached

    key = f"predictions/{ticker.replace('=', '')}_prediction.csv"
    try:
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        content = obj["Body"].read().decode("utf-8")
        rows = list(csv.DictReader(content.splitlines()))

        name = TICKERS.get(ticker, ticker)

        if not rows:
            payload = {"ticker": ticker, "name": name, "message": "No data"}
            _set_cache(cache_predictions, ticker, payload)
            return payload

        dates = [r.get("Date") for r in rows]
        preds = [r.get("Predicted Direction") for r in rows]
        closes = []
        for r in rows:
            c = r.get("Close")
            try:
                closes.append(float(c) if c not in (None, "") else None)
            except ValueError:
                closes.append(None)

        def actual_dir(i: int):
            if i == 0 or closes[i] is None or closes[i - 1] is None:
                return None
            if closes[i] > closes[i - 1]:
                return "Up"
            if closes[i] < closes[i - 1]:
                return "Down"
            return "Flat"

        n = len(rows)
        payload = {
            "ticker": ticker,
            "name": name,
            "tomorrows_prediction": preds[-1] if n >= 1 else None,
        }

        max_items = 6
        for i in range(max_items):
            j = n - 1 - i
            if j < 0:
                break
            pred_for_j = preds[j - 1] if j - 1 >= 0 else None
            act = actual_dir(j)
            correct = (act == pred_for_j) if act in ("Up", "Down") and pred_for_j in ("Up", "Down") else None

            payload[f"date_{i}"] = dates[j]
            payload[f"close_{i}"] = closes[j]
            payload[f"pred_{i}"] = pred_for_j
            payload[f"correct_prediction_{i}"] = True if correct else False if correct is False else None

        if n < max_items:
            payload["message"] = f"Only {n} row(s) available; computed up to {min(max_items, n)} date(s)."

        # Cache result
        _set_cache(cache_predictions, ticker, payload)
        return payload

    except s3.exceptions.NoSuchKey:
        payload = {"ticker": ticker, "name": name, "message": "No file in S3"}
        _set_cache(cache_predictions, ticker, payload)
        return payload
    except Exception as e:
        payload = {"ticker": ticker, "name": name, "error": str(e)}
        _set_cache(cache_predictions, ticker, payload)
        return payload


def _metrics_payload_for(ticker: str):
    # Check cache first
    cached = _get_cached(cache_metrics, ticker)
    if cached:
        return cached

    key = f"metrics/{ticker.replace('=', '')}_data.csv"
    try:
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        content = obj["Body"].read().decode("utf-8")
        rows = list(csv.DictReader(content.splitlines()))
        name = TICKERS.get(ticker, ticker)

        if not rows:
            payload = {"ticker": ticker, "rise_pct": None, "fall_pct": None, "f1_score": None, "message": "No data"}
            _set_cache(cache_metrics, ticker, payload)
            return payload

        latest = rows[-1]
        payload = {
            "ticker": ticker,
            "name": name,
            "rise_pct": latest["Precision (Rise)"],
            "fall_pct": latest["Precision (Fall)"],
            "f1_score": latest["F1 Score"],
        }
        _set_cache(cache_metrics, ticker, payload)
        return payload

    except s3.exceptions.NoSuchKey:
        payload = {"ticker": ticker, "rise_pct": None, "fall_pct": None, "f1_score": None, "message": "No file in S3"}
        _set_cache(cache_metrics, ticker, payload)
        return payload
    except Exception as e:
        payload = {"ticker": ticker, "rise_pct": None, "fall_pct": None, "f1_score": None, "error": str(e)}
        _set_cache(cache_metrics, ticker, payload)
        return payload


@app.get("/predict/{ticker}")
def get_prediction(ticker: str, x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    return _prediction_payload_for(ticker)


@app.get("/predict_all")
def get_all_predictions(x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    return {"results": [_prediction_payload_for(t) for t in TICKERS.keys()]}


@app.get("/metrics/{ticker}")
def get_metrics(ticker: str, x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    return _metrics_payload_for(ticker)


@app.get("/metrics_all")
def get_all_metrics(x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    return {"results": [_metrics_payload_for(t) for t in TICKERS.keys()]}

@app.post("/feedback")
def send_feedback(feedback: FeedbackRequest, x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    ses.send_email(
        Source="kamil@clocktrades.com",
        Destination={"ToAddresses": ["kamil@clocktrades.com"]},
        Message={
            "Subject": {"Data": f"BiasPredictor Feedback: {feedback.subject}"},
            "Body": {
                "Text": {
                    "Data": f"From: {feedback.email}\n\n{feedback.message}"
                }
            },
        },
    )
    return {"status": "success"}
