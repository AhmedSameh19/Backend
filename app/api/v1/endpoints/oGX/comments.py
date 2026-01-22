from app.models.leads.expa_lead_comments import ExpaLeadComment
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.members import Member

from app.db.session import get_db

from app.schemas.leads.comments import CommentCreate, CommentResponse
router = APIRouter(prefix="/leads", tags=["Leads"])


# Add a comment to a lead
#endpoint: /leads/{expa_person_id}/comments
#Example request body: {"text": "This is a comment", "created_by": "member_123"}
@router.post("/{expa_person_id}/comments")
def add_comment(
    expa_person_id: str,
    payload: CommentCreate,
    db: Session = Depends(get_db),
) -> CommentResponse:
    try:
        stmt = (
            select(Member)
            .where(Member.expa_person_id == payload.created_by)
        )
        member = db.execute(stmt).scalars().first()
        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        comment = ExpaLeadComment(
            expa_person_id=expa_person_id,
            comment=payload.text,
            creator_name=member.full_name,
        )

        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment
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

# Retrieve comments for a lead
# endpoint: /leads/{expa_person_id}/comments
@router.get("/{expa_person_id}/comments")
def get_comments(
    expa_person_id: str,
    db: Session = Depends(get_db),
)-> list[CommentResponse]:
    try:
        stmt = (
            select(ExpaLeadComment)
            .where(ExpaLeadComment.expa_person_id == expa_person_id)
            .order_by(ExpaLeadComment.created_at.desc())
        )
        return db.execute(stmt).scalars().all()
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

# Delete a comment from a lead
# endpoint: /leads/{expa_person_id}/comments/{comment_id}
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
        comment = db.get(ExpaLeadComment, comment_id)
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