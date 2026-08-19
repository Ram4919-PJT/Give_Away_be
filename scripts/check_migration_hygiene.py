#!/usr/bin/env python3
"""Guard against reintroducing manual SQL migration paths.

Run from Give_Away_be:
    python scripts/check_migration_hygiene.py

Exits 0 when checks pass, 1 when violations are found.
Does not connect to or modify any database.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = BACKEND_ROOT / "scripts"
LEGACY_DIR = SCRIPTS_DIR / "legacy_sql_migrations"
SERVICES_DIR = BACKEND_ROOT / "services"

ALLOWED_LEGACY_RUNNERS = frozenset(
    {
        "run_kyc_migration.py",
        "run_receiver_kyc_phase2_migration.py",
        "run_assistance_migration.py",
        "run_assistance_disbursement_migration.py",
        "run_ngo_dashboard_migration.py",
        "run_email_migration.py",
    }
)

CREATE_ALL_ALLOWLIST = frozenset(
    {
        SERVICES_DIR / "iam-service" / "app" / "db" / "init_db.py",
    }
)

CREATE_ALL_PATTERN = re.compile(r"(?:Base\.)?metadata\.create_all\s*\(")


def _fail(messages: list[str]) -> int:
    for msg in messages:
        print(f"ERROR: {msg}", file=sys.stderr)
    print(
        "\nSee docs/DATABASE_MIGRATIONS.md and scripts/legacy_sql_migrations/README.md",
        file=sys.stderr,
    )
    return 1


def check_ensure_sql_outside_legacy() -> list[str]:
    violations: list[str] = []
    for path in SCRIPTS_DIR.glob("ensure_*.sql"):
        violations.append(
            f"Schema SQL file must live under legacy_sql_migrations/: {path.relative_to(BACKEND_ROOT)}"
        )
    return violations


def check_migration_runners() -> list[str]:
    violations: list[str] = []
    for path in SCRIPTS_DIR.glob("run_*_migration.py"):
        name = path.name
        if name not in ALLOWED_LEGACY_RUNNERS:
            violations.append(
                f"New migration runner is not allowed: {path.relative_to(BACKEND_ROOT)}"
            )
            continue
        text = path.read_text(encoding="utf-8")
        if "deprecated_exit" not in text and "DEPRECATED" not in text:
            violations.append(
                f"Legacy runner must use deprecation guard: {path.relative_to(BACKEND_ROOT)}"
            )
    return violations


def _is_test_path(path: Path) -> bool:
    parts = path.parts
    return "tests" in parts or path.name.startswith("test_") or path.name.endswith("_test.py")


def check_create_all_usage() -> list[str]:
    violations: list[str] = []
    for path in SERVICES_DIR.rglob("*.py"):
        if _is_test_path(path):
            continue
        if path.resolve() in {p.resolve() for p in CREATE_ALL_ALLOWLIST}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if CREATE_ALL_PATTERN.search(text):
            violations.append(
                f"create_all() is only allowed in test fixtures or allowlisted init_db.py: "
                f"{path.relative_to(BACKEND_ROOT)}"
            )
    return violations


def main() -> int:
    violations: list[str] = []
    violations.extend(check_ensure_sql_outside_legacy())
    violations.extend(check_migration_runners())
    violations.extend(check_create_all_usage())
    if violations:
        return _fail(violations)
    print("Migration hygiene checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
