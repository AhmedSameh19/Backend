# Backend API updates (for Frontend team)

Base URL: `http://localhost:8000/api/v1` (or your deployed API base).

---

## Market Research

### New fields on IGV & B2B records
- **status**: `"lead"` | `"contacted"` | `"visited"` (default: `"lead"`)
- **visit_date**: optional datetime (when status is `visited`)

### New endpoints

| Method | Path | Description | Body / Params |
|--------|------|-------------|----------------|
| **GET** | `/market-research/scheduled-visits` | List IGV & B2B records that have a visit date set (for calendar) | — |
| **PATCH** | `/market-research/igv/{id}` | Update IGV status and/or visit_date | `{"status": "contacted"}` or `{"status": "visited", "visit_date": "2026-02-20T10:00:00Z"}` |
| **PATCH** | `/market-research/b2b/{id}` | Update B2B status and/or visit_date | Same as above |

`{id}` = database primary key of the IGV or B2B record.

---

## Google Calendar

All calendar endpoints require **user_id** as query param (e.g. from `person_id` cookie).

| Method | Path | Description | Body / Params |
|--------|------|-------------|----------------|
| **GET** | `/calendar/google/connect?user_id=...` | Redirects user to Google OAuth (open in browser) | — |
| **GET** | `/calendar/google/callback` | OAuth callback (handled by redirect from Google) | — |
| **GET** | `/calendar/google/status?user_id=...` | Check if user has connected Google Calendar | Returns `{"connected": true\|false}` |
| **GET** | `/calendar/google/events?user_id=...` | List events from user's Google Calendar | Optional: `time_min`, `time_max` (ISO datetime) |
| **POST** | `/calendar/google/events?user_id=...` | Create event in user's Google Calendar | `{"summary": "...", "start": "ISO", "end": "ISO", "description": "..."}` |

Env vars required for Google Calendar: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_CALENDAR_REDIRECT_URI`.
