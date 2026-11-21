"""CR-05 rotational placements and mid-placement transfers (Evaluación 4).

The placement keeps the academic identity; ``placement_segment`` rows keep the
operational conditions of each rotation (organization/unit, supervisor, dates,
modality, responsibilities, expected hours) and their own records.

Every command follows the lifecycle pattern (ADR-003/005): authorize -> lock the
placement row -> evaluate guards from persisted rows -> mutate -> audit, all in
one ``db.command`` transaction. PostgreSQL triggers in migration 0016 repeat the
critical guards (single active segment, enablement, immutability, closure gate).
"""
from __future__ import annotations

import datetime as dt
import math

import psycopg

from app.db import CommandContext
from app.errors import BusinessError, NotFound
from app.modules.audit import service as audit
from app.modules.authz import service as authz
from app.modules.policies import service as policies

OPEN_STATUSES = ("PLANNED", "ACTIVE")
ENDED_STATUSES = ("COMPLETED", "TERMINATED_EARLY", "TRANSFERRED")
MODALITIES = {"ONSITE", "REMOTE", "HYBRID"}
RECOGNITION = {"ACCEPTED_HOURS_RECOGNIZED", "NOT_RECOGNIZED"}
REVIEW_DECISIONS = {"ACCEPTED", "REJECTED", "DISPUTED"}
REVIEW_REASON_CODES = {"DUPLICATE", "OUTSIDE_SEGMENT", "NOT_VERIFIABLE", "OTHER"}
EXPERIENCE_DECISIONS = {"APPROVED", "CHANGES_REQUIRED"}


def _gate(fn):
    try:
        return fn()
    except psycopg.errors.RaiseException as exc:  # DB safety net fired
        message = str(exc).split("\n")[0]
        code = message.split(":", 1)[0] if ":" in message else "GATE_VIOLATION"
        raise BusinessError(code if code.isupper() else "GATE_VIOLATION", message) from exc
    except psycopg.errors.UniqueViolation as exc:
        if "placement_one_active_segment" in str(exc):
            raise BusinessError("SEGMENT_ALREADY_ACTIVE") from exc
        raise


def _clean(value: str | None, field: str, limit: int, *, required: bool = True) -> str | None:
    text = (value or "").strip()
    if not text:
        if required:
            raise BusinessError("SEGMENT_FIELD_REQUIRED", field)
        return None
    if len(text) > limit:
        raise BusinessError("SEGMENT_FIELD_TOO_LONG", field)
    return text


def _lock_active_placement(ctx: CommandContext, pid: int) -> dict:
    placement = ctx.execute("SELECT * FROM placement WHERE id=%s FOR UPDATE", (pid,)).fetchone()
    if placement is None:
        raise NotFound()
    if placement["state"] != "ACTIVE":
        raise BusinessError("PLACEMENT_NOT_ACTIVE", placement["state"])
    return placement


def _segment(ctx_or_cur, pid: int, sid: int, *, lock: bool = False) -> dict:
    execute = ctx_or_cur.execute
    row = execute(
        "SELECT * FROM placement_segment WHERE id=%s AND placement_id=%s" + (" FOR UPDATE" if lock else ""),
        (sid, pid),
    ).fetchone()
    if row is None:
        raise NotFound()
    return row


def active_segment(cur, pid: int) -> dict | None:
    return cur.execute(
        "SELECT * FROM placement_segment WHERE placement_id=%s AND status='ACTIVE'", (pid,)
    ).fetchone()


def has_segments(cur, pid: int) -> bool:
    return cur.execute(
        "SELECT EXISTS (SELECT 1 FROM placement_segment WHERE placement_id=%s) AS present", (pid,)
    ).fetchone()["present"]


def _validate_segment_fields(ctx: CommandContext, data: dict) -> dict:
    unit = _clean(data.get("unit"), "unit", 160)
    responsibilities = _clean(data.get("responsibilities"), "responsibilities", 5000)
    modality = data.get("modality")
    if modality not in MODALITIES:
        raise BusinessError("SEGMENT_MODALITY_INVALID")
    start, end = data.get("start_date"), data.get("end_date")
    if not isinstance(start, dt.date) or not isinstance(end, dt.date) or end < start:
        raise BusinessError("SEGMENT_DATES_INVALID")
    expected = data.get("expected_hours")
    if expected is not None and (not math.isfinite(float(expected)) or float(expected) <= 0):
        raise BusinessError("SEGMENT_EXPECTED_HOURS_INVALID")
    org = ctx.execute("SELECT id FROM host_org WHERE id=%s", (data.get("host_org_id"),)).fetchone()
    if org is None:
        raise BusinessError("SEGMENT_ORGANIZATION_INVALID")
    supervisor_id = data.get("workplace_supervisor_id")
    supervisor = ctx.execute(
        """SELECT 1 FROM user_account u JOIN role_assignment ra ON ra.user_id=u.id
           WHERE u.id=%s AND u.is_active AND ra.role='WORKPLACE_SUPERVISOR' AND ra.host_org_id=%s""",
        (supervisor_id, org["id"]),
    ).fetchone()
    if supervisor is None:
        raise BusinessError("SEGMENT_SUPERVISOR_INVALID",
                            "El supervisor debe pertenecer a la organización del segmento.")
    return {"host_org_id": org["id"], "unit": unit, "workplace_supervisor_id": supervisor_id,
            "start_date": start, "end_date": end, "modality": modality,
            "responsibilities": responsibilities, "expected_hours": expected}


def _insert_segment(ctx: CommandContext, pid: int, fields: dict, origin: str) -> dict:
    seq = ctx.execute(
        "SELECT coalesce(max(sequence_no),0)+1 AS n FROM placement_segment WHERE placement_id=%s", (pid,)
    ).fetchone()["n"]
    segment = ctx.execute(
        """INSERT INTO placement_segment(placement_id, sequence_no, host_org_id, unit, workplace_supervisor_id,
             start_date, end_date, modality, responsibilities, expected_hours, origin, status, created_by)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'PLANNED',%s) RETURNING id, sequence_no""",
        (pid, seq, fields["host_org_id"], fields["unit"], fields["workplace_supervisor_id"],
         fields["start_date"], fields["end_date"], fields["modality"], fields["responsibilities"],
         fields["expected_hours"], origin, ctx.actor_id),
    ).fetchone()
    _instantiate_conditions(ctx, pid, segment["id"])
    return segment


def _instantiate_conditions(ctx: CommandContext, pid: int, sid: int) -> None:
    """CR-05-BR-02: enablement conditions come from the program's configured
    activation policy (the same institutional source used for the placement);
    no additional institutional requirement is invented here."""
    program = ctx.execute(
        """SELECT pr.code FROM placement p JOIN application a ON a.id=p.application_id
           JOIN role_assignment ra ON ra.user_id=a.student_id AND ra.role='STUDENT'
           JOIN academic_program pr ON pr.id=ra.program_id WHERE p.id=%s ORDER BY ra.id LIMIT 1""",
        (pid,),
    ).fetchone()
    policy = policies.latest_policy(ctx.cur, program["code"], "ACTIVATION") if program else None
    if policy is None:
        return
    for condition in policy["conditions"]:
        if condition["type"] == "REQUIRE_DOCUMENTS":
            for kind in condition["value"]:
                ctx.execute(
                    """INSERT INTO placement_segment_condition(segment_id, kind, source_policy_version_id)
                       VALUES (%s,%s,%s) ON CONFLICT DO NOTHING""",
                    (sid, kind, policy["id"]),
                )
        elif condition["type"] == "SUPERVISORS_ASSIGNED" and condition["value"]:
            # The segment cannot be created without a validated supervisor of its organization.
            ctx.execute(
                """INSERT INTO placement_segment_condition(segment_id, kind, source_policy_version_id,
                     status, confirmed_by, confirmed_at, reference)
                   VALUES (%s,'SUPERVISOR_ASSIGNED',%s,'SATISFIED',%s,clock_timestamp(),
                     'Supervisor validado contra la organización del segmento') ON CONFLICT DO NOTHING""",
                (sid, policy["id"], ctx.actor_id),
            )


def _authorize_manager(ctx: CommandContext, pid: int) -> dict:
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "placement:read", pid)
    authz.authorize(ctx.cur, subj, "segment:manage", pid)
    return subj


def create_segment(ctx: CommandContext, pid: int, data: dict) -> dict:
    """Plan a new rotation inside the same academic placement (status PLANNED)."""
    _authorize_manager(ctx, pid)
    _lock_active_placement(ctx, pid)
    fields = _validate_segment_fields(ctx, data)

    def run():
        return _insert_segment(ctx, pid, fields, "ROTATION")
    segment = _gate(run)
    audit.write(ctx.cur, "segment.planned", "placement", pid, None,
                {"segment_id": segment["id"], "sequence_no": segment["sequence_no"],
                 "host_org_id": fields["host_org_id"], "origin": "ROTATION"})
    return {"segment_id": segment["id"], "sequence_no": segment["sequence_no"], "status": "PLANNED"}


def confirm_condition(ctx: CommandContext, pid: int, sid: int, condition_id: int, reference: str) -> None:
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "segment_condition:confirm", pid)
    _lock_active_placement(ctx, pid)
    segment = _segment(ctx, pid, sid, lock=True)
    if segment["status"] != "PLANNED":
        raise BusinessError("SEGMENT_NOT_PLANNED", segment["status"])
    clean_reference = _clean(reference, "reference", 500)
    condition = ctx.execute(
        "SELECT * FROM placement_segment_condition WHERE id=%s AND segment_id=%s FOR UPDATE",
        (condition_id, sid),
    ).fetchone()
    if condition is None:
        raise NotFound()
    if condition["status"] != "REQUIRED":
        raise BusinessError("SEGMENT_CONDITION_ALREADY_SATISFIED")
    ctx.execute(
        """UPDATE placement_segment_condition SET status='SATISFIED', confirmed_by=%s,
           confirmed_at=clock_timestamp(), reference=%s WHERE id=%s""",
        (ctx.actor_id, clean_reference, condition_id),
    )
    audit.write(ctx.cur, "segment.condition_satisfied", "placement", pid,
                {"segment_id": sid, "kind": condition["kind"], "status": "REQUIRED"},
                {"segment_id": sid, "kind": condition["kind"], "status": "SATISFIED"})


def segment_unmet_conditions(cur, sid: int) -> list[str]:
    return [row["kind"] for row in cur.execute(
        "SELECT kind FROM placement_segment_condition WHERE segment_id=%s AND status<>'SATISFIED' ORDER BY id",
        (sid,),
    ).fetchall()]


def activate_segment(ctx: CommandContext, pid: int, sid: int) -> None:
    """CR-05-BR-02: explicit activation; completing a previous segment never does this."""
    _authorize_manager(ctx, pid)
    _lock_active_placement(ctx, pid)
    segment = _segment(ctx, pid, sid, lock=True)
    if segment["status"] != "PLANNED":
        raise BusinessError("SEGMENT_NOT_PLANNED", segment["status"])
    unmet = segment_unmet_conditions(ctx.cur, sid)
    if unmet:
        raise BusinessError("SEGMENT_CONDITIONS_UNMET", unmet)
    current = active_segment(ctx.cur, pid)
    if current is not None:
        raise BusinessError("SEGMENT_ALREADY_ACTIVE", {"active_segment_id": current["id"]})

    def run():
        ctx.execute(
            """UPDATE placement_segment SET status='ACTIVE', activated_at=clock_timestamp(), activated_by=%s
               WHERE id=%s""",
            (ctx.actor_id, sid),
        )
    _gate(run)
    audit.write(ctx.cur, "segment.activated", "placement", pid,
                {"segment_id": sid, "status": "PLANNED"}, {"segment_id": sid, "status": "ACTIVE"})


def _end_date(segment: dict, ended_on: dt.date | None) -> dt.date:
    if ended_on is None:
        return max(segment["start_date"], min(dt.date.today(), segment["end_date"]))
    if ended_on < segment["start_date"] or ended_on > segment["end_date"]:
        raise BusinessError("SEGMENT_END_DATE_INVALID")
    return ended_on


def _complete_segment_row(ctx: CommandContext, pid: int, segment: dict, ended_on: dt.date | None) -> None:
    final_required = ctx.execute(
        """SELECT EXISTS (SELECT 1 FROM completion_requirement WHERE placement_id=%s
           AND kind='FINAL_EVALUATION' AND mandatory) AS required""",
        (pid,),
    ).fetchone()["required"]
    if final_required and not ctx.execute(
        """SELECT EXISTS (SELECT 1 FROM placement_evaluation WHERE placement_id=%s
           AND segment_id=%s AND kind='FINAL') AS present""",
        (pid, segment["id"]),
    ).fetchone()["present"]:
        raise BusinessError("SEGMENT_FINAL_EVALUATION_MISSING", {"segment_id": segment["id"]})
    end = _end_date(segment, ended_on)

    def run():
        ctx.execute(
            """UPDATE placement_segment SET status='COMPLETED', ended_on=%s, ended_at=clock_timestamp(),
               ended_by=%s, work_recognition='ACCEPTED_HOURS_RECOGNIZED' WHERE id=%s""",
            (end, ctx.actor_id, segment["id"]),
        )
    _gate(run)
    audit.write(ctx.cur, "segment.completed", "placement", pid,
                {"segment_id": segment["id"], "status": "ACTIVE"},
                {"segment_id": segment["id"], "status": "COMPLETED", "ended_on": end.isoformat()})


def complete_segment(ctx: CommandContext, pid: int, sid: int, ended_on: dt.date | None = None) -> None:
    _authorize_manager(ctx, pid)
    _lock_active_placement(ctx, pid)
    segment = _segment(ctx, pid, sid, lock=True)
    if segment["status"] != "ACTIVE":
        raise BusinessError("SEGMENT_NOT_ACTIVE", segment["status"])
    _complete_segment_row(ctx, pid, segment, ended_on)


def auto_complete_single_segment(ctx: CommandContext, pid: int) -> None:
    """Keep the E3 single-segment flow: confirming completion of a practice that
    has exactly one (non-cancelled) segment closes that segment in the same
    transaction. Multi-segment practices require explicit segment closure and an
    approved combined-experience review."""
    rows = ctx.execute(
        "SELECT * FROM placement_segment WHERE placement_id=%s AND status<>'CANCELLED' FOR UPDATE", (pid,),
    ).fetchall()
    if len(rows) == 1 and rows[0]["status"] == "ACTIVE":
        _complete_segment_row(ctx, pid, rows[0], None)


def terminate_segment(ctx: CommandContext, pid: int, sid: int, *, ended_on: dt.date,
                      reason_shared: str, reason_internal: str | None,
                      work_recognition: str, recognition_note: str | None) -> None:
    """CR-05-BR-08: early termination keeps hours, evaluations and incidents and
    records the reason and the decision on recognizing the work."""
    _authorize_manager(ctx, pid)
    _lock_active_placement(ctx, pid)
    segment = _segment(ctx, pid, sid, lock=True)
    if segment["status"] != "ACTIVE":
        raise BusinessError("SEGMENT_NOT_ACTIVE", segment["status"])
    if work_recognition not in RECOGNITION:
        raise BusinessError("SEGMENT_RECOGNITION_INVALID")
    if ended_on < segment["start_date"] or ended_on > segment["end_date"] or ended_on > dt.date.today():
        raise BusinessError("SEGMENT_END_DATE_INVALID")
    shared = _clean(reason_shared, "reason_shared", 1000)
    internal = _clean(reason_internal, "reason_internal", 3000, required=False)
    note = _clean(recognition_note, "recognition_note", 1000, required=False)

    def run():
        ctx.execute(
            """UPDATE placement_segment SET status='TERMINATED_EARLY', ended_on=%s, ended_at=clock_timestamp(),
               ended_by=%s, end_reason_shared=%s, end_reason_internal=%s, work_recognition=%s,
               recognition_note=%s WHERE id=%s""",
            (ended_on, ctx.actor_id, shared, internal, work_recognition, note, sid),
        )
    _gate(run)
    # The internal reason is intentionally kept out of the audit payload.
    audit.write(ctx.cur, "segment.terminated_early", "placement", pid,
                {"segment_id": sid, "status": "ACTIVE"},
                {"segment_id": sid, "status": "TERMINATED_EARLY", "ended_on": ended_on.isoformat(),
                 "work_recognition": work_recognition})


def cancel_segment(ctx: CommandContext, pid: int, sid: int, reason_shared: str) -> None:
    _authorize_manager(ctx, pid)
    _lock_active_placement(ctx, pid)
    segment = _segment(ctx, pid, sid, lock=True)
    if segment["status"] != "PLANNED":
        raise BusinessError("SEGMENT_NOT_PLANNED", segment["status"])
    shared = _clean(reason_shared, "reason_shared", 1000)

    def run():
        ctx.execute(
            """UPDATE placement_segment SET status='CANCELLED', ended_at=clock_timestamp(), ended_by=%s,
               end_reason_shared=%s WHERE id=%s""",
            (ctx.actor_id, shared, sid),
        )
    _gate(run)
    audit.write(ctx.cur, "segment.cancelled", "placement", pid,
                {"segment_id": sid, "status": "PLANNED"}, {"segment_id": sid, "status": "CANCELLED"})


def transfer(ctx: CommandContext, pid: int, from_sid: int, *, effective_date: dt.date,
             reason_shared: str, reason_internal: str | None, prior_work_treatment: str,
             destination: dict) -> dict:
    """CR-05-BR-05: one atomic, audited operation. The origin segment is closed
    (TRANSFERRED) without rewriting its records; the destination is a new PLANNED
    segment that still has to meet its own enablement conditions (BR-02)."""
    _authorize_manager(ctx, pid)
    _lock_active_placement(ctx, pid)
    origin = _segment(ctx, pid, from_sid, lock=True)
    if origin["status"] != "ACTIVE":
        raise BusinessError("SEGMENT_NOT_ACTIVE", origin["status"])
    if prior_work_treatment not in RECOGNITION:
        raise BusinessError("TRANSFER_TREATMENT_INVALID")
    if effective_date < origin["start_date"] or effective_date > dt.date.today():
        raise BusinessError("TRANSFER_EFFECTIVE_DATE_INVALID")
    shared = _clean(reason_shared, "reason_shared", 1000)
    internal = _clean(reason_internal, "reason_internal", 3000, required=False)
    fields = _validate_segment_fields(ctx, destination)
    if fields["start_date"] < effective_date:
        raise BusinessError("TRANSFER_DESTINATION_DATES_INVALID",
                            "El destino no puede comenzar antes de la fecha de efecto.")

    def run():
        ctx.execute(
            """UPDATE placement_segment SET status='TRANSFERRED', ended_on=%s, ended_at=clock_timestamp(),
               ended_by=%s, end_reason_shared=%s, end_reason_internal=%s, work_recognition=%s
               WHERE id=%s""",
            (effective_date, ctx.actor_id, shared, internal, prior_work_treatment, from_sid),
        )
        destination_row = _insert_segment(ctx, pid, fields, "TRANSFER")
        record = ctx.execute(
            """INSERT INTO placement_transfer(placement_id, from_segment_id, to_segment_id, effective_date,
                 reason_shared, reason_internal, prior_work_treatment, approved_by)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id, approved_at""",
            (pid, from_sid, destination_row["id"], effective_date, shared, internal,
             prior_work_treatment, ctx.actor_id),
        ).fetchone()
        return destination_row, record
    destination_row, record = _gate(run)
    audit.write(ctx.cur, "segment.transferred", "placement", pid,
                {"segment_id": from_sid, "status": "ACTIVE"},
                {"transfer_id": record["id"], "from_segment_id": from_sid,
                 "to_segment_id": destination_row["id"], "effective_date": effective_date.isoformat(),
                 "prior_work_treatment": prior_work_treatment, "approved_by": ctx.actor_id})
    return {"transfer_id": record["id"], "to_segment_id": destination_row["id"],
            "to_sequence_no": destination_row["sequence_no"], "status": "PLANNED"}


def review_hours(ctx: CommandContext, pid: int, entry_id: int, *, decision: str,
                 accepted_hours: float | None, reason_code: str | None, reason: str | None) -> dict:
    """CR-05-BR-04: reported hours become accepted only through an explicit review."""
    if decision not in REVIEW_DECISIONS:
        raise BusinessError("HOURS_REVIEW_DECISION_INVALID")
    if reason_code is not None and reason_code not in REVIEW_REASON_CODES:
        raise BusinessError("HOURS_REVIEW_REASON_INVALID")
    clean_reason = _clean(reason, "reason", 1000, required=decision != "ACCEPTED")
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "hours:review", pid)
    _lock_active_placement(ctx, pid)
    entry = ctx.execute(
        "SELECT * FROM progress_entry WHERE id=%s AND placement_id=%s", (entry_id, pid),
    ).fetchone()
    if entry is None:
        raise NotFound()
    if decision == "ACCEPTED":
        accepted = float(entry["hours"]) if accepted_hours is None else float(accepted_hours)
        if not math.isfinite(accepted) or accepted <= 0 or accepted > float(entry["hours"]):
            raise BusinessError("HOURS_REVIEW_INVALID", "Las horas aceptadas no pueden superar las reportadas.")
    else:
        accepted = None
    # A workplace supervisor acting as configured reviewer reviews only the
    # entries of the segment they currently supervise.
    if not _reviews_any_segment(ctx.cur, subj, pid):
        active = active_segment(ctx.cur, pid)
        if active is None or entry["segment_id"] != active["id"] or active["workplace_supervisor_id"] != subj["id"]:
            raise BusinessError("HOURS_REVIEW_OUTSIDE_SEGMENT")

    def run():
        return ctx.execute(
            """INSERT INTO progress_entry_review(entry_id, decision, accepted_hours, reason_code, reason, reviewer_id)
               VALUES (%s,%s,%s,%s,%s,%s) RETURNING id, reviewed_at""",
            (entry_id, decision, accepted, reason_code, clean_reason, ctx.actor_id),
        ).fetchone()
    record = _gate(run)
    audit.write(ctx.cur, "progress.hours_reviewed", "placement", pid, None,
                {"entry_id": entry_id, "segment_id": entry["segment_id"], "decision": decision,
                 "accepted_hours": accepted, "reason_code": reason_code})
    return {"review_id": record["id"], "decision": decision, "accepted_hours": accepted,
            "reviewed_at": record["reviewed_at"]}


def _reviews_any_segment(cur, subj: dict, pid: int) -> bool:
    """University reviewers (faculty/coordinators) may review entries of any segment."""
    from app.config import get_settings

    configured = set(get_settings().hours_reviewer_roles) - {"WORKPLACE_SUPERVISOR"}
    if not any(role["role"] in configured for role in subj["roles"]):
        return False
    restricted = {**subj, "roles": [role for role in subj["roles"] if role["role"] in configured]}
    return authz.can_perform(cur, restricted, "hours:review", pid)


def record_experience_review(ctx: CommandContext, pid: int, decision: str, rationale: str) -> dict:
    """CR-05-BR-07: academic review of the combined experience (all segments)."""
    if decision not in EXPERIENCE_DECISIONS:
        raise BusinessError("EXPERIENCE_REVIEW_DECISION_INVALID")
    clean_rationale = (rationale or "").strip()
    if not clean_rationale or len(clean_rationale) > 3000:
        raise BusinessError("EXPERIENCE_REVIEW_RATIONALE_REQUIRED")
    subj = authz.subject(ctx.cur, ctx.actor_id)
    authz.authorize(ctx.cur, subj, "experience:review", pid)
    _lock_active_placement(ctx, pid)
    open_rows = ctx.execute(
        "SELECT count(*) AS n FROM placement_segment WHERE placement_id=%s AND status IN ('PLANNED','ACTIVE')",
        (pid,),
    ).fetchone()["n"]
    if open_rows:
        raise BusinessError("SEGMENTS_STILL_OPEN", open_rows)
    record = ctx.execute(
        """INSERT INTO placement_experience_review(placement_id, decision, rationale, reviewer_id)
           VALUES (%s,%s,%s,%s) RETURNING id, reviewed_at""",
        (pid, decision, clean_rationale, ctx.actor_id),
    ).fetchone()
    audit.write(ctx.cur, "placement.experience_reviewed", "placement", pid, None,
                {"review_id": record["id"], "decision": decision})
    return {"review_id": record["id"], "decision": decision, "reviewed_at": record["reviewed_at"]}


# --------------------------------------------------------------------------- reads

def is_external_only(subj: dict) -> bool:
    return bool(subj["roles"]) and all(role["role"] in authz.EXTERNAL for role in subj["roles"])


def visible_segment_ids(cur, subj: dict, pid: int) -> set[int] | None:
    """None = every segment. External users see only the segments of their own
    current relationship (supervisor of an open segment / member of its org)."""
    if not is_external_only(subj):
        return None
    supervisor = any(role["role"] == "WORKPLACE_SUPERVISOR" for role in subj["roles"])
    member_orgs = [role["host_org_id"] for role in subj["roles"] if role["role"] == "HOST_ORG_MEMBER"]
    rows = cur.execute(
        """SELECT id FROM placement_segment WHERE placement_id=%s AND (
             (%s AND workplace_supervisor_id=%s AND status IN ('PLANNED','ACTIVE')) OR
             (host_org_id = ANY(%s) AND status <> 'CANCELLED'))""",
        (pid, supervisor, subj["id"], member_orgs),
    ).fetchall()
    return {row["id"] for row in rows}


def filter_by_segment(rows: list[dict], visible: set[int] | None) -> list[dict]:
    if visible is None:
        return rows
    return [row for row in rows if row.get("segment_id") in visible]


def hours_summary(cur, pid: int, visible: set[int] | None = None) -> dict:
    """Reported vs pending vs accepted vs rejected/disputed, per segment and consolidated."""
    rows = cur.execute(
        """SELECT pe.segment_id, s.sequence_no, s.work_recognition,
                  coalesce(sum(pe.hours),0) AS reported,
                  coalesce(sum(pe.hours) FILTER (WHERE r.decision IS NULL),0) AS pending,
                  coalesce(sum(r.accepted_hours) FILTER (WHERE r.decision='ACCEPTED'),0) AS accepted,
                  coalesce(sum(pe.hours) FILTER (WHERE r.decision='REJECTED'),0) AS rejected,
                  coalesce(sum(pe.hours) FILTER (WHERE r.decision='DISPUTED'),0) AS disputed
           FROM progress_entry pe
           LEFT JOIN LATERAL (SELECT decision, accepted_hours FROM progress_entry_review rv
                              WHERE rv.entry_id=pe.id ORDER BY rv.id DESC LIMIT 1) r ON true
           LEFT JOIN placement_segment s ON s.id=pe.segment_id
           WHERE pe.placement_id=%s
           GROUP BY pe.segment_id, s.sequence_no, s.work_recognition
           ORDER BY s.sequence_no NULLS FIRST""",
        (pid,),
    ).fetchall()
    segments = [{**row, "counts_toward_total": row["work_recognition"] != "NOT_RECOGNIZED"}
                for row in rows if visible is None or row["segment_id"] in visible]
    totals = cur.execute(
        "SELECT placement_accepted_hours(%s) AS accepted, placement_pending_hour_entries(%s) AS pending_entries",
        (pid, pid),
    ).fetchone()
    if visible is not None:
        consolidated = sum((row["accepted"] for row in segments if row["counts_toward_total"]), start=0)
        return {"segments": segments, "reported_total": sum((r["reported"] for r in segments), start=0),
                "accepted_total": consolidated, "pending_entries": None, "scope": "SEGMENT"}
    return {"segments": segments,
            "reported_total": sum((r["reported"] for r in segments), start=0),
            "accepted_total": totals["accepted"],
            "pending_entries": totals["pending_entries"],
            "scope": "PLACEMENT"}


def list_segments(cur, subj: dict, pid: int) -> list[dict]:
    authz.authorize(cur, subj, "placement:read", pid)
    visible = visible_segment_ids(cur, subj, pid)
    read_internal = authz.can_perform(cur, subj, "segment:read_internal", pid)
    rows = cur.execute(
        """SELECT s.id, s.sequence_no, s.host_org_id, org.name AS host_org_name, s.unit,
                  s.workplace_supervisor_id, sup.display_name AS workplace_supervisor_name,
                  s.start_date, s.end_date, s.modality, s.responsibilities, s.expected_hours,
                  s.origin, s.status, s.activated_at, s.ended_on, s.ended_at, s.end_reason_shared,
                  s.end_reason_internal, s.work_recognition, s.recognition_note
           FROM placement_segment s JOIN host_org org ON org.id=s.host_org_id
           LEFT JOIN user_account sup ON sup.id=s.workplace_supervisor_id
           WHERE s.placement_id=%s ORDER BY s.sequence_no""",
        (pid,),
    ).fetchall()
    out = []
    for row in rows:
        if visible is not None and row["id"] not in visible:
            continue
        item = dict(row)
        if not read_internal:
            item.pop("end_reason_internal")  # CR-05-BR-09
        item["conditions"] = cur.execute(
            """SELECT c.id, c.kind, c.status, c.confirmed_at, c.reference, u.display_name AS confirmed_by
               FROM placement_segment_condition c LEFT JOIN user_account u ON u.id=c.confirmed_by
               WHERE c.segment_id=%s ORDER BY c.id""",
            (row["id"],),
        ).fetchall()
        item["status_history"] = cur.execute(
            """SELECT h.from_status, h.to_status, h.changed_at, u.display_name AS actor_name
               FROM placement_segment_status_history h LEFT JOIN user_account u ON u.id=h.actor_id
               WHERE h.segment_id=%s ORDER BY h.id""",
            (row["id"],),
        ).fetchall()
        out.append(item)
    return out


def segment_options(cur, subj: dict, pid: int) -> list[dict]:
    """Organizations with their active workplace supervisors, for segment managers only."""
    authz.authorize(cur, subj, "placement:read", pid)
    authz.authorize(cur, subj, "segment:manage", pid)
    rows = cur.execute(
        """SELECT org.id AS host_org_id, org.name AS host_org_name, u.id AS supervisor_id,
                  u.display_name AS supervisor_name
           FROM host_org org
           JOIN role_assignment ra ON ra.host_org_id=org.id AND ra.role='WORKPLACE_SUPERVISOR'
           JOIN user_account u ON u.id=ra.user_id AND u.is_active
           ORDER BY org.name, u.display_name""",
    ).fetchall()
    options: dict[int, dict] = {}
    for row in rows:
        option = options.setdefault(row["host_org_id"], {"id": row["host_org_id"], "name": row["host_org_name"],
                                                          "supervisors": []})
        option["supervisors"].append({"id": row["supervisor_id"], "display_name": row["supervisor_name"]})
    return list(options.values())


def list_transfers(cur, subj: dict, pid: int) -> list[dict]:
    authz.authorize(cur, subj, "placement:read", pid)
    visible = visible_segment_ids(cur, subj, pid)
    read_internal = authz.can_perform(cur, subj, "segment:read_internal", pid)
    rows = cur.execute(
        """SELECT t.id, t.from_segment_id, f.sequence_no AS from_sequence_no, t.to_segment_id,
                  d.sequence_no AS to_sequence_no, t.effective_date, t.reason_shared, t.reason_internal,
                  t.prior_work_treatment, t.approved_at, u.display_name AS approved_by
           FROM placement_transfer t
           JOIN placement_segment f ON f.id=t.from_segment_id
           JOIN placement_segment d ON d.id=t.to_segment_id
           JOIN user_account u ON u.id=t.approved_by
           WHERE t.placement_id=%s ORDER BY t.id""",
        (pid,),
    ).fetchall()
    out = []
    for row in rows:
        if visible is not None and row["from_segment_id"] not in visible and row["to_segment_id"] not in visible:
            continue
        item = dict(row)
        if not read_internal:
            item.pop("reason_internal")  # CR-05-BR-09
        out.append(item)
    return out


def list_experience_reviews(cur, subj: dict, pid: int) -> list[dict]:
    authz.authorize(cur, subj, "placement:read", pid)
    if is_external_only(subj):
        return []
    return cur.execute(
        """SELECT r.id, r.decision, r.rationale, r.reviewed_at, u.display_name AS reviewer
           FROM placement_experience_review r JOIN user_account u ON u.id=r.reviewer_id
           WHERE r.placement_id=%s ORDER BY r.id DESC""",
        (pid,),
    ).fetchall()


def segment_gate_status(cur, pid: int) -> dict:
    """Segment-level closure conditions recomputed from persisted rows (BR-07)."""
    counts = cur.execute(
        """SELECT count(*) FILTER (WHERE status IN ('PLANNED','ACTIVE')) AS open_segments,
                  count(*) FILTER (WHERE status <> 'CANCELLED') AS effective_segments,
                  count(*) FILTER (WHERE status = 'ACTIVE') AS active_segments,
                  max(ended_at) AS last_ended_at
           FROM placement_segment WHERE placement_id=%s""",
        (pid,),
    ).fetchone()
    pending = cur.execute("SELECT placement_pending_hour_entries(%s) AS n", (pid,)).fetchone()["n"]
    missing_evaluations = [row["sequence_no"] for row in cur.execute(
        """SELECT s.sequence_no FROM placement_segment s
           WHERE s.placement_id=%s AND s.status='COMPLETED' AND s.origin<>'MIGRATED_SINGLE'
             AND EXISTS (SELECT 1 FROM completion_requirement cr WHERE cr.placement_id=s.placement_id
                         AND cr.kind='FINAL_EVALUATION' AND cr.mandatory)
             AND NOT EXISTS (SELECT 1 FROM placement_evaluation ev WHERE ev.segment_id=s.id AND ev.kind='FINAL')
           ORDER BY s.sequence_no""",
        (pid,),
    ).fetchall()]
    review_required = counts["effective_segments"] > 1
    latest = cur.execute(
        """SELECT decision, reviewed_at FROM placement_experience_review
           WHERE placement_id=%s ORDER BY id DESC LIMIT 1""",
        (pid,),
    ).fetchone()
    review_ok = (not review_required) or (
        latest is not None and latest["decision"] == "APPROVED"
        and (counts["last_ended_at"] is None or latest["reviewed_at"] >= counts["last_ended_at"])
    )
    return {"open_segments": counts["open_segments"], "active_segments": counts["active_segments"],
            "effective_segments": counts["effective_segments"], "pending_hour_entries": pending,
            "segments_missing_final_evaluation": missing_evaluations,
            "combined_review_required": review_required, "combined_review_approved": review_ok}


def segment_blockers(cur, pid: int, *, allow_single_active: bool) -> list[str]:
    status = segment_gate_status(cur, pid)
    blockers = []
    open_segments = status["open_segments"]
    if allow_single_active and status["effective_segments"] == 1 and status["active_segments"] == 1:
        open_segments -= 1
    if open_segments:
        blockers.append("SEGMENTS_OPEN")
    if status["pending_hour_entries"]:
        blockers.append("HOURS_PENDING_REVIEW")
    if status["segments_missing_final_evaluation"]:
        blockers.append("SEGMENT_FINAL_EVALUATION")
    if not status["combined_review_approved"]:
        blockers.append("COMBINED_EXPERIENCE_REVIEW")
    return blockers
