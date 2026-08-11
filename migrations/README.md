# Database Migrations

Run with an explicit PostgreSQL URL:

```bash
NARRATOPRO_DATABASE_URL=postgresql+psycopg://... alembic upgrade head
NARRATOPRO_DATABASE_URL=postgresql+psycopg://... alembic downgrade base
```

Revision `0001_e02` establishes the E02 schemas and metadata baseline. It is an additive clean
deployment with no table rewrite or lock on existing business rows. Rollback drops only this empty
baseline and is prohibited after production data exists without an approved backup/deletion plan.

Future revisions must be self-contained snapshots: they may not depend on mutable current metadata.
Every revision records compatibility, lock risk, forward/rollback plan, validation query, owner, and
maximum allowed pause in its revision documentation.
