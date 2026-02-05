from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.icx.expa_icx_lead_comments import ExpaICXLeadComment
from app.models.icx.expa_icx_leads import ExpaICXLead
from app.models.members import Member
from app.schemas.icx.comments import ICXCommentCreate, ICXCommentOut

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/icx/leads", tags=["iCX Leads"])


@router.post("/{application_id}/comments", response_model=ICXCommentOut)
def add_icx_comment(
    application_id: str,
    payload: ICXCommentCreate,
    db: Session = Depends(get_db),
) -> ICXCommentOut:
    try:
        lead = db.get(ExpaICXLead, str(application_id))
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        member = db.execute(select(Member).where(Member.expa_person_id == payload.created_by)).scalars().first()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        comment = ExpaICXLeadComment(
            application_id=str(application_id),
            comment=payload.text,
            creator_name=member.full_name,
        )

        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("DB error in add_icx_comment(application_id=%s)", application_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error") from e
    except Exception as e:
        db.rollback()
        logger.exception("Unexpected error in add_icx_comment(application_id=%s)", application_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


@router.get("/{application_id}/comments", response_model=list[ICXCommentOut])
def get_icx_comments(application_id: str, db: Session = Depends(get_db)) -> list[ICXCommentOut]:
    try:
        stmt = (
            select(ExpaICXLeadComment)
            .where(ExpaICXLeadComment.application_id == str(application_id))
            .order_by(ExpaICXLeadComment.created_at.desc(), ExpaICXLeadComment.id.desc())
        )
        return db.execute(stmt).scalars().all()
    except SQLAlchemyError as e:
        logger.exception("DB error in get_icx_comments(application_id=%s)", application_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error") from e
    except Exception as e:
        logger.exception("Unexpected error in get_icx_comments(application_id=%s)", application_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


@router.delete(
    "/{application_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_icx_comment(application_id: str, comment_id: int, db: Session = Depends(get_db)) -> Response:
    try:
        comment = db.get(ExpaICXLeadComment, comment_id)
        if not comment or comment.application_id != str(application_id):
            raise HTTPException(status_code=404, detail="Comment not found")

        db.delete(comment)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception(
            "DB error in delete_icx_comment(application_id=%s, comment_id=%s)",
            application_id,
            comment_id,
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error") from e
    except Exception as e:
        db.rollback()
        logger.exception(
            "Unexpected error in delete_icx_comment(application_id=%s, comment_id=%s)",
            application_id,
            comment_id,
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e
