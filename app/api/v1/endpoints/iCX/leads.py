from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import logging

from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, tuple_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.icx.expa_icx_leads import ExpaICXLead
from app.models.members import Member
from app.schemas.icx.leads import ICXLeadBulkAssignRequest
from app.utils.pagination import PaginatedResponse, PaginationParams, build_pagination_response
from sqlalchemy import or_, desc, asc, func
from typing import Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/icx/leads", tags=["iCX Leads"])


@router.get("/", response_model=PaginatedResponse[Any])
def get_icx_leads(
    host_lc_id: str,
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    try:
        # Special case: treat 1609 as "all leads"
        if str(host_lc_id) == "1609":
            query = select(ExpaICXLead)
        else:
            query = select(ExpaICXLead).filter(ExpaICXLead.host_lc_id == host_lc_id)

        if params.search:
            search_t = f"%{params.search}%"
            query = query.filter(
                or_(
                    ExpaICXLead.full_name.ilike(search_t),
                    ExpaICXLead.email.ilike(search_t),
                    ExpaICXLead.phone.ilike(search_t)
                )
            )

        total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0

        sort_col = getattr(ExpaICXLead, params.sortBy, ExpaICXLead.created_at)
        if params.sortOrder == "desc":
            query = query.order_by(desc(sort_col), ExpaICXLead.application_id.desc())
        else:
            query = query.order_by(asc(sort_col), ExpaICXLead.application_id.asc())

        query = query.offset(params.skip).limit(params.limit)
        items = db.execute(query).scalars().all()

        return build_pagination_response(jsonable_encoder(list(items)), total, params.page, params.limit)
    except SQLAlchemyError as e:
        logger.exception("DB error in get_icx_leads(host_lc_id=%s)", host_lc_id)
        raise HTTPException(status_code=503, detail="Database error") from e
    except Exception as e:
        logger.exception("Unexpected error in get_icx_leads(host_lc_id=%s)", host_lc_id)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/assign/bulk")
def bulk_assign_icx_leads(
    payload: ICXLeadBulkAssignRequest,
    db: Session = Depends(get_db),
):
    try:
        if not payload.application_ids:
            raise HTTPException(status_code=400, detail="application_ids must not be empty")

        member_id = str(payload.member_id)
        application_ids = [str(x) for x in payload.application_ids]

        member = db.execute(select(Member).where(Member.expa_person_id == member_id)).scalars().first()


        stmt = select(ExpaICXLead.application_id).where(ExpaICXLead.application_id.in_(application_ids))
        existing_ids = set(db.execute(stmt).scalars().all())

        missing_ids = [aid for aid in application_ids if aid not in existing_ids]
        if not existing_ids:
            raise HTTPException(status_code=404, detail="No iCX leads found for provided application_ids")

        updated_count = (
            db.query(ExpaICXLead)
            .filter(ExpaICXLead.application_id.in_(list(existing_ids)))
            .update(
                {
                    ExpaICXLead.assigned_member_id: member.expa_person_id if member else None,
                    ExpaICXLead.assigned_member_name: member.full_name if member else payload.member_id,
                },
                synchronize_session=False,
            )
        )

        db.commit()

        return {
            "ok": True,
            "assigned_to": {"member_id": member_id, "member_name": member.full_name if member else payload.member_id},
            "requested": len(application_ids),
            "updated": int(updated_count or 0),
            "missing_application_ids": missing_ids,
        }
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception(
            "DB error in bulk_assign_icx_leads(member_id=%s, application_ids=%s)",
            payload.member_id,
            len(payload.application_ids),
        )
        raise HTTPException(status_code=503, detail="Database error") from e
    except Exception as e:
        db.rollback()
        logger.exception(
            "Unexpected error in bulk_assign_icx_leads(member_id=%s, application_ids=%s)",
            payload.member_id,
            len(payload.application_ids),
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e

@router.get("/{application_id}")
def get_icx_lead(
    application_id: str,
    db: Session = Depends(get_db),
):
    try:
        lead = db.get(ExpaICXLead, application_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return lead
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database error")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")
