"""T-23: module boundaries (AST check). Domain modules never import adapters or another
module's private files; cross-module usage goes through ``service.py`` (ADR-002 / ADR-007)."""
from __future__ import annotations

import ast
import pathlib

BACKEND = pathlib.Path(__file__).resolve().parents[1]
MODULES = BACKEND / "app" / "modules"


def _imports(path: pathlib.Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.append(node.module)
    return out


def test_domain_never_imports_adapters():
    bad = []
    for path in MODULES.rglob("*.py"):
        # identity.service is the composition edge for the simulated IdP adapter.
        if path.name == "service.py" and path.parent.name == "identity":
            continue
        for imp in _imports(path):
            if imp.startswith("app.adapters"):
                bad.append(f"{path.relative_to(BACKEND)} imports {imp}")
    assert not bad, bad


def test_cross_module_imports_via_public_service():
    bad = []
    for path in MODULES.rglob("*.py"):
        for imp in _imports(path):
            parts = imp.split(".")
            # app.modules.<module>.<sub> allowed only when <sub> is 'service' (or the module itself)
            if imp.startswith("app.modules.") and len(parts) >= 4 and parts[3] != "service":
                bad.append(f"{path.relative_to(BACKEND)} imports {imp}")
    assert not bad, bad
