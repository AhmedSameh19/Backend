from __future__ import annotations

from datetime import datetime, timedelta, timezone

from celery.utils.log import get_task_logger
from sqlalchemy import select, and_

from app.db.session import SessionLocal
from app.models.leads.expa_lead_followups import ExpaLeadFollowUp
from app.models.icx.expa_icx_lead_followups import ExpaICXLeadFollowUp
from app.models.members import Member
from app.services.email_service import send_email
from app.workers.celery_app import celery

logger = get_task_logger(__name__)

WINDOW_MINUTES = 15


def _build_followup_html(
    member_name: str,
    follow_up_text: str,
    follow_up_at: datetime,
    lead_type: str,
    lead_id: str,
) -> str:
    """Build a simple HTML email body for a follow-up reminder."""
    return f"""\
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
  <h2 style="color: #037ef3;">⏰ Follow-Up Reminder</h2>
  <p>Hi <strong>{member_name}</strong>,</p>
  <p>You have a follow-up that is due now:</p>
  <table style="border-collapse: collapse; margin: 16px 0;">
    <tr>
      <td style="padding: 6px 12px; font-weight: bold;">Type</td>
      <td style="padding: 6px 12px;">{lead_type}</td>
    </tr>
    <tr>
      <td style="padding: 6px 12px; font-weight: bold;">Lead / Application ID</td>
      <td style="padding: 6px 12px;">{lead_id}</td>
    </tr>
    <tr>
      <td style="padding: 6px 12px; font-weight: bold;">Due at</td>
      <td style="padding: 6px 12px;">{follow_up_at.strftime("%Y-%m-%d %H:%M %Z")}</td>
    </tr>
    <tr>
      <td style="padding: 6px 12px; font-weight: bold;">Note</td>
      <td style="padding: 6px 12px;">{follow_up_text}</td>
    </tr>
  </table>
  <p>Please take action as soon as possible.</p>
  <br/>
  <p style="color: #999; font-size: 12px;">— AIESEC Egypt CRM</p>
</body>
</html>"""


def _process_followups(db, now_start, now_end) -> dict:
    """Query both OGX and ICX follow-ups due in the window and send emails."""
    sent = 0
    skipped_no_email = 0
    failed = 0

    # ── OGX Follow-ups ──────────────────────────────────────────────
    ogx_stmt = (
        select(ExpaLeadFollowUp, Member)
        .join(Member, Member.expa_person_id == ExpaLeadFollowUp.created_by_member_id)
        .where(
            and_(
                ExpaLeadFollowUp.status == "pending",
                ExpaLeadFollowUp.follow_up_at >= now_start,
                ExpaLeadFollowUp.follow_up_at < now_end,
            )
        )
    )
    for followup, member in db.execute(ogx_stmt).all():
        if not member.email:
            logger.info(
                "OGX followup %s — member %s has no email, skipping",
                followup.id, member.member_id,
            )
            skipped_no_email += 1
            continue

        html = _build_followup_html(
            member_name=member.full_name,
            follow_up_text=followup.follow_up_text,
            follow_up_at=followup.follow_up_at,
            lead_type="OGX Lead",
            lead_id=followup.expa_person_id,
        )
        ok = send_email(
            to=member.email,
            subject=f"Follow-Up Reminder — OGX Lead {followup.expa_person_id}",
            html_body=html,
        )
        if ok:
            sent += 1
        else:
            failed += 1

    # ── ICX Follow-ups ──────────────────────────────────────────────
    icx_stmt = (
        select(ExpaICXLeadFollowUp, Member)
        .join(Member, Member.expa_person_id == ExpaICXLeadFollowUp.created_by_member_id)
        .where(
            and_(
                ExpaICXLeadFollowUp.status == "pending",
                ExpaICXLeadFollowUp.follow_up_at >= now_start,
                ExpaICXLeadFollowUp.follow_up_at < now_end,
            )
        )
    )
    for followup, member in db.execute(icx_stmt).all():
        if not member.email:
            logger.info(
                "ICX followup %s — member %s has no email, skipping",
                followup.id, member.member_id,
            )
            skipped_no_email += 1
            continue

        html = _build_followup_html(
            member_name=member.full_name,
            follow_up_text=followup.follow_up_text,
            follow_up_at=followup.follow_up_at,
            lead_type="ICX Application",
            lead_id=followup.application_id,
        )
        ok = send_email(
            to=member.email,
            subject=f"Follow-Up Reminder — ICX Application {followup.application_id}",
            html_body=html,
        )
        if ok:
            sent += 1
        else:
            failed += 1

    return {"sent": sent, "skipped_no_email": skipped_no_email, "failed": failed}


@celery.task(name="notifications.send_followup_reminders")
def send_followup_reminders() -> dict:
    """
    Scan for pending follow-ups due in the current 15-minute window
    and email the member who created them.
    """
    now = datetime.now(timezone.utc)
    window_start = now
    window_end = now + timedelta(minutes=WINDOW_MINUTES)

    logger.info(
        "Checking for follow-ups due between %s and %s",
        window_start.isoformat(), window_end.isoformat(),
    )

    db = SessionLocal()
    try:
        result = _process_followups(db, window_start, window_end)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Error processing follow-up reminders")
        raise
    finally:
        db.close()

    logger.info(
        "Follow-up reminders done — sent=%s skipped_no_email=%s failed=%s",
        result["sent"], result["skipped_no_email"], result["failed"],
    )
    return {"ok": True, **result}
