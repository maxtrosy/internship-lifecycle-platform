"""Operational aggregates derived from persisted lifecycle tables."""
from __future__ import annotations

import psycopg

from app.errors import Forbidden


def _scope(subj: dict, program_id: int | None, organization_id: int | None,
           opportunity_state: str | None) -> tuple[str, list]:
    if any(role["role"] == "EXPERIENTIAL_COORDINATOR" for role in subj["roles"]):
        parts = ["TRUE"]
        params: list[object] = []
        programs: list[int] | None = None
    else:
        programs = sorted({
        role["program_id"] for role in subj["roles"]
        if role["role"] == "PROGRAM_COORDINATOR" and role["program_id"] is not None
        })
        if not programs:
            raise Forbidden("operational reports are limited to program and experiential coordinators")
        parts = []
        params = []
        if program_id is not None and program_id not in programs:
            raise Forbidden("the requested program is outside the caller's report scope")
        if program_id is None:
            parts.append("o.program_id = ANY(%s)")
            params.append(programs)
    if program_id is not None:
        parts.append("o.program_id = %s")
        params.append(program_id)
    if organization_id is not None:
        parts.append("o.host_org_id = %s")
        params.append(organization_id)
    if opportunity_state:
        parts.append("o.state = %s")
        params.append(opportunity_state)
    return " AND ".join(parts) if parts else "TRUE", params


def operations(cur: psycopg.Cursor, subj: dict, *, program_id: int | None = None,
               organization_id: int | None = None, placement_state: str | None = None,
               opportunity_state: str | None = None, application_state: str | None = None) -> dict:
    where, params = _scope(subj, program_id, organization_id, opportunity_state)
    placement_filter = " AND p.state=%s" if placement_state else ""
    application_filter = " AND a.state=%s" if application_state else ""
    placement_params = [*params, *([placement_state] if placement_state else [])]
    application_params = [*params, *([application_state] if application_state else [])]

    def grouped(sql: str, query_params: list | None = None) -> list[dict]:
        return cur.execute(sql.format(scope=where), params if query_params is None else query_params).fetchall()

    placement_states = grouped(
        """SELECT p.state, count(*)::int AS count
           FROM placement p JOIN application a ON a.id=p.application_id
           JOIN opportunity o ON o.id=a.opportunity_id WHERE {scope}{placement_filter}
           GROUP BY p.state ORDER BY p.state"""
        .replace("{placement_filter}", placement_filter), placement_params,
    )
    opportunity_states = grouped(
        """SELECT o.state, count(*)::int AS count FROM opportunity o
           WHERE {scope} GROUP BY o.state ORDER BY o.state"""
    )
    application_states = grouped(
        """SELECT a.state, count(*)::int AS count FROM application a
           JOIN opportunity o ON o.id=a.opportunity_id WHERE {scope}{application_filter}
           GROUP BY a.state ORDER BY a.state"""
        .replace("{application_filter}", application_filter), application_params,
    )
    active = cur.execute(
        """SELECT count(*)::int AS count FROM placement p
           JOIN application a ON a.id=p.application_id JOIN opportunity o ON o.id=a.opportunity_id
           WHERE {scope}{application_filter} AND p.state='ACTIVE'{placement_filter}""".format(
               scope=where, application_filter=application_filter, placement_filter=placement_filter),
        [*params, *([application_state] if application_state else []), *([placement_state] if placement_state else [])],
    ).fetchone()["count"]
    pending_documents = cur.execute(
        """SELECT count(*)::int AS count FROM checklist_item ci
           JOIN placement p ON p.id=ci.placement_id JOIN application a ON a.id=p.application_id
           JOIN opportunity o ON o.id=a.opportunity_id
           WHERE {scope}{placement_filter}{application_filter} AND ci.mandatory AND ci.status <> 'APPROVED'
             AND p.state NOT IN ('CLOSED','REJECTED','CANCELLED')""".format(
                 scope=where, placement_filter=placement_filter, application_filter=application_filter),
        [*params, *([placement_state] if placement_state else []), *([application_state] if application_state else [])],
    ).fetchone()["count"]
    incidents = cur.execute(
        """SELECT count(*)::int AS count FROM placement_incident i
           JOIN placement p ON p.id=i.placement_id JOIN application a ON a.id=p.application_id
           JOIN opportunity o ON o.id=a.opportunity_id
           WHERE {scope}{placement_filter}{application_filter} AND i.status='REPORTED'""".format(
               scope=where, placement_filter=placement_filter, application_filter=application_filter),
        [*params, *([placement_state] if placement_state else []), *([application_state] if application_state else [])],
    ).fetchone()["count"]
    end_dates = grouped(
        """SELECT pv.end_date, count(*)::int AS placements
           FROM placement p JOIN application a ON a.id=p.application_id
           JOIN opportunity o ON o.id=a.opportunity_id
           JOIN placement_version pv ON pv.id=p.current_version_id
           WHERE {scope}{application_filter}{placement_filter} AND p.state='ACTIVE' AND pv.end_date >= CURRENT_DATE
           GROUP BY pv.end_date ORDER BY pv.end_date""".replace(
               "{application_filter}", application_filter).replace("{placement_filter}", placement_filter),
        [*params, *([application_state] if application_state else []), *([placement_state] if placement_state else [])],
    )
    programs = grouped(
        """SELECT ap.id AS program_id, ap.code AS program_code, ap.name AS program_name,
                  count(DISTINCT o.id)::int AS opportunities,
                  count(DISTINCT a.id)::int AS applications,
                  count(DISTINCT p.id)::int AS placements
           FROM opportunity o JOIN academic_program ap ON ap.id=o.program_id
           LEFT JOIN application a ON a.opportunity_id=o.id{application_join_filter}
           LEFT JOIN placement p ON p.application_id=a.id{placement_join_filter}
           WHERE {scope}
           GROUP BY ap.id, ap.code, ap.name ORDER BY ap.code""".replace(
               "{application_join_filter}", " AND a.state=%s" if application_state else "").replace(
               "{placement_join_filter}", " AND p.state=%s" if placement_state else ""),
        [*([application_state] if application_state else []), *([placement_state] if placement_state else []), *params],
    )
    organizations = grouped(
        """SELECT h.id AS organization_id, h.name AS organization,
                  count(DISTINCT o.id)::int AS opportunities,
                  count(DISTINCT a.id)::int AS applications,
                  count(DISTINCT p.id)::int AS placements
           FROM opportunity o JOIN host_org h ON h.id=o.host_org_id
           LEFT JOIN application a ON a.opportunity_id=o.id{application_join_filter}
           LEFT JOIN placement p ON p.application_id=a.id{placement_join_filter}
           WHERE {scope}
           GROUP BY h.id, h.name ORDER BY h.name""".replace(
               "{application_join_filter}", " AND a.state=%s" if application_state else "").replace(
               "{placement_join_filter}", " AND p.state=%s" if placement_state else ""),
        [*([application_state] if application_state else []), *([placement_state] if placement_state else []), *params],
    )
    return {
        "placements_by_state": placement_states,
        "opportunities_by_state": opportunity_states,
        "applications_by_state": application_states,
        "active_placements": active,
        "mandatory_documents_pending": pending_documents,
        "reported_incidents": incidents,
        "expected_end_dates": end_dates,
        "by_program": programs,
        "by_organization": organizations,
    }


def rotations(cur: psycopg.Cursor, subj: dict, *, program_id: int | None = None,
              organization_id: int | None = None) -> dict:
    """CR-05 aggregates (rotations, transfers, interruptions, accepted hours,
    missing evaluations, pending consolidations) with the same scope rules as
    ``operations``: program coordinators see their programs, the experiential
    coordinator sees every program, nobody else is allowed. Aggregates only;
    no names, reasons, evaluations or entry-level data are returned. The
    organization filter applies to the placement's opportunity, like
    ``operations``; a segment may run at another organization."""
    where, params = _scope(subj, program_id, organization_id, None)
    scoped = f"""
        WITH scoped AS (
          SELECT p.id AS placement_id, p.state AS placement_state, o.program_id
          FROM placement p JOIN application a ON a.id=p.application_id
          JOIN opportunity o ON o.id=a.opportunity_id WHERE {where}
        ), seg AS (
          SELECT s.*, sc.program_id, sc.placement_state FROM placement_segment s
          JOIN scoped sc ON sc.placement_id=s.placement_id
        ), per_placement AS (
          SELECT sc.placement_id, sc.program_id, sc.placement_state,
                 count(s.id) FILTER (WHERE s.status <> 'CANCELLED') AS effective,
                 count(s.id) FILTER (WHERE s.status IN ('PLANNED','ACTIVE')) AS open,
                 max(s.ended_at) AS last_ended_at
          FROM scoped sc LEFT JOIN placement_segment s ON s.placement_id=sc.placement_id
          GROUP BY sc.placement_id, sc.program_id, sc.placement_state
        ), consolidation AS (
          SELECT pp.*, (pp.placement_state='ACTIVE' AND pp.effective > 1 AND pp.open = 0 AND NOT EXISTS (
                   SELECT 1 FROM placement_experience_review r
                   WHERE r.placement_id=pp.placement_id AND r.decision='APPROVED'
                     AND r.id = (SELECT max(r2.id) FROM placement_experience_review r2
                                 WHERE r2.placement_id=pp.placement_id)
                     AND (pp.last_ended_at IS NULL OR r.reviewed_at >= pp.last_ended_at))) AS pending
          FROM per_placement pp
        )"""

    def one(select: str) -> dict:
        return cur.execute(scoped + select, params).fetchone()

    def many(select: str) -> list[dict]:
        return cur.execute(scoped + select, params).fetchall()

    placements = one(
        """SELECT count(*) FILTER (WHERE effective > 1)::int AS multi_segment_placements,
                  count(*) FILTER (WHERE effective = 1)::int AS single_segment_placements,
                  count(*) FILTER (WHERE pending)::int AS pending_consolidations
           FROM consolidation"""
    )
    segments_by_status = many(
        "SELECT status, count(*)::int AS count FROM seg GROUP BY status ORDER BY status"
    )
    active_rotations = one(
        """SELECT count(*)::int AS count FROM seg s
           WHERE s.status='ACTIVE' AND s.placement_state='ACTIVE' AND EXISTS (
             SELECT 1 FROM placement_segment o WHERE o.placement_id=s.placement_id
               AND o.id <> s.id AND o.status <> 'CANCELLED')"""
    )["count"]
    transfers = many(
        """SELECT t.prior_work_treatment AS treatment, count(*)::int AS count
           FROM placement_transfer t JOIN scoped sc ON sc.placement_id=t.placement_id
           GROUP BY t.prior_work_treatment ORDER BY t.prior_work_treatment"""
    )
    interruptions = many(
        """SELECT work_recognition AS recognition, count(*)::int AS count FROM seg
           WHERE status='TERMINATED_EARLY' GROUP BY work_recognition ORDER BY work_recognition"""
    )
    hours = one(
        """SELECT coalesce(sum(pe.hours),0) AS reported,
                  coalesce(sum(r.accepted_hours) FILTER (WHERE r.decision='ACCEPTED'
                    AND s.work_recognition IS DISTINCT FROM 'NOT_RECOGNIZED'),0) AS accepted,
                  count(pe.id) FILTER (WHERE (r.decision IS NULL OR r.decision='DISPUTED')
                    AND s.work_recognition IS DISTINCT FROM 'NOT_RECOGNIZED')::int AS pending_entries,
                  count(pe.id) FILTER (WHERE r.decision='DISPUTED')::int AS disputed_entries,
                  coalesce(sum(pe.hours) FILTER (WHERE s.work_recognition='NOT_RECOGNIZED'),0)
                    AS not_recognized
           FROM progress_entry pe JOIN scoped sc ON sc.placement_id=pe.placement_id
           LEFT JOIN LATERAL (SELECT decision, accepted_hours FROM progress_entry_review rv
                              WHERE rv.entry_id=pe.id ORDER BY rv.id DESC LIMIT 1) r ON true
           LEFT JOIN placement_segment s ON s.id=pe.segment_id"""
    )
    evaluations = one(
        """SELECT count(*) FILTER (WHERE s.status='ACTIVE')::int AS active_without_final,
                  count(*) FILTER (WHERE s.status='COMPLETED' AND s.origin <> 'MIGRATED_SINGLE')::int
                    AS completed_without_final
           FROM seg s
           WHERE s.status IN ('ACTIVE','COMPLETED')
             AND EXISTS (SELECT 1 FROM completion_requirement cr WHERE cr.placement_id=s.placement_id
                         AND cr.kind='FINAL_EVALUATION' AND cr.mandatory)
             AND NOT EXISTS (SELECT 1 FROM placement_evaluation ev
                             WHERE ev.segment_id=s.id AND ev.kind='FINAL')"""
    )
    by_program = many(
        """SELECT ap.id AS program_id, ap.code AS program_code, ap.name AS program_name,
                  count(*) FILTER (WHERE c.effective > 1)::int AS multi_segment_placements,
                  count(*) FILTER (WHERE c.pending)::int AS pending_consolidations,
                  (SELECT count(*) FROM placement_transfer t JOIN scoped sc ON sc.placement_id=t.placement_id
                   WHERE sc.program_id=ap.id)::int AS transfers,
                  (SELECT count(*) FROM seg s WHERE s.program_id=ap.id
                   AND s.status='TERMINATED_EARLY')::int AS interruptions
           FROM consolidation c JOIN academic_program ap ON ap.id=c.program_id
           GROUP BY ap.id, ap.code, ap.name ORDER BY ap.code"""
    )
    return {
        "multi_segment_placements": placements["multi_segment_placements"],
        "single_segment_placements": placements["single_segment_placements"],
        "active_rotations": active_rotations,
        "segments_by_status": segments_by_status,
        "transfers": sum(row["count"] for row in transfers),
        "transfers_by_treatment": transfers,
        "interruptions": sum(row["count"] for row in interruptions),
        "interruptions_by_recognition": interruptions,
        "hours": {
            "reported": float(hours["reported"]),
            "accepted": float(hours["accepted"]),
            "not_recognized": float(hours["not_recognized"]),
            "pending_entries": hours["pending_entries"],
            "disputed_entries": hours["disputed_entries"],
        },
        "active_segments_without_final_evaluation": evaluations["active_without_final"],
        "completed_segments_missing_final_evaluation": evaluations["completed_without_final"],
        "pending_consolidations": placements["pending_consolidations"],
        "by_program": by_program,
    }
