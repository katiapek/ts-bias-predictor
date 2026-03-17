# timeseriespredictor/auth/service.py
import os
from datetime import datetime, timedelta
import requests
from jose import jwt
from sqlalchemy.orm import Session
from timeseriespredictor import models
from timeseriespredictor.db import get_db

SECRET_KEY = os.getenv("JWT_SECRET")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET environment variable is required")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60*24*7))

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def exchange_google_code_for_token(code: str):
    token_url = "https://oauth2.googleapis.com/token"
    payload = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }
    resp = requests.post(token_url, data=payload, timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_google_userinfo(access_token: str):
    resp = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def create_or_get_user(db: Session, userinfo: dict):
    email = userinfo.get("email")
    provider_id = userinfo.get("id")
    name = userinfo.get("name")
    picture = userinfo.get("picture")

    # Try by provider_id first, then email
    user = db.query(models.User).filter_by(provider_id=provider_id).first()
    if not user and email:
        user = db.query(models.User).filter_by(email=email).first()

    if not user:
        user = models.User(
            email=email,
            name=name,
            provider=models.AuthProvider.google,
            provider_id=provider_id,
            picture=picture
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        # update basic info if changed
        changed = False
        if user.name != name:
            user.name = name
            changed = True
        if user.picture != picture:
            user.picture = picture
            changed = True
        if changed:
            db.commit()
            db.refresh(user)
    return user
