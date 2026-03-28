"""Google Calendar OAuth and API client."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.google_calendar_token import GoogleCalendarToken

SCOPES = ["https://www.googleapis.com/auth/calendar", "https://www.googleapis.com/auth/calendar.events"]


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


def get_authorization_url(state: str) -> str:
    """Build Google OAuth URL. state should be user_id for callback."""
    flow = _get_flow()
    url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    return url


def exchange_code_for_tokens(code: str, state: str, db: Session) -> GoogleCalendarToken:
    """Exchange authorization code for tokens and store for user (state=user_id)."""
    flow = _get_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    expires_at = None
    if creds.expiry:
        expires_at = creds.expiry

    row = db.query(GoogleCalendarToken).filter(GoogleCalendarToken.user_id == state).first()
    if row:
        row.access_token = creds.token
        row.refresh_token = row.refresh_token or creds.refresh_token
        row.expires_at = expires_at
        db.commit()
        db.refresh(row)
        return row
    row = GoogleCalendarToken(
        user_id=state,
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
