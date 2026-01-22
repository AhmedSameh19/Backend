from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.members import Member

from app.schemas.members import MemberCreate, MemberOut, OkResponse

router = APIRouter(prefix="/members", tags=["members"])


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
    
# Get members in a specific LC that report to a specific member
# endpoint: /members/by-lc/{home_lc_id}/reports-to/{reports_to_member_id}
@router.get("/by-lc/{home_lc_id}/reports-to/{reports_to_member_id}", response_model=List[MemberOut])
def list_members_by_lc_and_reports_to(
    home_lc_id: str,
    reports_to_member_id: str,
    db: Session = Depends(get_db),
) -> List[MemberOut]:
    try:
        # The path param may be an EXPA person id; resolve it to our member_id.
        member = (
            db.execute(select(Member).where(Member.expa_person_id == reports_to_member_id))
            .scalars()
            .first()
        )
        if not member:
            # Fallback: treat it as our PK (member_id)
            member = db.get(Member, reports_to_member_id)
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        stmt = (
            select(Member)
            .where(Member.home_lc_id == home_lc_id)
            .where(Member.reports_to_member_id == member.member_id)
            .order_by(Member.full_name.asc())
        )
        return db.execute(stmt).scalars().all()
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
