"""T-24: opportunity creation and role/relationship-scoped listing (C-03)."""
from __future__ import annotations

import pytest
import psycopg

from app import db
from app.errors import BusinessError, Forbidden, NotFound
from app.modules import authz
from app.modules.opportunities import service as opps
from tests.conftest import make_opportunity, seed_base


def test_t24_create_and_list(env):
    U = seed_base(env)
    with db.command(U["hm_alfa"]) as ctx:
        o1 = opps.create_opportunity(ctx, 1, U["P"]["ING-SIS"], "Alfa Role")
    with db.command(U["pc_sys"]) as ctx:
        o2 = opps.create_opportunity(ctx, 1, U["P"]["ING-SIS"], "Sys Role")

    with db.read() as cur:
        s1 = authz.subject(cur, U["s1"])
        hm_alfa = authz.subject(cur, U["hm_alfa"])
        hm_beta = authz.subject(cur, U["hm_beta"])
        pc_sys = authz.subject(cur, U["pc_sys"])
        assert {o["id"] for o in opps.list_opportunities(cur, s1)} == set()
        assert {o["id"] for o in opps.list_opportunities(cur, hm_alfa)} == {o1, o2}
        assert {o["id"] for o in opps.list_opportunities(cur, hm_beta)} == set()
        assert {o["id"] for o in opps.list_opportunities(cur, pc_sys)} == {o1, o2}
        assert all(o["state"] == "DRAFT" for o in opps.list_opportunities(cur, hm_alfa))


def test_t24_authorization(env):
    U = seed_base(env)
    with db.command(U["hm_beta"]) as ctx:
        with pytest.raises(Forbidden):
            opps.create_opportunity(ctx, 1, U["P"]["ING-SIS"], "Foreign")
    with db.command(U["pc_adm"]) as ctx:
        with pytest.raises(Forbidden):
            opps.create_opportunity(ctx, 1, U["P"]["ING-SIS"], "Foreign program")


def test_creation_catalogs_are_scoped_to_creator_relationships(env):
    U = seed_base(env)
    with db.read() as cur:
        employer = opps.list_creation_catalogs(cur, authz.subject(cur, U["hm_alfa"]))
        coordinator = opps.list_creation_catalogs(cur, authz.subject(cur, U["pc_sys"]))
        with pytest.raises(Forbidden):
            opps.list_creation_catalogs(cur, authz.subject(cur, U["s1"]))

    assert [org["name"] for org in employer["organizations"]] == ["Org Alfa (synthetic)"]
    assert {program["code"] for program in employer["programs"]} == {"ING-SIS", "ADM"}
    assert {org["name"] for org in coordinator["organizations"]} == {
        "Org Alfa (synthetic)", "Org Beta (synthetic)"
    }
    assert [program["code"] for program in coordinator["programs"]] == ["ING-SIS"]


def test_workplace_supervisor_catalog_is_scoped_to_opportunity_host(env):
    U = seed_base(env)
    opportunity_id = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa (synthetic)")
    env.admin.execute("UPDATE user_account SET is_active=false WHERE id=%s", (U["ws_alfa2"],))
    with db.read() as cur:
        supervisors = opps.list_workplace_supervisors(cur, authz.subject(cur, U["hm_alfa"]), opportunity_id)
        with pytest.raises(Forbidden):
            opps.list_workplace_supervisors(cur, authz.subject(cur, U["hm_beta"]), opportunity_id)
        with pytest.raises(Forbidden):
            opps.list_workplace_supervisors(cur, authz.subject(cur, U["s1"]), opportunity_id)
        with pytest.raises(NotFound):
            opps.list_workplace_supervisors(cur, authz.subject(cur, U["hm_alfa"]), 99999)

    assert [supervisor["display_name"] for supervisor in supervisors] == ["Workplace Sup Alfa"]


def test_review_and_publication_require_configured_related_authorities(env, monkeypatch):
    U = seed_base(env)
    with env.conn() as conn:
        with pytest.raises(psycopg.errors.RaiseException):
            conn.execute(
                "INSERT INTO opportunity(host_org_id,program_id,title,state) VALUES (1,%s,'Direct publish','PUBLISHED')",
                (U["P"]["ING-SIS"],),
            )
    monkeypatch.setenv("OPPORTUNITY_REVIEWER_ROLES", "PROGRAM_COORDINATOR")
    monkeypatch.setenv("OPPORTUNITY_PUBLISHER_ROLES", "EXPERIENTIAL_COORDINATOR")
    with db.command(U["hm_alfa"]) as ctx:
        opportunity_id = opps.create_opportunity(ctx, 1, U["P"]["ING-SIS"], "Review flow")
    with db.command(U["hm_alfa"]) as ctx:
        opps.submit_for_review(ctx, opportunity_id)
    with db.command(U["pc_adm"]) as ctx:
        with pytest.raises(Forbidden):
            opps.approve_for_publication(ctx, opportunity_id)
    with db.command(U["hm_alfa"]) as ctx:
        with pytest.raises(Forbidden):
            opps.approve_for_publication(ctx, opportunity_id)
    with db.command(U["pc_sys"]) as ctx:
        opps.approve_for_publication(ctx, opportunity_id)
    with db.command(U["pc_sys"]) as ctx:
        with pytest.raises(Forbidden):
            opps.publish_opportunity(ctx, opportunity_id)
    with db.command(U["ec1"]) as ctx:
        opps.publish_opportunity(ctx, opportunity_id)

    with db.read() as cur:
        student = authz.subject(cur, U["s1"])
        assert {o["id"] for o in opps.list_opportunities(cur, student)} == {opportunity_id}
        notices = cur.execute(
            "SELECT recipient_id, category FROM user_notification WHERE opportunity_id=%s",
            (opportunity_id,),
        ).fetchall()
    assert {(row["recipient_id"], row["category"]) for row in notices} == {
        (U["pc_sys"], "OPPORTUNITY_REVIEW"),
        (U["dual1"], "OPPORTUNITY_REVIEW"),
        (U["ec1"], "OPPORTUNITY_REVIEW"),
        (U["s1"], "OPPORTUNITY_PUBLISHED"),
        (U["s2"], "OPPORTUNITY_PUBLISHED"),
    }

    env.admin.execute(
        "INSERT INTO application(opportunity_id,student_id,state) VALUES (%s,%s,'SUBMITTED')",
        (opportunity_id, U["s1"]),
    )
    with db.command(U["hm_alfa"]) as ctx:
        opps.close_opportunity(ctx, opportunity_id)
    with db.read() as cur:
        owner = authz.subject(cur, U["s1"])
        unrelated = authz.subject(cur, U["s2"])
        assert {o["id"] for o in opps.list_opportunities(cur, owner)} == {opportunity_id}
        assert opps.list_opportunities(cur, unrelated) == []
        close_notice = cur.execute(
            "SELECT recipient_id, category FROM user_notification WHERE opportunity_id=%s AND category='OPPORTUNITY_CLOSED'",
            (opportunity_id,),
        ).fetchone()
    assert close_notice == {"recipient_id": U["s1"], "category": "OPPORTUNITY_CLOSED"}

    with env.conn() as conn:
        with pytest.raises(psycopg.errors.RaiseException):
            conn.execute("UPDATE opportunity SET state='DRAFT' WHERE id=%s", (opportunity_id,))

    with db.command(U["hm_alfa"]) as ctx:
        unconfigured_id = opps.create_opportunity(ctx, 1, U["P"]["ING-SIS"], "Unconfigured review")
    with db.command(U["hm_alfa"]) as ctx:
        opps.submit_for_review(ctx, unconfigured_id)
    monkeypatch.delenv("OPPORTUNITY_REVIEWER_ROLES", raising=False)
    with db.command(U["pc_sys"]) as ctx:
        with pytest.raises(BusinessError) as error:
            opps.approve_for_publication(ctx, unconfigured_id)
    assert error.value.code == "OPPORTUNITY_REVIEW_AUTHORITY_UNCONFIGURED"
    monkeypatch.setenv("OPPORTUNITY_REVIEWER_ROLES", "PROGRAM_COORDINATOR")
    monkeypatch.delenv("OPPORTUNITY_PUBLISHER_ROLES", raising=False)
    with db.command(U["pc_sys"]) as ctx:
        opps.approve_for_publication(ctx, unconfigured_id)
    with db.command(U["ec1"]) as ctx:
        with pytest.raises(BusinessError) as error:
            opps.publish_opportunity(ctx, unconfigured_id)
    assert error.value.code == "OPPORTUNITY_PUBLISH_AUTHORITY_UNCONFIGURED"
