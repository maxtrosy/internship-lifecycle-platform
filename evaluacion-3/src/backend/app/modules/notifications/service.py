"""Recipient-scoped lifecycle notices and practice conversations."""
from __future__ import annotations

import re

import psycopg

from app.db import CommandContext
from app.errors import BusinessError, Forbidden, NotFound
from app.modules.authz import service as authz
from app.modules.audit import service as audit


NOTICE_ACTIONS = {
    "application.submitted": "APPLICATION_SUBMITTED",
    "application.selected": "APPLICATION_SELECTED",
    "application.eligibility_review_requested": "ELIGIBILITY_REVIEW",
    "application.eligibility_reviewed": "ELIGIBILITY_REVIEW",
    "checklist_item.submitted": "DOCUMENT_ACTIVITY",
    "checklist_item.approved": "DOCUMENT_ACTIVITY",
    "checklist_item.rejected": "DOCUMENT_ACTIVITY",
    "checklist_item.rejected_after_activation": "DOCUMENT_ACTIVITY",
    "completion_evidence.submitted": "DOCUMENT_ACTIVITY",
    "placement.activated": "PLACEMENT_ACTIVATED",
    "progress.report_submitted": "PROGRESS_REPORTED",
    "progress.hours_recorded": "PROGRESS_REPORTED",
    "evaluation.submitted": "EVALUATION_SUBMITTED",
    "placement.incident_reported": "INCIDENT_REPORTED",
    "placement.change_reported": "CHANGE_REPORTED",
    "placement.completed": "PLACEMENT_COMPLETED",
    "placement.closed": "PLACEMENT_CLOSED",
    "message.sent": "MESSAGE_RECEIVED",
    "opportunity.submitted_for_review": "OPPORTUNITY_REVIEW",
    "opportunity.approved_for_publication": "OPPORTUNITY_REVIEW",
    "opportunity.published": "OPPORTUNITY_PUBLISHED",
    "opportunity.closed": "OPPORTUNITY_CLOSED",
}


def _placement_context(cur: psycopg.Cursor, placement_id: int) -> dict | None:
    return cur.execute(
        """SELECT p.id AS placement_id, a.student_id, o.id AS opportunity_id,
                  o.host_org_id, o.program_id,
                  pv.workplace_supervisor_id AS current_workplace_supervisor_id
           FROM placement p JOIN application a ON a.id=p.application_id
           JOIN opportunity o ON o.id=a.opportunity_id
           LEFT JOIN placement_version pv ON pv.id=p.current_version_id
           WHERE p.id=%s""",
        (placement_id,),
    ).fetchone()


def _app_context(cur: psycopg.Cursor, application_id: int) -> dict | None:
    return cur.execute(
        """SELECT a.id AS application_id, a.student_id, a.state, a.eligibility_result,
                  o.id AS opportunity_id,
                  o.host_org_id, o.program_id, p.id AS placement_id,
                  pv.workplace_supervisor_id AS current_workplace_supervisor_id
           FROM application a JOIN opportunity o ON o.id=a.opportunity_id
           LEFT JOIN placement p ON p.application_id=a.id
           LEFT JOIN placement_version pv ON pv.id=p.current_version_id
           WHERE a.id=%s""",
        (application_id,),
    ).fetchone()


def _checklist_placement_id(cur: psycopg.Cursor, item_id: int) -> int | None:
    row = cur.execute("SELECT placement_id FROM checklist_item WHERE id=%s", (item_id,)).fetchone()
    return row["placement_id"] if row else None


def _opportunity_recipients(cur: psycopg.Cursor, action: str, opportunity_id: int) -> set[int] | None:
    """Resolve event recipients from current program relations and configured authority."""
    from app.config import get_settings

    opportunity = cur.execute(
        "SELECT id, program_id FROM opportunity WHERE id=%s", (opportunity_id,),
    ).fetchone()
    if opportunity is None:
        return None
    settings = get_settings()
    if action == "opportunity.submitted_for_review":
        configured = settings.opportunity_reviewer_roles
    elif action == "opportunity.approved_for_publication":
        configured = settings.opportunity_publisher_roles
    else:
        configured = ()
    recipients: set[int] = set()
    if configured:
        recipients.update(row["user_id"] for row in cur.execute(
            """SELECT DISTINCT user_id FROM role_assignment
               WHERE role = ANY(%s) AND (role='EXPERIENTIAL_COORDINATOR' OR program_id=%s)""",
            (list(configured), opportunity["program_id"]),
        ).fetchall())
    elif action == "opportunity.published":
        # A published listing is relevant to students in its program.
        recipients.update(row["user_id"] for row in cur.execute(
            "SELECT user_id FROM role_assignment WHERE role='STUDENT' AND program_id=%s",
            (opportunity["program_id"],),
        ).fetchall())
    elif action == "opportunity.closed":
        # Notify only applicants whose opportunity has become unavailable.
        recipients.update(row["student_id"] for row in cur.execute(
            "SELECT student_id FROM application WHERE opportunity_id=%s",
            (opportunity_id,),
        ).fetchall())
    return recipients


def _related_recipients(cur: psycopg.Cursor, placement: dict, audience: str = "JOINT") -> set[int]:
    ids = {placement["student_id"]}
    if placement["current_workplace_supervisor_id"] is not None and audience == "JOINT":
        ids.add(placement["current_workplace_supervisor_id"])
    ids.update(
        row["user_id"] for row in cur.execute(
            "SELECT user_id FROM supervisor_assignment WHERE placement_id=%s AND kind='FACULTY'",
            (placement["placement_id"],),
        ).fetchall()
    )
    ids.update(
        row["user_id"] for row in cur.execute(
            """SELECT user_id FROM role_assignment
               WHERE role='PROGRAM_COORDINATOR' AND program_id=%s""",
            (placement["program_id"],),
        ).fetchall()
    )
    ids.update(
        row["user_id"] for row in cur.execute(
            "SELECT user_id FROM role_assignment WHERE role='EXPERIENTIAL_COORDINATOR'"
        ).fetchall()
    )
    return ids


def _recipients(cur: psycopg.Cursor, action: str, subject_type: str, subject_id: int,
                after: dict | None) -> tuple[set[int], int | None, int | None] | None:
    """Select only role/relationship-linked recipients; notices carry no source payload."""
    category = NOTICE_ACTIONS.get(action)
    if category is None:
        return None

    placement_id: int | None = None
    opportunity_id: int | None = None
    audience = "JOINT"
    if subject_type == "opportunity":
        opportunity_id = subject_id
        recipients = _opportunity_recipients(cur, action, opportunity_id)
        if recipients is None:
            return None
    elif action.startswith("application."):
        context = _app_context(cur, subject_id)
        if context is None:
            return None
        placement_id = context["placement_id"]
        opportunity_id = context["opportunity_id"]
        if action == "application.submitted":
            recipients = {
                row["user_id"] for row in cur.execute(
                    """SELECT user_id FROM role_assignment
                       WHERE role='HOST_ORG_MEMBER' AND host_org_id=%s""",
                    (context["host_org_id"],),
                ).fetchall()
            }
        elif action == "application.eligibility_review_requested":
            recipients = {
                row["user_id"] for row in cur.execute(
                    """SELECT user_id FROM role_assignment
                       WHERE role='PROGRAM_COORDINATOR' AND program_id=%s""",
                    (context["program_id"],),
                ).fetchall()
            }
        elif action == "application.eligibility_reviewed":
            recipients = {context["student_id"]}
            if (after or {}).get("state") == "SUBMITTED":
                recipients.update(
                    row["user_id"] for row in cur.execute(
                        """SELECT user_id FROM role_assignment
                           WHERE role='HOST_ORG_MEMBER' AND host_org_id=%s""",
                        (context["host_org_id"],),
                    ).fetchall()
                )
        else:
            if placement_id is None:
                return None
            recipients = _related_recipients(cur, context)
    elif subject_type == "checklist_item":
        placement_id = _checklist_placement_id(cur, subject_id)
        if placement_id is None:
            return None
        context = _placement_context(cur, placement_id)
        if context is None:
            return None
        opportunity_id = context["opportunity_id"]
        recipients = {context["student_id"]}
        recipients.update(
            row["user_id"] for row in cur.execute(
                "SELECT user_id FROM role_assignment WHERE role IN ('LEGAL_REVIEWER','EXPERIENTIAL_COORDINATOR')"
            ).fetchall()
        )
    elif subject_type == "placement":
        placement_id = subject_id
        context = _placement_context(cur, placement_id)
        if context is None:
            return None
        opportunity_id = context["opportunity_id"]
        if action == "completion_evidence.submitted":
            recipients = _related_recipients(cur, context, audience="ACADEMIC")
        elif category == "DOCUMENT_ACTIVITY":
            recipients = {context["student_id"]}
            recipients.update(
                row["user_id"] for row in cur.execute(
                    "SELECT user_id FROM role_assignment WHERE role IN ('LEGAL_REVIEWER','EXPERIENTIAL_COORDINATOR')"
                ).fetchall()
            )
        elif category == "EVALUATION_SUBMITTED":
            recipients = _related_recipients(cur, context, audience="ACADEMIC")
        elif category == "MESSAGE_RECEIVED":
            audience = (after or {}).get("audience", "JOINT")
            recipients = _related_recipients(cur, context, audience=audience)
        else:
            recipients = _related_recipients(cur, context)
    else:
        return None

    actor = audit_actor(cur)
    if actor is not None:
        recipients.discard(actor)
    active = {
        row["id"] for row in cur.execute(
            "SELECT id FROM user_account WHERE is_active=true AND id=ANY(%s)",
            (list(recipients),),
        ).fetchall()
    } if recipients else set()
    return active, placement_id, opportunity_id


def audit_actor(cur: psycopg.Cursor) -> int | None:
    from app.db import current_command

    command = current_command()
    return command.actor_id if command else None


def enqueue_from_audit(cur: psycopg.Cursor, event_id: int, action: str, subject_type: str,
                       subject_id: int, after: dict | None, created_at) -> None:
    prepared = _recipients(cur, action, subject_type, subject_id, after)
    if prepared is None:
        return
    recipients, placement_id, opportunity_id = prepared
    category = NOTICE_ACTIONS[action]
    for recipient_id in recipients:
        cur.execute(
            """INSERT INTO user_notification
                 (recipient_id, source_event_id, category, placement_id, opportunity_id, created_at)
               VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (recipient_id, source_event_id) DO NOTHING""",
            (recipient_id, event_id, category, placement_id, opportunity_id, created_at),
        )


def list_inbox(cur: psycopg.Cursor, recipient_id: int) -> list[dict]:
    return cur.execute(
        """SELECT id, category, placement_id, opportunity_id, created_at, read_at,
                  (read_at IS NOT NULL) AS is_read
           FROM user_notification WHERE recipient_id=%s
           ORDER BY created_at DESC, id DESC LIMIT 100""",
        (recipient_id,),
    ).fetchall()


def mark_read(ctx: CommandContext, notification_id: int) -> dict:
    row = ctx.execute(
        """UPDATE user_notification SET read_at=coalesce(read_at, now())
           WHERE id=%s AND recipient_id=%s
           RETURNING id, read_at""",
        (notification_id, ctx.actor_id),
    ).fetchone()
    if row is None:
        raise NotFound()
    audit.write(ctx.cur, "notification.read", "notification", row["id"], None, None)
    return row


def can_read_audience(cur: psycopg.Cursor, subj: dict, placement_id: int, audience: str) -> bool:
    if audience not in {"JOINT", "ACADEMIC"}:
        return False
    action = "message:joint:read" if audience == "JOINT" else "message:academic:read"
    return authz.can_perform(cur, subj, action, placement_id)


def list_messages(cur: psycopg.Cursor, subj: dict, placement_id: int, audience: str) -> list[dict]:
    authz.authorize(cur, subj, "placement:read", placement_id)
    if not can_read_audience(cur, subj, placement_id, audience):
        raise Forbidden("no access to this conversation audience")
    return cur.execute(
        """SELECT m.id, c.audience, u.display_name AS author_name, m.content, m.created_at
           FROM placement_conversation c JOIN placement_message m ON m.conversation_id=c.id
           JOIN user_account u ON u.id=m.author_id
           WHERE c.placement_id=%s AND c.audience=%s ORDER BY m.id""",
        (placement_id, audience),
    ).fetchall()


def message_capabilities(cur: psycopg.Cursor, subj: dict, placement_id: int) -> dict[str, bool]:
    authz.authorize(cur, subj, "placement:read", placement_id)
    return {
        "joint": can_read_audience(cur, subj, placement_id, "JOINT"),
        "academic": can_read_audience(cur, subj, placement_id, "ACADEMIC"),
    }


def create_message(ctx: CommandContext, placement_id: int, audience: str, content: str) -> dict:
    clean_content = re.sub(r"\s+", " ", content).strip()
    if not clean_content or len(clean_content) > 4000:
        raise BusinessError("MESSAGE_CONTENT_INVALID")
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "placement:read", placement_id)
    if not can_read_audience(ctx.cur, subj, placement_id, audience):
        raise Forbidden("no access to this conversation audience")
    conversation = ctx.execute(
        """INSERT INTO placement_conversation(placement_id,audience,created_by)
           VALUES (%s,%s,%s) ON CONFLICT (placement_id,audience)
           DO NOTHING
           RETURNING id""",
        (placement_id, audience, ctx.actor_id),
    ).fetchone()
    if conversation is None:
        conversation = ctx.execute(
            "SELECT id FROM placement_conversation WHERE placement_id=%s AND audience=%s",
            (placement_id, audience),
        ).fetchone()
    message = ctx.execute(
        """INSERT INTO placement_message(conversation_id,author_id,content)
           VALUES (%s,%s,%s) RETURNING id, content, created_at""",
        (conversation["id"], ctx.actor_id, clean_content),
    ).fetchone()
    audit.write(ctx.cur, "message.sent", "placement", placement_id, None,
                {"audience": audience, "message_id": message["id"]})
    return {"id": message["id"], "audience": audience, "content": message["content"],
            "created_at": message["created_at"], "author_name": subj["display_name"]}
