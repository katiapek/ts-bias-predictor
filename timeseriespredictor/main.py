from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import boto3
import csv
from datetime import datetime, timedelta
import os
from pydantic import BaseModel, EmailStr, constr
from botocore.exceptions import ClientError
import html
import email_validator
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, FileResponse, HTMLResponse
from pathlib import Path

app = FastAPI(title="ClockTrades Bias Predictor")

# Dynamically find the static directory relative to this file
BASE_DIR = Path(__file__).resolve().parent
LANDING_DIR = BASE_DIR / "static" / "landing"

# Mount static files (HTML, JS, CSS)
app.mount("/landing", StaticFiles(directory=str(LANDING_DIR), html=True), name="landing")

# Config
s3 = boto3.client("s3")  # uses credentials from aws configure
# Get secrets from env vars
API_KEY = os.getenv("API_KEY")
BUCKET_NAME = os.getenv("BUCKET_NAME")
# --- AWS SES Config ---
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
FEEDBACK_TO_EMAIL = os.getenv("FEEDBACK_TO_EMAIL", "kamil@clocktrades.com")
SES_SENDER_EMAIL = os.getenv("SES_SENDER_EMAIL", FEEDBACK_TO_EMAIL)  # must be verified in SES
ses = boto3.client("ses", region_name=AWS_REGION)

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


def _get_cached(cache_dict, key):
    """Check cache and return data if not expired"""
    entry = cache_dict.get(key)
    if entry:
        data, timestamp = entry
        if datetime.utcnow() - timestamp < CACHE_TTL:
            return data
    return None


def _set_cache(cache_dict, key, data):
    cache_dict[key] = (data, datetime.utcnow())


def _prediction_payload_for(ticker: str, freq: str):
    # Check cache first
    cache_key = (ticker, freq)
    cached = _get_cached(cache_predictions, cache_key)
    if cached:
        return cached

    name = TICKERS.get(ticker, ticker)
    key = f"predictions/{ticker.replace('=', '')}_{freq}_prediction.csv"

    try:
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        content = obj["Body"].read().decode("utf-8")
        rows = list(csv.DictReader(content.splitlines()))

        if not rows:
            payload = {"ticker": ticker, "name": name, "message": "No data"}
            _set_cache(cache_predictions, cache_key, payload)
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
        _set_cache(cache_predictions, cache_key, payload)
        return payload

    except ClientError as e:

        code = e.response.get("Error", {}).get("Code")

        if code == "NoSuchKey":
            payload = {"ticker": ticker, "name": name, "message": "No file in S3"}

            _set_cache(cache_predictions, cache_key, payload)

            return payload

        payload = {"ticker": ticker, "name": name, "error": str(e)}

        _set_cache(cache_predictions, cache_key, payload)

        return payload

    except Exception as e:

        payload = {"ticker": ticker, "name": name, "error": str(e)}

        _set_cache(cache_predictions, cache_key, payload)

        return payload


def _metrics_payload_for(ticker: str, freq: str):
    # Check cache first
    cache_key = (ticker, freq)
    cached = _get_cached(cache_metrics, cache_key)
    if cached:
        return cached
    name = TICKERS.get(ticker, ticker)
    key = f"metrics/{ticker.replace('=', '')}_{freq}_data.csv"

    try:
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        content = obj["Body"].read().decode("utf-8")
        rows = list(csv.DictReader(content.splitlines()))

        if not rows:
            payload = {"ticker": ticker, "rise_pct": None, "fall_pct": None, "f1_score": None, "message": "No data"}
            _set_cache(cache_metrics, cache_key, payload)
            return payload

        latest = rows[-1]
        payload = {
            "ticker": ticker,
            "name": name,
            "rise_pct": latest["Precision (Rise)"],
            "fall_pct": latest["Precision (Fall)"],
            "f1_score": latest["F1 Score"],
        }
        _set_cache(cache_metrics, cache_key, payload)
        return payload

    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")

        if code == "NoSuchKey":
            payload = {"ticker": ticker, "name": name, "rise_pct": None, "fall_pct": None, "f1_score": None,
                       "message": "No file in S3"}

            _set_cache(cache_metrics, cache_key, payload)

            return payload

        payload = {"ticker": ticker, "name": name, "rise_pct": None, "fall_pct": None, "f1_score": None,
                   "error": str(e)}

        _set_cache(cache_metrics, cache_key, payload)

        return payload

    except Exception as e:

        payload = {"ticker": ticker, "name": name, "rise_pct": None, "fall_pct": None, "f1_score": None,
                   "error": str(e)}
        _set_cache(cache_metrics, cache_key, payload)
        return payload


# Redirect root path to /landing/
@app.get("/", include_in_schema=False)
def read_root():
    index_file = LANDING_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))


@app.get("/predict/{ticker}/{freq}")
def get_prediction(ticker: str, freq: str, x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    return _prediction_payload_for(ticker, freq)


@app.get("/predict_all/{freq}")
def get_all_predictions(freq: str, x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    return {"results": [_prediction_payload_for(t, freq) for t in TICKERS.keys()]}


@app.get("/metrics/{ticker}/{freq}")
def get_metrics(ticker: str, freq: str, x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    return _metrics_payload_for(ticker, freq)


@app.get("/metrics_all/{freq}")
def get_all_metrics(freq: str, x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    return {"results": [_metrics_payload_for(t, freq) for t in TICKERS.keys()]}


# --- Pydantic model for feedback ---
class FeedbackRequest(BaseModel):
    email: EmailStr
    subject: constr(min_length=1, max_length=200)
    message: constr(min_length=1, max_length=5000)


# --- Feedback endpoint ---
@app.post("/feedback", status_code=200)
def submit_feedback(payload: FeedbackRequest):
    """Handles customer feedback and sends via AWS SES."""

    subject = f"[ClockTrades Feedback] {payload.subject}"

    # Sanitize user input to avoid injection in HTML
    safe_message = html.escape(payload.message)

    body_text = (
        f"Feedback submitted at {datetime.utcnow().isoformat()}Z\n\n"
        f"From: {payload.email}\n\n"
        f"Message:\n{payload.message}\n"
    )

    body_html = f"""
    <html>
      <body>
        <h3>Feedback submitted at {datetime.utcnow().isoformat()}Z</h3>
        <p><b>From:</b> {html.escape(payload.email)}</p>
        <p><b>Message:</b><br>{safe_message.replace(chr(10), '<br>')}</p>
      </body>
    </html>
    """

    try:
        ses.send_email(
            Source=SES_SENDER_EMAIL,
            Destination={"ToAddresses": [FEEDBACK_TO_EMAIL]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": body_text, "Charset": "UTF-8"},
                    "Html": {"Data": body_html, "Charset": "UTF-8"},
                },
            },
            ReplyToAddresses=[payload.email],
        )
        return {"status": "ok"}

    except ClientError as e:
        raise HTTPException(
            status_code=400,
            detail=f"SES error: {e.response['Error']['Message']}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal error while sending feedback.")

# from timeseriespredictor.auth.routes import router as auth_router
# app.include_router(auth_router)
