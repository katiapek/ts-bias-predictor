from fastapi import FastAPI, Header, HTTPException  # , Depends
import boto3
import csv

API_KEY = "itssecret123"

app = FastAPI(title="ClockTrades Bias Predictor")

# Config
BUCKET_NAME = "xlstm"
s3 = boto3.client("s3")  # uses credentials from aws configure

TICKERS = {"NQ=F": "NQ 100",
           "ES=F": "S&P 500",
           "6E=F": "EUR/USD",
           "6J=F": "JPY/USD",
           "CL=F": "CRUDE OIL",
           "GC=F": "GOLD",
           "BTC-USD": "BITCOIN"
           }

def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _prediction_payload_for(ticker: str):
    key = f"predictions/{ticker.replace('=', '')}_prediction.csv"
    try:
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        content = obj["Body"].read().decode("utf-8")
        rows = list(csv.DictReader(content.splitlines()))

        name = TICKERS.get(ticker, ticker)

        if not rows:
            return {"ticker": ticker, "name": name, "message": "No data"}

        # Prepare arrays
        dates = [r.get("Date") for r in rows]
        preds = [r.get("Predicted Direction") for r in rows]
        closes = []

        for r in rows:
            c = r.get("Close")
            try:
                closes.append(float(c) if c not in (None, "") else None)
            except ValueError:
                closes.append(None)

        # Actual direction for index i (current day) vs prevous day
        def actual_dir(i:int):
            if i == 0 or closes[i] is None or closes[i-1] is None:
                return None
            if closes[i]>closes[i-1]:
                return "Up"
            if closes[i]<closes[i-1]:
                return "Down"
            return "Flat"

        # Evaluate correctness for the five dates preceding the last date

        n = len(rows)
        payload = {
            "ticker": ticker,
            "name": name,
            # prediction recorded on the latest day - for the next trading day
            "tomorrows_prediction": preds[-1] if n>=1 else None,
        }

        # Build date_i, close_i, pred_i, correct_prediction_i for i = 0..5
        max_items = 6
        for i in range(max_items):
            j = n - 1 - i  # row index of the date being reported (0 = latest)
            if j < 0:
                break

                # Prediction that applied to date j is the one recorded on the prior date (j-1)
            pred_for_j = preds[j - 1] if j - 1 >= 0 else None
            act = actual_dir(j)
            correct = None
            if act in ("Up", "Down") and pred_for_j in ("Up", "Down"):
                correct = (act == pred_for_j)

            payload[f"date_{i}"] = dates[j]
            payload[f"close_{i}"] = closes[j]
            payload[f"pred_{i}"] = pred_for_j
            payload[f"correct_prediction_{i}"] = True if correct is True else False if correct is False else None

        if n < max_items:
            payload["message"] = f"Only {n} row(s) available; computed up to {min(max_items, n)} date(s)."

        return payload

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


@app.get("/predict/{ticker}")
def get_prediction(ticker: str):
    return _prediction_payload_for(ticker)


@app.get("/predict_all")
def get_all_predictions(x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
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
def get_all_metrics(x_api_key: str = Header(None)):
    verify_api_key(x_api_key)
    tickers = list(TICKERS.keys())

    return {"results": [_metrics_payload_for(t) for t in tickers]}
