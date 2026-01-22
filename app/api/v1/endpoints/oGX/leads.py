from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, tuple_
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.models.leads.expa_leads import ExpaLead
from app.models.members import Member

from app.schemas.leads.leads import LeadAssignRequest, LeadBulkAssignRequest

router = APIRouter(prefix="/leads", tags=["Leads"])

## Retrieve leads by home LC ID with pagination
#endpoint: /leads/?home_lc_id={home_lc_id}
@router.get("/")
def get_leads(
    home_lc_id: int,
    cursor_created_at: Optional[datetime] = None,
    cursor_expa_person_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    try:
        if limit <= 0:
            raise HTTPException(status_code=400, detail="limit must be > 0")

        if (cursor_created_at is None) != (cursor_expa_person_id is None):
            raise HTTPException(
                status_code=400,
                detail="cursor_created_at and cursor_expa_person_id must be provided together",
            )

        query = db.query(ExpaLead).filter(ExpaLead.home_lc_id == home_lc_id)
        query = query.order_by(ExpaLead.created_at.desc(), ExpaLead.expa_person_id.desc())

        if cursor_created_at is not None and cursor_expa_person_id is not None:
            query = query.filter(
                tuple_(ExpaLead.created_at, ExpaLead.expa_person_id)
                < (cursor_created_at, cursor_expa_person_id)
            )
        elif skip:
            # Backward-compatible offset pagination (less efficient for large offsets)
            query = query.offset(skip)

        # Fetch one extra row to know if there is a next page.
        items = query.limit(limit + 1).all()
        next_cursor: Optional[Dict[str, Any]] = None
        if len(items) > limit:
            items = items[:limit]
            last = items[-1]
            next_cursor = {
                "created_at": last.created_at.isoformat(),
                "expa_person_id": last.expa_person_id,
            }

        return {"items": items, "next_cursor": next_cursor}
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database error")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

# NEW: Bulk assign leads to a member
# endpoint: PATCH /leads/assign/bulk
# body: {"member_id":"member_123","expa_person_ids":["5652633","5653427"]}
@router.patch("/assign/bulk")
def bulk_assign_leads(
    payload: LeadBulkAssignRequest,
    db: Session = Depends(get_db),
):
    try:
        if not payload.expa_person_ids:
            raise HTTPException(status_code=400, detail="expa_person_ids must not be empty")

        stmt = (
                select(Member)
                .where(Member.expa_person_id == payload.member_id)
            )
        member = db.execute(stmt).scalars().first()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        stmt = select(ExpaLead.expa_person_id).where(ExpaLead.expa_person_id.in_(payload.expa_person_ids))
        existing_ids = set(db.execute(stmt).scalars().all())

        missing_ids = [epid for epid in payload.expa_person_ids if epid not in existing_ids]
        if not existing_ids:
            raise HTTPException(status_code=404, detail="No leads found for provided expa_person_ids")

        updated_count = (
            db.query(ExpaLead)
            .filter(ExpaLead.expa_person_id.in_(list(existing_ids)))
            .update(
                {
                    ExpaLead.assigned_member_id: payload.member_id,
                    ExpaLead.assigned_member_name: member.full_name,
                },
                synchronize_session=False,
            )
        )
        print(updated_count)
        db.commit()

        return {
            "ok": True,
            "assigned_to": {"member_id": payload.member_id, "member_name": member.full_name},
            "requested": len(payload.expa_person_ids),
            "updated": int(updated_count or 0),
            "missing_expa_person_ids": missing_ids,
        }
    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Database error")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


## Retrieve a lead by expa_person_id for lead profile view
#endpoint: /leads/{expa_person_id}
@router.get("/{expa_person_id}")
def get_lead(
    expa_person_id: str,
    db: Session = Depends(get_db),
):
    try:
        lead = db.get(ExpaLead, expa_person_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return lead
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database error")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")


###################################################################


##Can be removed later and only keep the bulk assign endpoint

## Assign a lead to a member
#Example request body: {"member_id": "member_123"}
#endpoint: /leads/{expa_person_id}/assign
@router.patch("/{expa_person_id}/assign")
def assign_lead(
    expa_person_id: str,
    payload: LeadAssignRequest,
    db: Session = Depends(get_db),
):
    try:
        lead = db.get(ExpaLead, expa_person_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        stmt = (
            select(Member)
            .where(Member.expa_person_id == payload.created_by)
        )
        member = db.execute(stmt).scalars().first()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        lead.assigned_member_id = payload.member_id
        lead.assigned_member_name = member.full_name

        db.commit()
        db.refresh(lead)

        return {
            "ok": True,
            "assigned_to": {
                "member_id": payload.member_id,
                "member_name": member.full_name,
            },
        }
    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Database error")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")