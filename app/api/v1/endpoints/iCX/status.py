from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.icx.expa_icx_lead_status_snapshot import ExpaICXLeadStatusSnapshot
from app.models.icx.expa_icx_leads import ExpaICXLead
from app.schemas.icx.status import ICXLeadStatusOut, ICXLeadStatusUpdate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/icx/leads", tags=["iCX Leads"])


@router.get("/{application_id}/status")
def get_icx_status(
    application_id: str,
    db: Session = Depends(get_db),
):
    try:
        lead = db.get(ExpaICXLead, str(application_id))
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        status_row = db.get(ExpaICXLeadStatusSnapshot, str(application_id))
        if not status_row:
            return {}
        return status_row
    except HTTPException:
        raise
    except SQLAlchemyError as e:
        logger.exception("DB error in get_icx_status(application_id=%s)", application_id)
        raise HTTPException(status_code=503, detail="Database error") from e
    except Exception as e:
        logger.exception("Unexpected error in get_icx_status(application_id=%s)", application_id)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.patch("/{application_id}/status", response_model=ICXLeadStatusOut)
def patch_icx_status(
    application_id: str,
    payload: ICXLeadStatusUpdate,
    db: Session = Depends(get_db),
) -> ICXLeadStatusOut:
    try:
        lead = db.get(ExpaICXLead, str(application_id))
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        status_row = db.get(ExpaICXLeadStatusSnapshot, str(application_id))
        if not status_row:
            status_row = ExpaICXLeadStatusSnapshot(application_id=str(application_id))
            db.add(status_row)

        data = payload.model_dump(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        # If out_of_process is set to yes, reason must be provided (either in payload or already stored)
        next_out = data.get("out_of_process", status_row.out_of_process)
        next_reason = data.get("reason", status_row.reason)
        if next_out == "yes" and (not next_reason or not str(next_reason).strip()):
            raise HTTPException(status_code=400, detail="reason is required when out_of_process is yes")

        allowed_keys = set(ExpaICXLeadStatusSnapshot.__mapper__.attrs.keys())
        unknown = [k for k in data.keys() if k not in allowed_keys]
        if unknown:
            raise HTTPException(status_code=400, detail=f"Invalid field(s): {unknown}")

        for key, value in data.items():
            setattr(status_row, key, value)

        db.commit()
        db.refresh(status_row)
        return status_row
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("DB error in patch_icx_status(application_id=%s)", application_id)
        raise HTTPException(status_code=503, detail="Database error") from e
    except Exception as e:
        db.rollback()
        logger.exception("Unexpected error in patch_icx_status(application_id=%s)", application_id)
        raise HTTPException(status_code=500, detail="Internal server error") from e
