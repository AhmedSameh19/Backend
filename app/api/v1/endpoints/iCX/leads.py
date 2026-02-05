from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, tuple_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.icx.expa_icx_leads import ExpaICXLead
from app.models.members import Member
from app.schemas.icx.leads import ICXLeadBulkAssignRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/icx/leads", tags=["iCX Leads"])


@router.get("/")
def get_icx_leads(
    host_lc_id: str,
    cursor_created_at: Optional[datetime] = None,
    cursor_application_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    try:
        if limit <= 0:
            raise HTTPException(status_code=400, detail="limit must be > 0")

        if (cursor_created_at is None) != (cursor_application_id is None):
            raise HTTPException(
                status_code=400,
                detail="cursor_created_at and cursor_application_id must be provided together",
            )

        # Special case: treat 1609 as "all leads"
        if str(host_lc_id) == "1609":
            query = db.query(ExpaICXLead)
        else:
            query = db.query(ExpaICXLead).filter(ExpaICXLead.host_lc_id == host_lc_id)

        query = query.order_by(ExpaICXLead.created_at.desc(), ExpaICXLead.application_id.desc())

        if cursor_created_at is not None and cursor_application_id is not None:
            query = query.filter(
                tuple_(ExpaICXLead.created_at, ExpaICXLead.application_id) < (cursor_created_at, cursor_application_id)
            )
        elif skip:
            query = query.offset(skip)

        items = query.limit(limit + 1).all()
        next_cursor: Optional[Dict[str, Any]] = None
        if len(items) > limit:
            items = items[:limit]
            last = items[-1]
            next_cursor = {
                "created_at": last.created_at.isoformat() if last.created_at else None,
                "application_id": last.application_id,
            }

        return {"items": items, "next_cursor": next_cursor}
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
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

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
                    ExpaICXLead.assigned_member_id: member_id,
                    ExpaICXLead.assigned_member_name: member.full_name,
                },
                synchronize_session=False,
            )
        )

        db.commit()

        return {
            "ok": True,
            "assigned_to": {"member_id": member_id, "member_name": member.full_name},
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
