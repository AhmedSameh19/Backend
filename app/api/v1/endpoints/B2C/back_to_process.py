from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query,status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.b2c.b2c_back_to_process import B2CBackToProcess
from app.models.leads.expa_leads import ExpaLead
from app.schemas.b2c.back_to_process import BackToProcessIn, BackToProcessOut


router = APIRouter(prefix="/b2c", tags=["B2C"])


@router.get("/back-to-process/{home_lc_id}", response_model=list[BackToProcessOut])
def list_back_to_process(
	home_lc_id: int,
	limit: int = Query(100, gt=0, le=500),  # max 500 rows at once
    offset: int = Query(0, ge=0),
	db: Session = Depends(get_db),
) -> list[BackToProcessOut]:
	try:
		if limit <= 0:
			raise HTTPException(status_code=400, detail="limit must be > 0")

		stmt = (
			select(B2CBackToProcess)
			.where(B2CBackToProcess.home_lc_id == home_lc_id)
			.order_by(B2CBackToProcess.inserted_at.desc())
			.limit(limit)
			.offset(offset)
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


@router.post("/back-to-process", response_model=BackToProcessOut, status_code=status.HTTP_201_CREATED)
def add_back_to_process(
	payload: BackToProcessIn,
	db: Session = Depends(get_db),
) -> BackToProcessOut:
	
	try:
		lead = db.get(ExpaLead, payload.expa_person_id)
		if not lead:
			raise HTTPException(status_code=404, detail="Lead not found")

		row = B2CBackToProcess(
			expa_person_id=lead.expa_person_id,
			created_at=lead.created_at,
			full_name=lead.full_name,
			email=lead.email,
			phone=lead.phone,
			expa_status=lead.expa_status,
			selected_programmes=lead.selected_programmes,
			home_lc_name=lead.home_lc_name,
			home_mc_name=lead.home_mc_name,
			home_lc_id=lead.home_lc_id,
			home_mc_id=lead.home_mc_id,
		)

		db.add(row)
		db.commit()
		db.refresh(row)
		return row
	except HTTPException:
		raise
	except IntegrityError:
		db.rollback()
		raise HTTPException(status_code=409, detail="Lead already in back_to_process")
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
