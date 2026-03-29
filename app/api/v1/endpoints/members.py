from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select, or_, desc, asc
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.members import Member

from app.schemas.members import MemberCreate, MemberOut, OkResponse
from app.services.expa_client import ExpaClient
from app.utils.pagination import PaginatedResponse, PaginationParams, build_pagination_response

router = APIRouter(prefix="/members", tags=["members"])


# Create a new member
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


@router.get("", response_model=PaginatedResponse[MemberOut])
def list_members(params: PaginationParams = Depends(), db: Session = Depends(get_db)) -> PaginatedResponse[MemberOut]:
    try:
        query = select(Member)
        if params.search:
            search_t = f"%{params.search}%"
            query = query.where(or_(Member.full_name.ilike(search_t), Member.email.ilike(search_t)))
        
        total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
        
        sort_col = getattr(Member, params.sortBy, Member.full_name)
        if params.sortOrder == "desc":
            query = query.order_by(desc(sort_col))
        else:
            query = query.order_by(asc(sort_col))
            
        query = query.offset(params.skip).limit(params.limit)
        members = db.execute(query).scalars().all()
        return build_pagination_response(list(members), total, params.page, params.limit)
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database error: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.get("/by-lc/{home_lc_id}", response_model=PaginatedResponse[MemberOut])
def list_members_by_lc(
    home_lc_id: str,
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
) -> PaginatedResponse[MemberOut]:
    try:
        lc_id_str = str(home_lc_id).strip() if home_lc_id else ""
        if not lc_id_str:
            return build_pagination_response([], 0, params.page, params.limit)
        
        query = select(Member)
        if lc_id_str != str(settings.EXPA_HOME_MC_ID):
            query = query.where(Member.home_lc_id == lc_id_str)
        if params.search:
            search_t = f"%{params.search}%"
            query = query.where(or_(Member.full_name.ilike(search_t), Member.email.ilike(search_t)))
        
        total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
        
        sort_col = getattr(Member, params.sortBy, Member.full_name)
        if params.sortOrder == "desc":
            query = query.order_by(desc(sort_col))
        else:
            query = query.order_by(asc(sort_col))
            
        query = query.offset(params.skip).limit(params.limit)
        result = db.execute(query).scalars().all()
        return build_pagination_response(list(result), total, params.page, params.limit)
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


@router.get("/by-lc/{home_lc_id}/reports-to/{reports_to_member_id}", response_model=PaginatedResponse[MemberOut])
def list_members_by_lc_and_reports_to(
    home_lc_id: str,
    reports_to_member_id: str,
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    alt_person_id: str | None = Query(
        None,
        description="Alternate EXPA person id if auth cookie uses a different format than members.expa_person_id",
    ),
) -> PaginatedResponse[MemberOut]:
    try:
        param = (reports_to_member_id or "").strip()
        param_alt = (alt_person_id or "").strip() if alt_person_id else None
        
        # Resolve manager position IDs and person IDs
        manager_position_ids = []
        manager_person_ids = []
        
        for candidate in [param, param_alt]:
            if not candidate:
                continue
            # Try to find the person in our database first
            rows = db.execute(
                select(Member).where(Member.expa_person_id == candidate)
            ).scalars().all()
            if rows:
                manager_position_ids.extend(r.member_id for r in rows)
                manager_person_ids.append(candidate)
            else:
                # Fallback: treat candidate as a position ID (member_id)
                member = db.get(Member, candidate)
                if member:
                    manager_position_ids.append(member.member_id)
                    if member.expa_person_id:
                        manager_person_ids.append(member.expa_person_id)
                else:
                    # If manager not in database, treat candidate as a raw person ID or position ID
                    # We'll search by this raw ID in both columns
                    manager_position_ids.append(candidate)
                    manager_person_ids.append(candidate)

        manager_position_ids = list(dict.fromkeys(manager_position_ids))
        manager_person_ids = list(dict.fromkeys(manager_person_ids))
        
        lc_id_str = str(home_lc_id).strip() if home_lc_id else ""
        if not lc_id_str:
            return build_pagination_response([], 0, params.page, params.limit)
            
        # Search for subordinates by position ID OR the new reports_to_person_id field
        query = select(Member).where(
            or_(
                func.trim(Member.reports_to_member_id).in_(manager_position_ids),
                func.trim(Member.reports_to_person_id).in_(manager_person_ids)
            )
        )
        
        if lc_id_str != str(settings.EXPA_HOME_MC_ID):
            query = query.where(Member.home_lc_id == lc_id_str)
            
        if params.search:
            search_t = f"%{params.search}%"
            query = query.where(or_(Member.full_name.ilike(search_t), Member.email.ilike(search_t)))
            
        total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0
        
        sort_col = getattr(Member, params.sortBy, Member.full_name)
        if params.sortOrder == "desc":
            query = query.order_by(desc(sort_col))
        else:
            query = query.order_by(asc(sort_col))
            
        query = query.offset(params.skip).limit(params.limit)
        result = db.execute(query).scalars().all()
        return build_pagination_response(list(result), total, params.page, params.limit)
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