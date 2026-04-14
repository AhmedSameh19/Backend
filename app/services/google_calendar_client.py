"""Google Calendar OAuth and API client."""
from __future__ import annotations

import base64
import hashlib
import json
import secrets
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import redis
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.google_calendar_token import GoogleCalendarToken

SCOPES = ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/calendar.events"]
PKCE_STATE_TTL_SECONDS = 600
_PKCE_REDIS_KEY_PREFIX = "gcal:pkce:"
_pkce_lock = threading.Lock()
_pkce_fallback_store: Dict[str, Dict[str, Any]] = {}


def _get_flow() -> Flow:
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        raise ValueError("GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set")
    redirect_uri = settings.GOOGLE_CALENDAR_REDIRECT_URI or f"{settings.BACKEND_URL}/api/v1/calendar/google/callback"
    return Flow.from_client_config(
        {
            "web": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )


def _urlsafe_b64_no_pad(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _build_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return _urlsafe_b64_no_pad(digest)


def _get_pkce_redis() -> Optional[redis.Redis]:
    if not settings.REDIS_URL:
        return None
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        client.ping()
        return client
    except Exception:
        return None


def _store_pkce_state(nonce: str, user_id: str, code_verifier: str) -> None:
    payload = {"user_id": user_id, "code_verifier": code_verifier, "created_at": int(time.time())}
    redis_client = _get_pkce_redis()
    if redis_client is not None:
        redis_client.setex(f"{_PKCE_REDIS_KEY_PREFIX}{nonce}", PKCE_STATE_TTL_SECONDS, json.dumps(payload))
        return
    # Local fallback for non-Redis/dev environments.
    with _pkce_lock:
        _pkce_fallback_store[nonce] = {**payload, "expires_at": time.time() + PKCE_STATE_TTL_SECONDS}


def _load_and_consume_pkce_state(nonce: str) -> Dict[str, Any]:
    redis_client = _get_pkce_redis()
    if redis_client is not None:
        key = f"{_PKCE_REDIS_KEY_PREFIX}{nonce}"
        raw = redis_client.get(key)
        redis_client.delete(key)
        if not raw:
            raise ValueError("OAuth state is missing or expired. Please reconnect Google Calendar.")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            raise ValueError("Invalid OAuth state payload")
        return payload

    with _pkce_lock:
        payload = _pkce_fallback_store.pop(nonce, None)
    if not payload:
        raise ValueError("OAuth state is missing or expired. Please reconnect Google Calendar.")
    if payload.get("expires_at", 0) < time.time():
        raise ValueError("OAuth state expired. Please reconnect Google Calendar.")
    return payload


def get_authorization_url(state: str) -> str:
    """Build Google OAuth URL with PKCE and nonce state."""
    flow = _get_flow()
    code_verifier = secrets.token_urlsafe(48)
    code_challenge = _build_code_challenge(code_verifier)
    nonce = secrets.token_urlsafe(24)
    _store_pkce_state(nonce=nonce, user_id=state, code_verifier=code_verifier)
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=nonce,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    return url


def exchange_code_for_tokens(code: str, state: str, db: Session) -> GoogleCalendarToken:
    """Exchange authorization code for tokens and store for user (state=pkce nonce)."""
    flow = _get_flow()
    pkce_state = _load_and_consume_pkce_state(state)
    user_id = str(pkce_state.get("user_id") or "").strip()
    code_verifier = str(pkce_state.get("code_verifier") or "").strip()
    if not user_id or not code_verifier:
        raise ValueError("Invalid OAuth state payload for PKCE exchange")

    flow.fetch_token(code=code, code_verifier=code_verifier)
    creds = flow.credentials
    expires_at = None
    if creds.expiry:
        expires_at = creds.expiry

    row = db.query(GoogleCalendarToken).filter(GoogleCalendarToken.user_id == user_id).first()
    if row:
        row.access_token = creds.token
        row.refresh_token = row.refresh_token or creds.refresh_token
        row.expires_at = expires_at
        db.commit()
        db.refresh(row)
        return row
    row = GoogleCalendarToken(
        user_id=user_id,
        access_token=creds.token,
        refresh_token=creds.refresh_token,
        expires_at=expires_at,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _get_credentials_for_user(user_id: str, db: Session) -> Optional[Credentials]:
    """Load credentials from DB; refresh access token if expired."""
    row = db.query(GoogleCalendarToken).filter(GoogleCalendarToken.user_id == user_id).first()
    if not row:
        return None
    creds = Credentials(
        token=row.access_token,
        refresh_token=row.refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )
    # Refresh if DB says expired (or no expiry stored) or Credentials say expired
    now = datetime.now(timezone.utc)
    expires_at = row.expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    need_refresh = (
        row.refresh_token
        and (expires_at is None or expires_at <= now)
    ) or (getattr(creds, "expired", False) and row.refresh_token)
    if need_refresh and row.refresh_token:
        try:
            creds.refresh(Request())
            row.access_token = creds.token
            if getattr(creds, "expiry", None):
                row.expires_at = creds.expiry
            db.commit()
        except Exception:
            pass
    return creds


def list_events(
    user_id: str,
    db: Session,
    time_min: Optional[datetime] = None,
    time_max: Optional[datetime] = None,
    max_results: int = 100,
) -> List[Dict[str, Any]]:
    """List events from the user's primary Google Calendar."""
    creds = _get_credentials_for_user(user_id, db)
    if not creds:
        return []
    service = build("calendar", "v3", credentials=creds)
    params: Dict[str, Any] = {
        "calendarId": "primary",
        "singleEvents": True,
        "orderBy": "startTime",
        "maxResults": max_results,
    }
    if time_min:
        params["timeMin"] = time_min.isoformat() + ("Z" if time_min.tzinfo is None else "")
    if time_max:
        params["timeMax"] = time_max.isoformat() + ("Z" if time_max.tzinfo is None else "")
    result = service.events().list(**params).execute()
    return result.get("items", [])


def create_event(
    user_id: str,
    db: Session,
    summary: str,
    start: datetime,
    end: datetime,
    description: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Create an event in the user's primary Google Calendar."""
    creds = _get_credentials_for_user(user_id, db)
    if not creds:
        return None
    service = build("calendar", "v3", credentials=creds)
    body: Dict[str, Any] = {
        "summary": summary,
        "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
    }
    if description:
        body["description"] = description
    event = service.events().insert(calendarId="primary", body=body).execute()
    return event


def has_connected_calendar(user_id: str, db: Session) -> bool:
    """Return True if user has stored Google Calendar tokens."""
    row = db.query(GoogleCalendarToken).filter(GoogleCalendarToken.user_id == user_id).first()
    return row is not None
