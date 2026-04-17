from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.icx.expa_icx_realizations import ExpaICXRealization
from app.models.icx.icx_realizations_standards import ICXRealizationsStandards
from app.schemas.icx.realizations_standards import (
    ICXRealizationsStandardsResponse,
    ICXRealizationsStandardsUpdateRequest,
)

router = APIRouter(prefix="/icx/realizations/standards", tags=["iCX Realizations"])


@router.get("/{application_id}", response_model=ICXRealizationsStandardsResponse)
def get_icx_realizations_standards(
    application_id: str,
    db: Session = Depends(get_db),
):
    try:
        stmt = select(ICXRealizationsStandards).where(
            or_(
                ICXRealizationsStandards.application_id == str(application_id).strip(),
                ICXRealizationsStandards.expa_person_id == str(application_id).strip()
            )
        )
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


@router.patch("/{application_id}", response_model=ICXRealizationsStandardsResponse)
def patch_icx_realizations_standards(
    application_id: str,
    payload: ICXRealizationsStandardsUpdateRequest,
    db: Session = Depends(get_db),
):
    try:
        updates = payload.model_dump(exclude_unset=True)
        if not updates:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

        realization = db.execute(
            select(ExpaICXRealization).where(
                or_(
                    ExpaICXRealization.application_id == str(application_id).strip(),
                    ExpaICXRealization.expa_person_id == str(application_id).strip()
                )
            )
        ).scalars().first()

        if not realization:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Realization not found for ID: {application_id}")

        standards = (
            db.execute(
                select(ICXRealizationsStandards).where(ICXRealizationsStandards.application_id == str(application_id))
            )
            .scalars()
            .first()
        )

        if not standards:
            standards = ICXRealizationsStandards(
                application_id=str(application_id),
                expa_person_id=realization.expa_person_id,
            )
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
