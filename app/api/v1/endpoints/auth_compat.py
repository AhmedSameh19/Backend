"""Compatibility /auth routes for the React app (local dev + cookie/Bearer checks)."""

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request

router = APIRouter(prefix="/auth", tags=["auth-compat"])


def _bearer_token(authorization: Optional[str], request: Request) -> Optional[str]:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip() or None
    return request.cookies.get("access_token")


@router.get("/check")
def auth_check(request: Request, authorization: Optional[str] = Header(None)):
    token = _bearer_token(authorization, request)
    return {"authenticated": bool(token)}


@router.get("/profile")
def auth_profile(request: Request, authorization: Optional[str] = Header(None)):
    token = _bearer_token(authorization, request)
    if not token:
        return {"user": None}
    return {
        "user": {
            "role": "user",
            "mc_code": None,
            "lc_code": None,
            "lc_name": None,
        }
    }


@router.get("/resolve-dashboard")
def resolve_dashboard(request: Request, authorization: Optional[str] = Header(None)):
    token = _bearer_token(authorization, request)
    if not token:
        return {"redirect": "/login"}
    return {"redirect": "/"}


@router.post("/logout")
def auth_logout():
    return {"ok": True}


@router.post("/login")
def auth_login_stub():
    raise HTTPException(status_code=501, detail="Use EXPA OAuth from the login page")


@router.post("/refresh")
def auth_refresh_stub():
    raise HTTPException(status_code=401, detail="No refresh token session")
