from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.icx.expa_icx_lead_followups import ExpaICXLeadFollowUp
from app.models.icx.expa_icx_leads import ExpaICXLead
from app.models.members import Member
from app.schemas.icx.followups import ICXFollowUpCreate, ICXFollowUpOut, ICXFollowUpStatusUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/icx/leads", tags=["iCX Leads"])


@router.get(
    "/followups/created_by/{created_by_member_id}",
    response_model=list[ICXFollowUpOut],
    status_code=status.HTTP_200_OK,
)
def get_icx_followups_by_member(
    created_by_member_id: str,
    db: Session = Depends(get_db),
) -> list[ICXFollowUpOut]:
    try:
        stmt = (
            select(ExpaICXLeadFollowUp)
            .where(ExpaICXLeadFollowUp.created_by_member_id == created_by_member_id)
            .order_by(
                ExpaICXLeadFollowUp.follow_up_at.desc(),
                ExpaICXLeadFollowUp.created_at.desc(),
                ExpaICXLeadFollowUp.id.desc(),
            )
        )
        return db.execute(stmt).scalars().all()
    except SQLAlchemyError as e:
        logger.exception("DB error in get_icx_followups_by_member(created_by_member_id=%s)", created_by_member_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error") from e
    except Exception as e:
        logger.exception(
            "Unexpected error in get_icx_followups_by_member(created_by_member_id=%s)",
            created_by_member_id,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


@router.post("/{created_by}/followups", response_model=ICXFollowUpOut)
def create_icx_followup(
    created_by: str,
    payload: ICXFollowUpCreate,
    db: Session = Depends(get_db),
) -> ICXFollowUpOut:
    now = datetime.now(timezone.utc)
    follow_up_at = payload.follow_up_at
    if follow_up_at.tzinfo is None:
        follow_up_at = follow_up_at.replace(tzinfo=timezone.utc)
    if follow_up_at <= now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="follow_up_at must be in the future")

    try:
        lead = db.get(ExpaICXLead, str(payload.application_id))
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        created_by_member_id = None
        created_by_member_name = None
        if created_by is not None:
            member = db.execute(select(Member).where(Member.expa_person_id == created_by)).scalars().first()

            created_by_member_id = member.expa_person_id if member else None
            created_by_member_name = member.full_name if member else created_by

        followup = ExpaICXLeadFollowUp(
            application_id=str(payload.application_id),
            follow_up_text=payload.follow_up_text,
            follow_up_at=follow_up_at,
            status="pending",
            created_by_member_id=created_by_member_id,
            created_by_member_name=created_by_member_name,
            created_at=now,
        )

        db.add(followup)
        db.commit()
        db.refresh(followup)
        return followup

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("DB error in create_icx_followup(application_id=%s)", application_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error") from e
    except Exception as e:
        db.rollback()
        logger.exception("Unexpected error in create_icx_followup(application_id=%s)", application_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


@router.get("/{application_id}/followups", response_model=list[ICXFollowUpOut])
def list_icx_followups(application_id: str, db: Session = Depends(get_db)) -> list[ICXFollowUpOut]:
    try:
        stmt = (
            select(ExpaICXLeadFollowUp)
            .where(ExpaICXLeadFollowUp.application_id == str(application_id))
            .order_by(
                ExpaICXLeadFollowUp.follow_up_at.desc(),
                ExpaICXLeadFollowUp.created_at.desc(),
                ExpaICXLeadFollowUp.id.desc(),
            )
        )
        return db.execute(stmt).scalars().all()
    except SQLAlchemyError as e:
        logger.exception("DB error in list_icx_followups(application_id=%s)", application_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error") from e
    except Exception as e:
        logger.exception("Unexpected error in list_icx_followups(application_id=%s)", application_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


@router.patch("/{application_id}/followups/{followup_id}/status", response_model=ICXFollowUpOut)
def update_icx_followup_status(
    application_id: str,
    followup_id: int,
    payload: ICXFollowUpStatusUpdate,
    db: Session = Depends(get_db),
) -> ICXFollowUpOut:
    try:
        followup = db.get(ExpaICXLeadFollowUp, followup_id)
        if not followup or followup.application_id != str(application_id):
            raise HTTPException(status_code=404, detail="Follow-up not found")

        followup.status = payload.status
        db.commit()
        db.refresh(followup)
        return followup

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception(
            "DB error in update_icx_followup_status(application_id=%s, followup_id=%s)",
            application_id,
            followup_id,
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error") from e
    except Exception as e:
        db.rollback()
        logger.exception(
            "Unexpected error in update_icx_followup_status(application_id=%s, followup_id=%s)",
            application_id,
            followup_id,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


@router.delete(
    "/{application_id}/followups/{followup_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_icx_followup(application_id: str, followup_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        followup = db.get(ExpaICXLeadFollowUp, followup_id)
        if not followup or followup.application_id != str(application_id):
            raise HTTPException(status_code=404, detail="Follow-up not found")

        db.delete(followup)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception(
            "DB error in delete_icx_followup(application_id=%s, followup_id=%s)",
            application_id,
            followup_id,
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error") from e
    except Exception as e:
        db.rollback()
        logger.exception(
            "Unexpected error in delete_icx_followup(application_id=%s, followup_id=%s)",
            application_id,
            followup_id,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e
