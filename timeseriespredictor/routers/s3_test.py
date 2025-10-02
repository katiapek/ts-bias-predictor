import boto3
import csv
from fastapi import APIRouter

router = APIRouter()

# Config
BUCKET_NAME = "xlstm"
s3 = boto3.client("s3")  # uses credentials from aws configure

@router.get("/predict/{ticker)}")
def get_prediction(ticker: str):
    key = f"/predictions/{ticker.replace('=','')}_prediction.csv"

    try:
        # Fetch object from S3
        obj = s3.get_object(Bucket=BUCKET_NAME, Key=key)
        content = obj["Body"].read().decode("utf-8")

        # Parse CSV
        rows = list(csv.DictReader(content.splitlines()))
        if not rows:
            return {"ticker": ticker, "prediction": None, "message": "No data"}

        latest = rows[-1]  # last row = latest prediction
        return {
            "ticker": ticker,
            "date": latest["date"],
            "prediction": latest["prediction"]
        }

    except s3.exceptions.NoSuchKey:
        return {"ticker": ticker, "prediction": None, "message": "No file in S3"}
    except Exception as e:
        return {"ticker": ticker, "prediction": None, "error": str(e)}