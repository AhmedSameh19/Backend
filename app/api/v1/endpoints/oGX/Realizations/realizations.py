from fastapi.encoders import jsonable_encoder
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.members import Member
from app.models.leads.expa_lead_realizations import ExpaLeadRealization
from app.schemas.leads.leads import LeadBulkAssignRequest
from app.utils.pagination import PaginatedResponse, PaginationParams, build_pagination_response
from sqlalchemy import desc, asc, func, or_
from typing import Any

router = APIRouter(prefix="/realizations", tags=["Realizations"])


# Retrieve realizations by home LC ID with cursor pagination
# endpoint: /realizations/?home_lc_id={home_lc_id}
@router.get("/", response_model=PaginatedResponse[Any])
def get_realizations(
    home_lc_id: int,
    params: PaginationParams = Depends(),
    db: Session = Depends(get_db),
):
    try:
        if home_lc_id == 1609:
            query = select(ExpaLeadRealization)
        else:
            query = select(ExpaLeadRealization).where(ExpaLeadRealization.home_lc_id == home_lc_id)

        if params.search:
            search_t = f"%{params.search}%"
            query = query.filter(
                or_(
                    ExpaLeadRealization.full_name.ilike(search_t),
                    ExpaLeadRealization.email.ilike(search_t),
                    ExpaLeadRealization.contact_number.ilike(search_t)
                )
            )

        total = db.execute(select(func.count()).select_from(query.subquery())).scalar() or 0

        sort_col = getattr(ExpaLeadRealization, params.sortBy, ExpaLeadRealization.updated_at)
        if params.sortOrder == "desc":
            query = query.order_by(desc(sort_col), ExpaLeadRealization.id.desc())
        else:
            query = query.order_by(asc(sort_col), ExpaLeadRealization.id.asc())

        query = query.offset(params.skip).limit(params.limit)
        items = db.execute(query).scalars().all()

        return build_pagination_response(jsonable_encoder(list(items)), total, params.page, params.limit)
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


# Bulk assign realizations to a member
# endpoint: PATCH /realizations/assign/bulk
# body: {"member_id":"56523","expa_person_ids":["5652633","5653427"]}
@router.patch("/assign/bulk")
def bulk_assign_realizations(
    payload: LeadBulkAssignRequest,
    db: Session = Depends(get_db),
):
    try:
        if not payload.expa_person_ids:
            raise HTTPException(status_code=400, detail="expa_person_ids must not be empty")

        stmt = select(Member).where(Member.expa_person_id == payload.member_id)
        member = db.execute(stmt).scalars().first()


        stmt = select(ExpaLeadRealization.expa_person_id).where(
            ExpaLeadRealization.expa_person_id.in_(payload.expa_person_ids)
        )
        existing_ids = set(db.execute(stmt).scalars().all())

        missing_ids = [epid for epid in payload.expa_person_ids if epid not in existing_ids]
        if not existing_ids:
            raise HTTPException(status_code=404, detail="No realizations found for provided expa_person_ids")

        updated_count = (
            db.query(ExpaLeadRealization)
            .filter(ExpaLeadRealization.expa_person_id.in_(list(existing_ids)))
            .update(
                {
                    ExpaLeadRealization.assigned_member_id: payload.member_id,
                    ExpaLeadRealization.assigned_member_name: member.full_name if member else payload.member_id,
                },
                synchronize_session=False,
            )
        )
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