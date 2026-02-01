from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.leads.expa_leads import ExpaLead
from app.models.ogx.ogx_standards import OgxStandards
from app.schemas.ogx_standards import OgxStandardsResponse, OgxStandardsUpdateRequest

router = APIRouter(prefix="/realizations/standards", tags=["Realizations"])


@router.get("/{expa_person_id}", response_model=OgxStandardsResponse)
def get_standards(
	expa_person_id: str,
	db: Session = Depends(get_db),
):
	try:
		stmt = select(OgxStandards).where(OgxStandards.expa_person_id == expa_person_id)
		standards = db.execute(stmt).scalars().first()
		if not standards:
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Standards not found")
		return standards
	except HTTPException:
		raise
	except SQLAlchemyError:
		raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error")
	except Exception:
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")


@router.patch("/{expa_person_id}", response_model=OgxStandardsResponse)
def patch_standards(
	expa_person_id: str,
	payload: OgxStandardsUpdateRequest,
	db: Session = Depends(get_db),
):
	try:
		updates = payload.model_dump(exclude_unset=True)
		if not updates:
			raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

		# Ensure person exists (FK requirement)
		lead = db.execute(select(ExpaLead).where(ExpaLead.expa_person_id == expa_person_id)).scalars().first()
		if not lead:
			raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")

		standards = db.execute(select(OgxStandards).where(OgxStandards.expa_person_id == expa_person_id)).scalars().first()

		if not standards:
			standards = OgxStandards(expa_person_id=expa_person_id)
			db.add(standards)
			db.flush()

		for key, value in updates.items():
			setattr(standards, key, value)

		db.commit()
		db.refresh(standards)
		return standards
	except HTTPException:
		db.rollback()
		raise
	except SQLAlchemyError:
		db.rollback()
		raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database error")
	except Exception:
		db.rollback()
		raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
