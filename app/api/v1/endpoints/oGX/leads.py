from datetime import datetime
from typing import Any, Dict, Optional
import logging 

from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, tuple_
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db
from app.models.leads.expa_leads import ExpaLead
from app.models.members import Member

from app.schemas.leads.leads import LeadAssignRequest, LeadBulkAssignRequest
from app.utils.pagination import PaginatedResponse, PaginationParams, build_pagination_response
from sqlalchemy import or_, desc, asc, func

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/leads", tags=["Leads"])

## Retrieve leads by home LC ID with pagination
#endpoint: /leads/?home_lc_id={home_lc_id}
@router.get("/", response_model=PaginatedResponse[Any])
def get_leads(
    home_lc_id: int,
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    try:
        # Special case: treat 1609 as "all leads" (no LC filtering)
        if home_lc_id == 1609:
            query = select(ExpaLead)
        else:
            query = select(ExpaLead).filter(ExpaLead.home_lc_id == home_lc_id)

        if params.search:
            search_t = f"%{params.search}%"
            query = query.filter(
                or_(
                    ExpaLead.full_name.ilike(search_t),
                    ExpaLead.email.ilike(search_t),
                    ExpaLead.phone.ilike(search_t)
                )
            )

        total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0

        sort_col = getattr(ExpaLead, params.sortBy, ExpaLead.created_at)
        if params.sortOrder == "desc":
            query = query.order_by(desc(sort_col), ExpaLead.expa_person_id.desc())
        else:
            query = query.order_by(asc(sort_col), ExpaLead.expa_person_id.asc())
            
        query = query.offset(params.skip).limit(params.limit)
        items = db.execute(query).scalars().all()

        return build_pagination_response(jsonable_encoder(list(items)), total, params.page, params.limit)
    except SQLAlchemyError as e:
        logger.exception("DB error in get_leads(home_lc_id=%s)", home_lc_id)
        raise HTTPException(status_code=503, detail="Database error") from e
    except Exception as e:
        logger.exception("Unexpected error in get_leads(home_lc_id=%s)", home_lc_id)
        raise HTTPException(status_code=500, detail="Internal server error") from e

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
                    ExpaLead.assigned_member_id: member.expa_person_id if member else None,
                    ExpaLead.assigned_member_name: member.full_name if member else payload.member_id,
                },
                synchronize_session=False,
            )
        )
        print(updated_count)
        db.commit()

        return {
            "ok": True,
            "assigned_to": {"member_id": payload.member_id, "member_name": member.full_name if member else payload.member_id},
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


        lead.assigned_member_id = member.expa_person_id if member else None
        lead.assigned_member_name = member.full_name if member else payload.member_id

        db.commit()
        db.refresh(lead)

        return {
            "ok": True,
            "assigned_to": {
                "member_id": payload.member_id,
                "member_name": member.full_name if member else payload.member_id,
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