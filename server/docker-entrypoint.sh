#!/bin/sh
# Applies pending Alembic migrations, then runs the container's command.
# The schema must exist before the API starts: its startup creates the
# super admin. Retried because the db healthcheck can pass while MySQL is
# still running its first-start initialization (temporary server, database
# and user not created yet).
set -e

attempts=10
until (cd /app/db && alembic upgrade head); do
    attempts=$((attempts - 1))
    if [ "$attempts" -le 0 ]; then
        echo "Database migrations failed, giving up." >&2
        exit 1
    fi
    echo "Database migrations failed, retrying in 3 s ($attempts attempts left)..." >&2
    sleep 3
done

exec "$@"
