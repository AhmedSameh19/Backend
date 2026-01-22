from app.models.leads.expa_lead_snapshot import ExpaLeadStatusSnapshot
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db

from app.schemas.leads.status import LeadStatusUpdate, LeadStatusOut

router = APIRouter(prefix="/leads", tags=["Leads"])

# Retrieve status snapshot for a lead
# endpoint: /leads/{expa_person_id}/status
@router.get("/{expa_person_id}/status")
def get_status(
    expa_person_id: str,
    db: Session = Depends(get_db),
):
    try:
        status_row = db.get(ExpaLeadStatusSnapshot, expa_person_id)
        if not status_row:
            return {}
        return status_row
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database error")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

# Update status snapshot for a lead
# Example request body: {"contacted": true, "interested": false}
# endpoint: /leads/{expa_person_id}/status
# example PATCH /leads/123/status
# {
#   "contact_status": "yes"
# }
#
@router.patch("/{expa_person_id}/status")
def update_status(
    expa_person_id: str,
    payload: LeadStatusUpdate,
    db: Session = Depends(get_db),
) -> LeadStatusOut:
    try:
        status_row = db.get(ExpaLeadStatusSnapshot, expa_person_id)

        if not status_row:
            status_row = ExpaLeadStatusSnapshot(expa_person_id=expa_person_id)
            db.add(status_row)

        data = payload.model_dump(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        allowed_keys = set(ExpaLeadStatusSnapshot.__mapper__.attrs.keys())
        unknown = [k for k in data.keys() if k not in allowed_keys]
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid field(s): {unknown}. Allowed: {sorted(allowed_keys)}",
            )

        for key, value in data.items():
            setattr(status_row, key, value)

        db.commit()
        db.refresh(status_row)
        return status_row
    except HTTPException:
        raise
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Database error")
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")
