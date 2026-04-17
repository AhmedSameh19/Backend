from __future__ import annotations

import logging

from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.icx.expa_icx_realizations import ExpaICXRealization
from app.models.members import Member
from app.schemas.icx.leads import ICXLeadBulkAssignRequest
from app.utils.pagination import PaginatedResponse, PaginationParams, build_pagination_response
from sqlalchemy import desc, asc, func, or_
from typing import Any

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/icx/realizations", tags=["iCX Realizations"])


@router.get("/", response_model=PaginatedResponse[Any])
def get_icx_realizations(
    host_lc_id: str,
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    try:
        if str(host_lc_id) == "1609":
            query = select(ExpaICXRealization)
        else:
            query = select(ExpaICXRealization).where(ExpaICXRealization.host_lc_id == str(host_lc_id))

        if params.search:
            search_t = f"%{params.search}%"
            query = query.filter(
                or_(
                    ExpaICXRealization.full_name.ilike(search_t),
                    ExpaICXRealization.email.ilike(search_t),
                    ExpaICXRealization.contact_number.ilike(search_t)
                )
            )

        total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0

        # sort logic
        sort_col = getattr(ExpaICXRealization, params.sortBy, ExpaICXRealization.date_realized)
        if params.sortOrder == "desc":
            query = query.order_by(desc(sort_col).nullslast(), ExpaICXRealization.application_id.desc())
        else:
            query = query.order_by(asc(sort_col).nullsfirst(), ExpaICXRealization.application_id.asc())

        query = query.offset(params.skip).limit(params.limit)
        items = db.execute(query).scalars().all()

        return build_pagination_response(jsonable_encoder(list(items)), total, params.page, params.limit)
    except SQLAlchemyError as e:
        logger.exception("DB error in get_icx_realizations(host_lc_id=%s)", host_lc_id)
        raise HTTPException(status_code=503, detail="Database error") from e
    except Exception as e:
        logger.exception("Unexpected error in get_icx_realizations(host_lc_id=%s)", host_lc_id)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/assign/bulk")
def bulk_assign_icx_realizations(
    payload: ICXLeadBulkAssignRequest,
    db: Session = Depends(get_db),
):
    try:
        if not payload.application_ids:
            raise HTTPException(status_code=400, detail="application_ids must not be empty")

        member_id = str(payload.member_id)
        application_ids = [str(x) for x in payload.application_ids]

        member = db.execute(select(Member).where(Member.expa_person_id == member_id)).scalars().first()


        stmt = select(ExpaICXRealization.application_id).where(ExpaICXRealization.application_id.in_(application_ids))
        existing_ids = set(db.execute(stmt).scalars().all())

        missing_ids = [aid for aid in application_ids if aid not in existing_ids]
        if not existing_ids:
            raise HTTPException(status_code=404, detail="No iCX realizations found for provided application_ids")

        updated_count = (
            db.query(ExpaICXRealization)
            .filter(ExpaICXRealization.application_id.in_(list(existing_ids)))
            .update(
                {
                    ExpaICXRealization.assigned_member_id: member_id,
                    ExpaICXRealization.assigned_member_name: member.full_name if member else member_id,
                },
                synchronize_session=False,
            )
        )

        db.commit()

        return {
            "ok": True,
            "assigned_to": {"member_id": member_id, "member_name": member.full_name if member else member_id},
            "requested": len(application_ids),
            "updated": int(updated_count or 0),
            "missing_application_ids": missing_ids,
        }
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception(
            "DB error in bulk_assign_icx_realizations(member_id=%s, application_ids=%s)",
            payload.member_id,
            len(payload.application_ids),
        )
        raise HTTPException(status_code=503, detail="Database error") from e
    except Exception as e:
        db.rollback()
        logger.exception(
            "Unexpected error in bulk_assign_icx_realizations(member_id=%s, application_ids=%s)",
            payload.member_id,
            len(payload.application_ids),
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e
