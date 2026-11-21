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
