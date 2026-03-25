from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.members import Member
from app.schemas.members import MemberCreate, MemberOut, OkResponse
from app.services.expa_client import ExpaClient

router = APIRouter(prefix="/members", tags=["members"])


def _aiesec_year_range(today: date) -> tuple[str, str]:
    """AIESEC year: Feb 1 .. Feb 1 (next year). Same as sync task."""
    feb1 = date(today.year, 2, 1)
    if today >= feb1:
        start, end = feb1, date(today.year + 1, 2, 1)
    else:
        start, end = date(today.year - 1, 2, 1), feb1
    return start.isoformat(), end.isoformat()


# Create a new member
#endpoint: /members
#body: {"member_id": "member_123", "member_name": "John Doe"}
@router.post("", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def create_member(payload: MemberCreate, db: Session = Depends(get_db)) -> MemberOut:
    try:
        existing = db.get(Member, payload.member_id)
        if existing:
            raise HTTPException(status_code=409, detail="Member already exists")

        member = Member(member_id=payload.member_id, full_name=payload.full_name)
        db.add(member)
        db.commit()
        db.refresh(member)
        return member
    except HTTPException:
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Member already exists")
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error",
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

#get all of memberss
#endpoint: /members
@router.get("", response_model=List[MemberOut])
def list_members(db: Session = Depends(get_db)) -> List[MemberOut]:
    try:
        members = db.execute(select(Member).order_by(Member.full_name.asc())).scalars().all()
        return members
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )

# Get all members in a specific LC (for assign dropdown fallback when no one reports to you)
# endpoint: /members/by-lc/{home_lc_id}
@router.get("/by-lc/{home_lc_id}", response_model=List[MemberOut])
def list_members_by_lc(
    home_lc_id: str,
    db: Session = Depends(get_db),
) -> List[MemberOut]:
    """Return all members for the given LC. Use as fallback when reports-to returns empty."""
    try:
        lc_id_str = str(home_lc_id).strip() if home_lc_id else ""
        if not lc_id_str:
            return []
        stmt = (
            select(Member)
            .where(Member.home_lc_id == lc_id_str)
            .order_by(Member.full_name.asc())
        )
        result = db.execute(stmt).scalars().all()
        return list(result)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


# Get members in a specific LC that report to a specific member (must be before /{member_id})
# endpoint: /members/by-lc/{home_lc_id}/reports-to/{reports_to_member_id}
@router.get("/by-lc/{home_lc_id}/reports-to/{reports_to_member_id}", response_model=List[MemberOut])
def list_members_by_lc_and_reports_to(
    home_lc_id: str,
    reports_to_member_id: str,
    db: Session = Depends(get_db),
    alt_person_id: str | None = Query(
        None,
        description="Alternate EXPA person id if auth cookie uses a different format than members.expa_person_id",
    ),
) -> List[MemberOut]:
    try:
        # Path param can be EXPA person id or member_id (position id). Find ALL positions for this person.
        param = (reports_to_member_id or "").strip()
        param_alt = (alt_person_id or "").strip() if alt_person_id else None
        my_member_ids = []

        for candidate in [param, param_alt]:
            if not candidate:
                continue
            rows = db.execute(
                select(Member).where(Member.expa_person_id == candidate)
            ).scalars().all()
            my_member_ids.extend(r.member_id for r in rows)
            if not rows:
                member = db.get(Member, candidate)
                if member and member.member_id not in my_member_ids:
                    my_member_ids.append(member.member_id)

        my_member_ids = list(dict.fromkeys(my_member_ids))
        # Also match by raw param(s): EXPA/sync may store reports_to as person id in some rows
        reports_to_candidates = list(my_member_ids)
        for c in [param, param_alt]:
            if c and c not in reports_to_candidates:
                reports_to_candidates.append(c)
        if not reports_to_candidates:
            return []
        lc_id_str = str(home_lc_id).strip() if home_lc_id else ""
        if not lc_id_str:
            return []
        stmt = (
            select(Member)
            .where(Member.home_lc_id == lc_id_str)
            .where(Member.reports_to_member_id.in_(reports_to_candidates))
            .order_by(Member.full_name.asc())
        )
        # .scalars().all() returns list of Member instances for List[MemberOut] serialization
        result = db.execute(stmt).scalars().all()
        return list(result)
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


def _debug_reports_to_impl(
    home_lc_id: str,
    reports_to_member_id: str,
    alt_person_id: str | None,
    db: Session,
) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "requested_id": reports_to_member_id,
        "lc_id": home_lc_id,
        "found_by_expa_person_id": False,
        "found_by_member_id": False,
        "my_member_ids": [],
        "reports_to_candidates": [],
        "subordinates_count": 0,
        "subordinates": [],
        "lc_members_count": 0,
        "distinct_reports_to_in_lc": [],
        "your_ids_found_in_lc_reports_to": False,
    }
    try:
        lc_id_str = str(home_lc_id).strip() if home_lc_id else ""
        if lc_id_str:
            lc_count = db.execute(
                select(func.count()).select_from(Member).where(Member.home_lc_id == lc_id_str)
            ).scalar() or 0
            out["lc_members_count"] = lc_count
            distinct_rt = db.execute(
                select(Member.reports_to_member_id)
                .where(Member.home_lc_id == lc_id_str)
                .where(Member.reports_to_member_id.isnot(None))
                .where(Member.reports_to_member_id != "")
                .distinct()
            ).scalars().all()
            out["distinct_reports_to_in_lc"] = sorted(set(r[0] for r in distinct_rt if r[0]))

        param = (reports_to_member_id or "").strip()
        param_alt = (alt_person_id or "").strip() if alt_person_id else None
        my_member_ids = []

        for candidate in [param, param_alt]:
            if not candidate:
                continue
            rows = db.execute(
                select(Member).where(Member.expa_person_id == candidate)
            ).scalars().all()
            if rows:
                out["found_by_expa_person_id"] = True
                my_member_ids.extend(r.member_id for r in rows)
            if not rows:
                member = db.get(Member, candidate)
                if member:
                    out["found_by_member_id"] = True
                    if member.member_id not in my_member_ids:
                        my_member_ids.append(member.member_id)

        my_member_ids = list(dict.fromkeys(my_member_ids))
        out["my_member_ids"] = my_member_ids
        # Also match by raw param(s) in case EXPA/sync stored person id in reports_to_member_id
        reports_to_candidates = list(my_member_ids)
        for c in [param, param_alt]:
            if c and c not in reports_to_candidates:
                reports_to_candidates.append(c)
        out["reports_to_candidates"] = reports_to_candidates
        distinct_set = set(out.get("distinct_reports_to_in_lc") or [])
        out["your_ids_found_in_lc_reports_to"] = any(c in distinct_set for c in reports_to_candidates)

        if not reports_to_candidates:
            return out

        if not lc_id_str:
            return out

        stmt = (
            select(Member)
            .where(Member.home_lc_id == lc_id_str)
            .where(Member.reports_to_member_id.in_(reports_to_candidates))
            .order_by(Member.full_name.asc())
        )
        result = db.execute(stmt).scalars().all()
        out["subordinates_count"] = len(result)
        out["subordinates"] = [
            {"member_id": r.member_id, "expa_person_id": r.expa_person_id, "full_name": r.full_name, "role": r.role}
            for r in result
        ]
        return out
    except Exception as e:
        out["error"] = str(e)
        return out


# Debug: same URL as the real endpoint but with /debug suffix so it's not matched by /{member_id}
@router.get("/by-lc/{home_lc_id}/reports-to/{reports_to_member_id}/debug", response_model=Dict[str, Any])
def debug_reports_to_suffix(
    home_lc_id: str,
    reports_to_member_id: str,
    db: Session = Depends(get_db),
    alt_person_id: str | None = Query(None, description="Alternate person/member id to try"),
) -> Dict[str, Any]:
    """
    Debug: run the same lookup as by-lc/.../reports-to and return what was found.
    Use this to verify members table has your positions and subordinates.
    """
    return _debug_reports_to_impl(home_lc_id, reports_to_member_id, alt_person_id, db)


@router.get("/debug/by-lc/{home_lc_id}/reports-to/{reports_to_member_id}", response_model=Dict[str, Any])
def debug_reports_to(
    home_lc_id: str,
    reports_to_member_id: str,
    db: Session = Depends(get_db),
    alt_person_id: str | None = Query(None, description="Alternate person/member id to try"),
) -> Dict[str, Any]:
    """Debug: same as .../reports-to/{id}/debug (alternative path)."""
    return _debug_reports_to_impl(home_lc_id, reports_to_member_id, alt_person_id, db)


@router.get("/me/reports", response_model=List[MemberOut])
def list_my_reports(request: Request, db: Session = Depends(get_db)) -> List[MemberOut]:
    """
    Return only members who report to the currently authenticated user (EXPA token).
    Use this for assign dropdowns so the list is strictly "who reports to me", not all LC.
    """
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    token = auth[7:].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    api_url = getattr(settings, "AIESEC_API_URL", None)
    if not api_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="EXPA API not configured")
    client = ExpaClient(api_url=api_url, api_token=f"Bearer {token}", timeout_seconds=30)
    try:
        current = client.fetch_current_person()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"EXPA current_person failed: {e!s}")
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current person not found")
    home_lc = current.get("home_lc") or {}
    lc_id = home_lc.get("id")
    if lc_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User has no home_lc")
    lc_id_str = str(lc_id)
    full_name = (current.get("full_name") or "").strip()
    from_date, to_date = _aiesec_year_range(date.today())
    try:
        positions = client.fetch_members(home_lc_id=int(lc_id), from_date=from_date, to_date=to_date)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"EXPA member positions failed: {e!s}")
    person_id = None
    for pos in positions or []:
        person = pos.get("person") or {}
        if (person.get("full_name") or "").strip() == full_name:
            pid = person.get("id")
            if pid is not None:
                person_id = str(pid)
                break
    if not person_id:
        return []
    rows = db.execute(
        select(Member).where(Member.expa_person_id == person_id)
    ).scalars().all()
    my_member_ids = [r.member_id for r in rows]
    if not my_member_ids:
        member = db.get(Member, person_id)
        if member:
            my_member_ids = [member.member_id]
    if not my_member_ids:
        return []
    stmt = (
        select(Member)
        .where(Member.home_lc_id == lc_id_str)
        .where(Member.reports_to_member_id.in_(my_member_ids))
        .order_by(Member.full_name.asc())
    )
    return list(db.execute(stmt).scalars().all())


@router.get("/me/sync-person-id", status_code=status.HTTP_200_OK)
def get_my_sync_person_id(request: Request):
    """
    Resolve the current user's person id in the format stored by the sync (EXPA member positions).
    Call with Authorization: Bearer <expa_access_token>. Returns the person id to use as alt_person_id
    when the auth cookie uses a different format (e.g. global id).
    """
    auth = request.headers.get("Authorization") or ""
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid Authorization header")
    token = auth[7:].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Bearer token")
    api_url = getattr(settings, "AIESEC_API_URL", None)
    if not api_url:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="EXPA API not configured")
    client = ExpaClient(api_url=api_url, api_token=f"Bearer {token}", timeout_seconds=30)
    try:
        current = client.fetch_current_person()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"EXPA current_person failed: {e!s}")
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Current person not found")
    home_lc = (current.get("home_lc") or {})
    lc_id = home_lc.get("id")
    if lc_id is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User has no home_lc")
    full_name = (current.get("full_name") or "").strip()
    from_date, to_date = _aiesec_year_range(date.today())
    try:
        positions = client.fetch_members(home_lc_id=int(lc_id), from_date=from_date, to_date=to_date)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"EXPA member positions failed: {e!s}")
    for pos in positions or []:
        person = pos.get("person") or {}
        if (person.get("full_name") or "").strip() == full_name:
            pid = person.get("id")
            if pid is not None:
                return {"sync_person_id": str(pid)}
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching position in member list")


#get member by id
#endpoint: /members/{member_id}
@router.get("/{member_id}", response_model=MemberOut)
def get_member(member_id: str, db: Session = Depends(get_db)) -> MemberOut:
    try:
        member = db.get(Member, member_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")
        return member
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error",
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
    
# Delete a member by id
#endpoint: /members/{member_id}
@router.delete("/{member_id}", response_model=OkResponse, status_code=status.HTTP_200_OK)
def delete_member(member_id: str, db: Session = Depends(get_db)) -> OkResponse:
    try:
        member = db.get(Member, member_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        db.delete(member)
        db.commit()
        return OkResponse(ok=True)
    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database error",
        )
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
