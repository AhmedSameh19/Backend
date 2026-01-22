from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.leads.expa_lead_followups import ExpaLeadFollowUp
from app.models.members import Member
from app.schemas.leads.followups import FollowUpCreate, FollowUpOut, FollowUpStatusUpdate

from datetime import datetime, timezone


router = APIRouter(prefix="/leads", tags=["Leads"])



# Create a follow-up for a lead
# endpoint: POST /leads/{expa_person_id}/followups
# body: {"follow_up_text": "Follow up text", "follow_up_at": "2024-12-31T12:00:00Z", "created_by": "member_123", "status": "pending"}
@router.post("/{expa_person_id}/followups", response_model=FollowUpOut)
def create_followup(
    expa_person_id: str,
    payload: FollowUpCreate,
    db: Session = Depends(get_db),
) -> FollowUpOut:

	# To check that follow_up_at is in the future
	now = datetime.now(timezone.utc)
	follow_up_at = payload.follow_up_at
	if follow_up_at.tzinfo is None:
		follow_up_at = follow_up_at.replace(tzinfo=timezone.utc)
	if follow_up_at <= now:
		raise HTTPException(
			status_code=status.HTTP_400_BAD_REQUEST,
			detail="follow_up_at must be greater than the current time",
		)

	try:
		created_by_member_id = None
		created_by_member_name = None

		if payload.created_by is not None:
			stmt = (
				select(Member)
				.where(Member.expa_person_id == payload.created_by)
			)
			member = db.execute(stmt).scalars().first()	
			if not member:
				raise HTTPException(status_code=404, detail="Member not found")
			created_by_member_id = payload.created_by
			created_by_member_name = member.full_name

		followup = ExpaLeadFollowUp(
			expa_person_id=expa_person_id,
			follow_up_text=payload.follow_up_text,
			follow_up_at=payload.follow_up_at,
			status="pending",	
			created_by_member_id=created_by_member_id,
			created_by_member_name=created_by_member_name,
			created_at=now
		)
		db.add(followup)
		db.commit()
		db.refresh(followup)
		return followup

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

# Get follow-ups created by a specific member
# endpoint: GET /leads/followups/created_by/{created_by_member_id}

@router.get("/followups/created_by/{created_by_member_id}", response_model=list[FollowUpOut],status_code=status.HTTP_200_OK)
def get_followups_by_member(
	created_by_member_id: str,
	db: Session = Depends(get_db),
) -> list[FollowUpOut]:
	try:
		stmt = (
			select(ExpaLeadFollowUp)
			.where(ExpaLeadFollowUp.created_by_member_id == created_by_member_id)
			.order_by(
				ExpaLeadFollowUp.follow_up_at.desc(),
				ExpaLeadFollowUp.created_at.desc(),
				ExpaLeadFollowUp.id.desc(),
			)
		)
		return db.execute(stmt).scalars().all()
	except HTTPException:
		raise
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

# Get follow-ups for a lead
# endpoint: GET /leads/{expa_person_id}/followups
@router.get("/{expa_person_id}/followups", response_model=list[FollowUpOut])
def list_followups(
	expa_person_id: str,
	db: Session = Depends(get_db),
) -> list[FollowUpOut]:
	try:
		stmt = (
			select(ExpaLeadFollowUp)
			.where(ExpaLeadFollowUp.expa_person_id == expa_person_id)
			.order_by(
				ExpaLeadFollowUp.follow_up_at.desc(),
				ExpaLeadFollowUp.created_at.desc(),
				ExpaLeadFollowUp.id.desc(),
			)
		)
		return db.execute(stmt).scalars().all()
	except HTTPException:
		raise
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


# Update follow-up status only
# endpoint: PATCH /leads/{expa_person_id}/followups/{followup_id}/status
@router.patch(
	"/{expa_person_id}/followups/{followup_id}/status",
	response_model=FollowUpOut,
)
def update_followup_status(
	expa_person_id: str,
	followup_id: int,
	payload: FollowUpStatusUpdate,
	db: Session = Depends(get_db),
) -> FollowUpOut:
	try:
		followup = db.get(ExpaLeadFollowUp, followup_id)
		if not followup or followup.expa_person_id != expa_person_id:
			raise HTTPException(status_code=404, detail="Follow-up not found")

		followup.status = payload.status
		db.commit()
		db.refresh(followup)
		return followup
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


# Delete a follow-up for a lead
# endpoint: DELETE /leads/{expa_person_id}/followups/{followup_id}
@router.delete(
	"/{expa_person_id}/followups/{followup_id}",
	status_code=status.HTTP_204_NO_CONTENT,
	response_class=Response,
)
def delete_followup(
	expa_person_id: str,
	followup_id: int,
	db: Session = Depends(get_db),
) -> Response:
	try:
		followup = db.get(ExpaLeadFollowUp, followup_id)
		if not followup or followup.expa_person_id != expa_person_id:
			raise HTTPException(status_code=404, detail="Follow-up not found")

		db.delete(followup)
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
