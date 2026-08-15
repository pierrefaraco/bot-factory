#!/bin/bash
# This script launches the ai_server Flask server using uv.
# uv manages the virtual environment and dependencies automatically —
# no manual activation needed (replaces z-activate.sh + venv activation).

set -e

# Ensure this dev container is on the same Docker network as the MySQL/Chroma
# containers (db, chromadb), otherwise DATABASE_URL's "db" host won't resolve.
DB_NETWORK="bot-factory_botfactory-network"
DEV_CONTAINER="dev-container"
if command -v docker &> /dev/null; then
    if ! docker network inspect "$DB_NETWORK" --format '{{json .Containers}}' 2>/dev/null | grep -q "$DEV_CONTAINER"; then
        echo "Connecting $DEV_CONTAINER to $DB_NETWORK..."
        docker network connect "$DB_NETWORK" "$DEV_CONTAINER" 2>/dev/null || true
    fi
fi

# Kill existing processes using the same port (safely)
FLASK_PORT=444
echo "Checking for processes using port $FLASK_PORT..."
PORT_PID=$(ss -ltnp "sport = :$FLASK_PORT" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | sort -u || true)
if [ -n "$PORT_PID" ]; then
    echo "Killing process(es) using port $FLASK_PORT: $PORT_PID"
    kill -TERM $PORT_PID 2>/dev/null || true
    sleep 2
    # Force kill if still running
    if kill -0 $PORT_PID 2>/dev/null; then
        echo "Force killing stubborn process(es)..."
        kill -KILL $PORT_PID 2>/dev/null || true
    fi
else
    echo "No processes found using port $FLASK_PORT"
fi

# Sync dependencies (creates/updates .venv from pyproject.toml + uv.lock)
echo "Syncing dependencies with uv..."
uv sync

# Load environment variables from .env
if [ ! -f .env ]; then
    echo "Error: .env not found. Copy .env.example to .env and fill in real values."
    exit 1
fi
set -a
source .env
set +a

# == Flask run ==
echo "Starting Flask server on port $FLASK_PORT..."
uv run flask run --host 0.0.0.0 -p $FLASK_PORT --no-reload
