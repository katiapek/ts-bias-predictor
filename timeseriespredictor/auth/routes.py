# timeseriespredictor/auth/routes.py
from fastapi import APIRouter, Query, Depends, Response, HTTPException
from sqlalchemy.orm import Session
from timeseriespredictor.db import get_db
from .service import exchange_google_code_for_token, fetch_google_userinfo, create_or_get_user, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/google/callback")
def google_callback(code: str = Query(...), state: str | None = None, response: Response = None, db: Session = Depends(get_db)):
    """
    Expects: GET /auth/google/callback?code=XXXX
    Exchanges the code, fetches userinfo, creates/gets user and returns JWT and user.
    It also sets an HttpOnly cookie named 'access_token'.
    """
    try:
        token_resp = exchange_google_code_for_token(code)
        access_token = token_resp.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="No access_token in token response")

        userinfo = fetch_google_userinfo(access_token)
        if not userinfo.get("email"):
            raise HTTPException(status_code=400, detail="Google did not return email")

        user = create_or_get_user(db, userinfo)

        jwt_token = create_access_token({"sub": str(user.id), "email": user.email})
        # Set HttpOnly cookie (Secure flag should be True in prod)
        response.set_cookie(
            key="access_token",
            value=jwt_token,
            httponly=True,
            samesite="lax",
            secure=False  # set True in production (HTTPS)
        )

        # Return minimal JSON for debugging; frontend may redirect after this
        return {"access_token": jwt_token, "user": {
            "id": user.id, "email": user.email, "name": user.name, "is_premium": user.is_premium
        }}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))
