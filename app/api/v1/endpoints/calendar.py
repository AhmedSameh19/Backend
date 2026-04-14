"""Google Calendar OAuth, connection status, and events for the CRM calendar page."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services import google_calendar_client as gcal

router = APIRouter()
logger = logging.getLogger(__name__)


# --- Schemas ---
class CalendarStatusOut(BaseModel):
    connected: bool = Field(..., description="Whether user has connected Google Calendar")


class GoogleEventOut(BaseModel):
    id: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    start: Optional[Dict[str, Any]] = None
    end: Optional[Dict[str, Any]] = None
    htmlLink: Optional[str] = Field(None, alias="html_link")

    class Config:
        from_attributes = True
        populate_by_name = True


class CreateCalendarEventIn(BaseModel):
    summary: str = Field(..., description="Event title")
    start: str = Field(..., description="ISO datetime e.g. 2026-02-05T14:00:00Z")
    end: str = Field(..., description="ISO datetime e.g. 2026-02-05T15:00:00Z")
    description: Optional[str] = None


def _require_user_id(user_id: Optional[str]) -> str:
    if not user_id or not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id query parameter is required (e.g. from person_id cookie)",
        )
    return user_id.strip()


# --- Endpoints ---
@router.get("/google/connect", tags=["calendar"])
def google_calendar_connect(
    user_id: Optional[str] = Query(None, description="Current user id (e.g. person_id from auth)"),
):
    """
    Redirect to Google OAuth. Frontend should call this with user_id (e.g. from person_id cookie).
    User will be redirected back to GOOGLE_CALENDAR_REDIRECT_URI with ?code=...&state=user_id.
    """
    uid = _require_user_id(user_id)
    url = gcal.get_authorization_url(state=uid)
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=url, status_code=302)


@router.get("/google/callback", tags=["calendar"])
def google_calendar_callback(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    OAuth callback. Exchanges code for tokens and stores them for user (state=user_id).
    Redirects to frontend calendar page.
    """
    if error:
        from fastapi.responses import RedirectResponse
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/calendar?google=error&message={error}",
            status_code=302,
        )
    if not code or not state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing code or state")
    try:
        gcal.exchange_code_for_tokens(code=code, state=state, db=db)
    except Exception as e:
        logger.exception("Google OAuth exchange failed for callback state=%s: %s", state, e)
        from fastapi.responses import RedirectResponse
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}/calendar?google=error&message=exchange_failed",
            status_code=302,
        )
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/calendar?google=connected", status_code=302)


@router.get("/google/status", response_model=CalendarStatusOut, tags=["calendar"])
def google_calendar_status(
    user_id: Optional[str] = Query(None, description="Current user id"),
    db: Session = Depends(get_db),
):
    """Return whether the user has connected their Google Calendar."""
    uid = _require_user_id(user_id)
    try:
        connected = gcal.has_connected_calendar(uid, db)
        return CalendarStatusOut(connected=connected)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Calendar status check failed: {str(e)}",
        )


@router.get("/google/events", response_model=List[GoogleEventOut], tags=["calendar"])
def list_google_calendar_events(
    user_id: Optional[str] = Query(None),
    time_min: Optional[str] = Query(None, description="ISO datetime"),
    time_max: Optional[str] = Query(None, description="ISO datetime"),
    db: Session = Depends(get_db),
):
    """List events from the user's Google Calendar for the given time range."""
    uid = _require_user_id(user_id)
    try:
        dt_min = datetime.fromisoformat(time_min.replace("Z", "+00:00")) if time_min else None
        dt_max = datetime.fromisoformat(time_max.replace("Z", "+00:00")) if time_max else None
    except (ValueError, AttributeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid time_min or time_max (use ISO format e.g. 2026-02-01T00:00:00Z): {e}",
        )
    try:
        items = gcal.list_events(user_id=uid, db=db, time_min=dt_min, time_max=dt_max)
        out = []
        for i in items:
            d = {k: i.get(k) for k in ["id", "summary", "description", "start", "end", "htmlLink"]}
            out.append(GoogleEventOut(**d))
        return out
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list calendar events: {str(e)}",
        )


@router.post("/google/events", response_model=Dict[str, Any], tags=["calendar"])
def create_google_calendar_event(
    payload: CreateCalendarEventIn,
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Create an event in the user's Google Calendar (e.g. company visit)."""
    uid = _require_user_id(user_id)
    try:
        start_dt = datetime.fromisoformat(payload.start.replace("Z", "+00:00"))
        end_dt = datetime.fromisoformat(payload.end.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid start or end datetime (use ISO format): {e}",
        )
    try:
        event = gcal.create_event(
            user_id=uid,
            db=db,
            summary=payload.summary,
            start=start_dt,
            end=end_dt,
            description=payload.description,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create calendar event: {str(e)}",
        )
    if not event:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google Calendar not connected. Connect first via /calendar/google/connect",
        )
    return event
