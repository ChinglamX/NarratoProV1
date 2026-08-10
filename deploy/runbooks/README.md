# Runbooks

Operational recovery procedures are added with the capability they govern. A dashboard or alert is incomplete without a linked runbook.

## Bootstrap infrastructure

1. Copy `deploy/compose/.env.example` to `deploy/compose/.env` and replace every placeholder.
2. Validate with `docker compose --env-file deploy/compose/.env -f deploy/compose/docker-compose.yml config --quiet`.
3. Start with the same command plus `up -d --wait`.
4. Inspect `docker compose ... ps` and service health before starting API/worker.
5. Stop with `down`; do not add `-v` unless loss of local state is explicitly intended.

The full A03 check is `make infra-accept`. It starts all services, writes PostgreSQL and MinIO persistence probes, restarts the stack, verifies both probes, and prints final service state. A failed image pull is an environment failure and does not count as runtime acceptance.

The checked-in example is only for configuration parsing and must not be used as production credentials.
