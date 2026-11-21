"""Assemble the self-contained Evaluación 4 package and ZIP.

Copies the current source tree into evaluacion-4/src (excluding dependencies,
build output, caches, secrets and local data), refreshes the CR-05 test copies
and config example, and writes evaluacion-4.zip at the repository root.
It never touches the Evaluación 3 folders or ZIPs.
"""
from __future__ import annotations

import fnmatch
import pathlib
import re
import shutil
import zipfile

REPO = pathlib.Path(__file__).resolve().parents[1]
PACKAGE = REPO / "evaluacion-4"
ZIP_PATH = REPO / "evaluacion-4.zip"

EXCLUDED_DIRS = {
    "node_modules", "dist", "test-results", "playwright-report", ".deps", ".venv", "__pycache__",
    ".pytest_cache", ".pocdeps", ".pocdata", ".piptmp", ".pnpm-store", ".neon",
}
EXCLUDED_FILES = [".env", ".env.*", "*.pyc", "*.tsbuildinfo", "*.egg-info", "*.log"]
ALLOWED_ENV = {".env.example"}

SOURCES = {
    "backend": ["app", "migrations", "tests", "scripts", "alembic.ini", "pyproject.toml", "README.md", ".env.example"],
    "frontend": ["src", "e2e", "index.html", "package.json", "pnpm-lock.yaml", "pnpm-workspace.yaml",
                 "playwright.config.ts", "tsconfig.json", "vite.config.ts"],
}
SCRIPTS = ["check_isolated_migrations.py", "run_isolated_e2e.py", "run_eval3_demo.py",
           "persist_synthetic_dataset.py", "build_eval4_package.py"]


def excluded(path: pathlib.Path) -> bool:
    if any(part in EXCLUDED_DIRS or part.endswith(".egg-info") for part in path.parts):
        return True
    name = path.name
    if name in ALLOWED_ENV:
        return False
    return any(fnmatch.fnmatch(name, pattern) for pattern in EXCLUDED_FILES)


def copy_item(source: pathlib.Path, target: pathlib.Path) -> None:
    if source.is_dir():
        for item in source.rglob("*"):
            if item.is_file() and not excluded(item.relative_to(source.parent)):
                destination = target / item.relative_to(source)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, destination)
    elif source.is_file() and not excluded(source):
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def main() -> int:
    src = PACKAGE / "src"
    if src.exists():
        shutil.rmtree(src)  # regenerated copy of the repository source, never original work
    for area, items in SOURCES.items():
        for item in items:
            copy_item(REPO / area / item, src / area / item)
    for script in SCRIPTS:
        copy_item(REPO / "scripts" / script, src / "scripts" / script)

    # The repository loader pins a real Neon endpoint host (no credentials). The
    # distributed copy replaces it with a placeholder so it can never target Neon.
    loader = src / "scripts" / "persist_synthetic_dataset.py"
    text = loader.read_text(encoding="utf-8")
    loader.write_text(re.sub(r'^DIRECT_HOST = ".*"$', 'DIRECT_HOST = "redacted-neon-host.invalid"',
                             text, count=1, flags=re.MULTILINE), encoding="utf-8")

    tests = PACKAGE / "tests"
    tests.mkdir(exist_ok=True)
    for name in ("test_cr05_segments.py", "test_lifecycle.py", "test_http_authorization.py"):
        shutil.copy2(REPO / "backend" / "tests" / name, tests / name)
    shutil.copy2(REPO / "scripts" / "check_isolated_migrations.py", tests / "check_isolated_migrations.py")
    config = PACKAGE / "config"
    config.mkdir(exist_ok=True)
    shutil.copy2(REPO / "backend" / ".env.example", config / ".env.example")

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    count = 0
    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as archive:
        for item in sorted(PACKAGE.rglob("*")):
            relative = item.relative_to(PACKAGE)
            if item.is_file() and not excluded(relative):
                archive.write(item, pathlib.Path("DH05_E4") / relative)
                count += 1
    print(f"PACKAGE={PACKAGE} FILES={count} ZIP={ZIP_PATH} BYTES={ZIP_PATH.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
