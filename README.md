# Time Series Bias Predictor

A FastAPI backend that serves daily market bias predictions (bullish/bearish) for futures and crypto, powered by the [ct-xLSTM-TS](https://github.com/ct-xlstm/ct-xlstm-ts) time-series model. The model runs on a CUDA-enabled AWS instance; this service exposes the predictions and performance metrics via a REST API.

## Supported Instruments

| Ticker    | Name      |
|-----------|-----------|
| NQ=F      | NQ 100    |
| ES=F      | S&P 500   |
| 6E=F      | EUR/USD   |
| 6J=F      | JPY/USD   |
| CL=F      | Crude Oil |
| GC=F      | Gold      |
| BTC-USD   | Bitcoin   |

## Architecture

```
Yahoo Finance ──► OHLC data ──► ct-xLSTM-TS model (CUDA / AWS) ──► S3
                                                                     │
PostgreSQL ◄── Alembic migrations                                    ▼
    │                                                         CSV predictions
    ▼                                                         & metrics
FastAPI backend ◄────────────────────────────────────────────────────┘
    │
    ├── /predict/{ticker}/{freq}     prediction endpoints (API-key protected)
    ├── /metrics/{ticker}/{freq}     model performance metrics
    ├── /auth/google/callback        Google OAuth → JWT
    ├── /feedback                    customer feedback via AWS SES
    └── /                            React landing page
```

## Tech Stack

- **Model**: ct-xLSTM-TS (PyTorch, requires CUDA)
- **Backend**: FastAPI, Pydantic, Uvicorn
- **Database**: PostgreSQL, SQLAlchemy ORM, Alembic migrations
- **Cloud**: AWS — S3 (prediction/metrics storage), SES (email), Elastic Beanstalk (deployment)
- **Auth**: Google OAuth 2.0 with JWT tokens
- **Frontend**: React (compiled, served as static files)
- **Containerization**: Docker

## Database Schema

- **ohlc** — historical OHLC candle data per ticker/timeframe
- **predictions** — predicted bias (-1 to 1) and predicted price
- **metrics** — model performance (MAE, RMSE, R², accuracy, precision, recall, F1)
- **users** — OAuth accounts (Google)
- **subscriptions** — user subscription status (Stripe/Paddle)

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL
- AWS CLI configured with S3/SES access

### Setup

```bash
# Clone and install
git clone https://github.com/katiapek/ts-bias-predictor.git
cd TimeSeriesBiasPredictor
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your values (see Environment Variables below)

# Run database migrations
alembic upgrade head

# Start the server
uvicorn timeseriespredictor.main:app --reload
```

### Environment Variables

| Variable                     | Description                          | Required |
|------------------------------|--------------------------------------|----------|
| `DATABASE_URL`               | PostgreSQL connection string         | Yes      |
| `JWT_SECRET`                 | Secret key for signing JWT tokens    | Yes      |
| `API_KEY`                    | API key for prediction endpoints     | Yes      |
| `BUCKET_NAME`                | S3 bucket with prediction CSVs      | Yes      |
| `GOOGLE_CLIENT_ID`           | Google OAuth client ID               | Yes      |
| `GOOGLE_CLIENT_SECRET`       | Google OAuth client secret           | Yes      |
| `GOOGLE_REDIRECT_URI`        | OAuth callback URL                   | Yes      |
| `AWS_REGION`                 | AWS region for SES                   | No       |
| `FEEDBACK_TO_EMAIL`          | Email address for feedback delivery  | No       |
| `SES_SENDER_EMAIL`           | Verified SES sender email            | No       |

### Docker

```bash
docker build -t bias-predictor .
docker run -p 8000:8000 --env-file .env bias-predictor
```

## API Endpoints

| Method | Path                       | Auth    | Description                        |
|--------|----------------------------|---------|------------------------------------|
| GET    | `/predict/{ticker}/{freq}` | API Key | Prediction for a single ticker     |
| GET    | `/predict_all/{freq}`      | API Key | Predictions for all tickers        |
| GET    | `/metrics/{ticker}/{freq}` | API Key | Performance metrics for a ticker   |
| GET    | `/metrics_all/{freq}`      | API Key | Metrics for all tickers            |
| GET    | `/auth/google/callback`    | —       | Google OAuth callback              |
| POST   | `/feedback`                | —       | Submit feedback (email, subject, message) |

## License

This project is provided for portfolio and educational purposes.
