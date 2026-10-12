"""Explicit libpq environment shared by database tools; never inherit PG*."""


def psql_environment(db, *, read_only=False):
    env = {"PATH": "/usr/bin:/bin", "PGHOST": db.host,
           "PGPORT": str(db.port), "PGDATABASE": db.name, "PGUSER": db.user,
           "PGPASSWORD": db.password, "PGCONNECT_TIMEOUT": "5",
           "PGSSLMODE": db.sslmode, "PGGSSENCMODE": "disable",
           "PGOPTIONS": "-c statement_timeout=30000"}
    if db.sslrootcert:
        env["PGSSLROOTCERT"] = db.sslrootcert
    if read_only:
        env["PGOPTIONS"] += " -c default_transaction_read_only=on"
    return env
