from app.models.b2c.b2c_comments import B2CComment
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
import logging

from app.models.members import Member

from app.db.session import get_db

from app.schemas.b2c.comments import CommentCreate, CommentResponse
router = APIRouter(prefix="/b2c", tags=["B2C"])

logger = logging.getLogger(__name__)


# Add a comment to a lead
#endpoint: /b2c/{expa_person_id}/comments
#Example request body: {"text": "This is a comment", "created_by": "member_123"}
@router.post("/{expa_person_id}/comments", response_model=CommentResponse)
def add_comment(
    expa_person_id: str,
    payload: CommentCreate,
    db: Session = Depends(get_db),
) -> CommentResponse:
    try:
        member = (
            db.execute(select(Member).where(Member.expa_person_id == payload.created_by))
            .scalars()
            .first()
        )


        # TODO: implement real authorization check; for now don't block all valid members
        # if not member.is_authorized_for_b2c:
        #     raise HTTPException(status_code=403, detail="Not authorized")

        comment = B2CComment(
            expa_person_id=expa_person_id,
            comment=payload.text,
            creator_name=member.full_name if member else payload.created_by,
        )

        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment

    except HTTPException:
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("DB error in add_comment (expa_person_id=%s)", expa_person_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error") from e
    except Exception as e:
        db.rollback()
        logger.exception("Unexpected error in add_comment (expa_person_id=%s)", expa_person_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e


# Retrieve comments for a lead
# endpoint: /b2c/{expa_person_id}/comments
@router.get("/{expa_person_id}/comments", response_model=list[CommentResponse])
def get_comments(expa_person_id: str, db: Session = Depends(get_db)) -> list[CommentResponse]:
    try:
        stmt = (
            select(B2CComment)
            .where(B2CComment.expa_person_id == expa_person_id)
            .order_by(B2CComment.created_at.desc())
        )
        return db.execute(stmt).scalars().all()
    except SQLAlchemyError as e:
        logger.exception("DB error in get_comments (expa_person_id=%s)", expa_person_id)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error") from e
    except Exception as e:
        logger.exception("Unexpected error in get_comments (expa_person_id=%s)", expa_person_id)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error") from e

# Delete a comment from a lead
# endpoint: /b2c/{expa_person_id}/comments/{comment_id}
@router.delete(
    "/{expa_person_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_comment(
    expa_person_id: str,
    comment_id: int,
    db: Session = Depends(get_db),
) -> Response:
    try:
        comment = db.get(B2CComment, comment_id)
        if not comment or comment.expa_person_id != expa_person_id:
            raise HTTPException(status_code=404, detail="Comment not found")

        db.delete(comment)
        db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
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