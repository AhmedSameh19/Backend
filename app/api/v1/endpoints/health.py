from fastapi import APIRouter, Depends, HTTPException, status
from app.workers.people_tasks import fetch_people_hourly
from app.workers.members_tasks import fetch_members_monthly
from app.workers.realizations_tasks import fetch_realizations_hourly
from app.workers.icx_leads_tasks import fetch_icx_leads_hourly
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.db.session import get_db

router = APIRouter()

@router.get("")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database not reachable",
        )

@router.get("/test-expa-task")
def test_expa_task():
    try:
        task = fetch_icx_leads_hourly.delay()
        return {"task_id": task.id}
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue task",
        )
