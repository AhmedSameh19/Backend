from app.models.b2c.b2c_status_snapshot import B2CLeadStatusSnapshot
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import get_db

from app.models.leads.expa_lead_snapshot import ExpaLeadStatusSnapshot
from app.schemas.b2c.status import B2CStatusUpdate, B2CStatusOut

router = APIRouter(prefix="/b2c", tags=["B2C"])

# Retrieve status snapshot for a lead
# endpoint: /b2c/{expa_person_id}/status
@router.get("/{expa_person_id}/status")
def get_status(
    expa_person_id: str,
    db: Session = Depends(get_db),
):
    try:
        status_row = db.get(B2CLeadStatusSnapshot, expa_person_id)
        if not status_row:
            return {}
        return status_row
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database error")
    except Exception:
        raise HTTPException(status_code=500, detail="Internal server error")

# Update status snapshot for a lead
# Example request body: {"contacted": true, "interested": false}
# endpoint: /b2c/{expa_person_id}/status
# example PATCH /b2c/123/status
# {
#   "contact_status": "yes"
# }
#
@router.patch("/{expa_person_id}/status")
def update_status(
    expa_person_id: str,
    payload: B2CStatusUpdate,
    db: Session = Depends(get_db),
) -> B2CStatusOut:
    try:
        status_row = db.get(B2CLeadStatusSnapshot, expa_person_id)
        if not status_row:
            status_row = B2CLeadStatusSnapshot(expa_person_id=expa_person_id)
            db.add(status_row)

        data = payload.model_dump(exclude_unset=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields provided to update")

        allowed_keys = set(B2CLeadStatusSnapshot.__mapper__.attrs.keys())
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
