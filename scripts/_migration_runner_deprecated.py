"""Shared exit handler for deprecated manual migration runners."""

from __future__ import annotations

import sys

DEPRECATED_MESSAGE = """\
DEPRECATED: {script_name} is no longer supported.

Alembic is the only supported database schema migration system.
Running this script against an Alembic-managed database is prohibited.

Use:

    cd services/<service-name>
    alembic upgrade head

See:
    scripts/legacy_sql_migrations/README.md
    docs/DATABASE_MIGRATIONS.md
"""


def deprecated_exit(script_name: str) -> int:
    print(DEPRECATED_MESSAGE.format(script_name=script_name), file=sys.stderr)
    return 1
