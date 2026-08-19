"""DEPRECATED legacy migration runner — use Alembic instead."""

from __future__ import annotations

import sys

from _migration_runner_deprecated import deprecated_exit

if __name__ == "__main__":
    sys.exit(deprecated_exit("run_kyc_migration.py"))
