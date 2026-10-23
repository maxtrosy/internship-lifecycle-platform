"""T-24: opportunity creation and role/relationship-scoped listing (C-03)."""
from __future__ import annotations

import pytest

from app import db
from app.errors import Forbidden
from app.modules import authz
from app.modules.opportunities import service as opps
from tests.conftest import seed_base


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
        assert {o["id"] for o in opps.list_opportunities(cur, s1)} == {o1, o2}
        assert {o["id"] for o in opps.list_opportunities(cur, hm_alfa)} == {o1, o2}
        assert {o["id"] for o in opps.list_opportunities(cur, hm_beta)} == set()
        assert {o["id"] for o in opps.list_opportunities(cur, pc_sys)} == {o1, o2}


def test_t24_authorization(env):
    U = seed_base(env)
    with db.command(U["hm_beta"]) as ctx:
        with pytest.raises(Forbidden):
            opps.create_opportunity(ctx, 1, U["P"]["ING-SIS"], "Foreign")
    with db.command(U["pc_adm"]) as ctx:
        with pytest.raises(Forbidden):
            opps.create_opportunity(ctx, 1, U["P"]["ING-SIS"], "Foreign program")
