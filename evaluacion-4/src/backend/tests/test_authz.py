"""T-03 port: role AND relationship authorization with multiple role assignments."""
from __future__ import annotations

import pytest

from app import db
from app.errors import Forbidden, NotFound
from app.modules import authz
from tests.conftest import make_opportunity, make_placement, seed_base


def _subject(cur, uid):
    return authz.subject(cur, uid)


def test_t03_matrix(env):
    U = seed_base(env)
    opp_alfa = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")
    opp_beta = make_opportunity(env, 2, U["P"]["ADM"], "Beta")
    p1 = make_placement(env, U["s1"], opp_alfa, supervisor_id=U["ws_alfa"], faculty_id=U["f1"])
    p2 = make_placement(env, U["s3"], opp_beta, supervisor_id=U["ws_beta"])
    p3 = make_placement(env, U["s2"], opp_alfa, supervisor_id=U["ws_alfa2"])
    env.admin.execute("INSERT INTO supervisor_assignment VALUES (%s,%s,'FACULTY')", (p1, U["dual1"]))

    expected = {
        "hm_alfa": {p1, p3}, "hm_beta": {p2}, "ws_alfa": {p1}, "ws_alfa2": {p3}, "ws_beta": {p2},
        "s1": {p1}, "s2": {p3}, "s3": {p2}, "f1": {p1}, "pc_sys": {p1, p3}, "pc_adm": {p2},
        "ec1": {p1, p2, p3}, "legal1": {p1, p2, p3}, "dual1": {p1, p3},
    }
    with db.read() as cur:
        for key, exp in expected.items():
            subj = _subject(cur, U[key])
            assert set(authz.visible_placement_ids(cur, subj)) == exp, key
            for pid in (p1, p2, p3):
                assert authz.can_read(cur, subj, pid) == (pid in exp), f"{key}:{pid}"

        # external gets NotFound; internal gets Forbidden (no relationship)
        for key, pid in (("hm_alfa", p2), ("ws_alfa", p2)):
            subj = _subject(cur, U[key])
            with pytest.raises(NotFound):
                authz.authorize(cur, subj, "placement:read", pid)
        for key, pid in (("s1", p2), ("pc_adm", p1)):
            subj = _subject(cur, U[key])
            with pytest.raises(Forbidden):
                authz.authorize(cur, subj, "placement:read", pid)

        # negative action cases denied
        for key, action, pid in (("s1", "placement:activate", p1),
                                 ("ws_alfa", "document:review", p1),
                                 ("s2", "progress:create", p1)):
            subj = _subject(cur, U[key])
            with pytest.raises(Forbidden):
                authz.authorize(cur, subj, action, pid)

        # positive action cases allowed
        for key, action, pid in (("ec1", "placement:activate", p1),
                                 ("pc_sys", "placement:approve_academic", p1),
                                 ("legal1", "document:review", p2),
                                 ("s1", "progress:create", p1)):
            subj = _subject(cur, U[key])
            authz.authorize(cur, subj, action, pid)

        view = authz.external_student_view(cur, U["s1"])
        assert set(view) == {"display_name", "program_code"}
        assert view["program_code"] == "ING-SIS"


def test_t03_multi_role_union(env):
    U = seed_base(env)
    opp = make_opportunity(env, 1, U["P"]["ING-SIS"], "Alfa")
    p = make_placement(env, U["s1"], opp)
    env.admin.execute("INSERT INTO supervisor_assignment VALUES (%s,%s,'FACULTY')", (p, U["dual1"]))
    with db.read() as cur:
        subj = _subject(cur, U["dual1"])
        assert {r["role"] for r in subj["roles"]} == {"PROGRAM_COORDINATOR", "FACULTY_SUPERVISOR"}
        assert authz.can_read(cur, subj, p)
