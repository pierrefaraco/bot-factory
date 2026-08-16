# Alembic — Usage Guide

All Alembic configuration (config, environment scripts, migrations) lives in `server/db/`:

```
server/db/
├── alembic.ini          # Alembic config (script_location = %(here)s/alembic)
├── alembic/
│   ├── env.py            # Bootstrap: import ai_server models + DATABASE_URL
│   ├── script.py.mako     # Template used to generate a new revision
│   └── versions/          # Migration history (one file per revision)
├── check_alembic.py        # Diagnostic script for configuration
├── drop_table.sh / .bat     # Destroy all tables (⚠️ destructive)
└── README.md                # This guide
```

> Migration commands (`init` / `create` / `upgrade` / `downgrade` / `history` / `current` / `stamp`) are exposed as `make db-*` targets at the project root (see `Makefile`). They run `uv run alembic` from `server/db/` and load `DATABASE_URL` automatically from `server/.env`.

## 1. Prerequisites (first run)

1. **Python virtual environment installed** (see `server/CLAUDE.md`):
```bash
cd server
uv sync
```
2. **A MySQL database running**, either via Docker (`make dev` / `make db-only`) or locally.

## 2. Configure `DATABASE_URL`

`alembic/env.py` reads `DATABASE_URL` via `ai_server.config.config.flask_config`. This is the same variable used by the Flask server and is defined in `server/.env`:

```
DATABASE_URL=******127.0.0.1:3306/botcraft?charset=utf8mb4
```

The `make db-*` targets load `server/.env` before invoking `alembic` — no need to export `DATABASE_URL` manually if the file is up to date.

## 3. Create the `alembic/` folder if missing

If the `alembic/` folder (containing `env.py`, `script.py.mako`, `versions/`) is missing, regenerate it with:

```bash
make db-init
```

This command (see `server/db/bootstrap_alembic.sh`) does nothing if `alembic/` already exists and is not empty (it never overwrites). If the folder does not exist, it runs `alembic init alembic` and then rewrites `alembic/env.py` with a customized version (imports `ai_server` models and reads `DATABASE_URL`) — no git required.

> ⚠️ `server/db/` (including `alembic/`) is currently not tracked by git in this repository (`git ls-files server/db` returns nothing). Consider `git add server/db` if you want to version this configuration and migration history.

## 4. Verify the configuration

A diagnostic script is provided:

```bash
cd server && uv run db/check_alembic.py
```

It checks: `DATABASE_URL`, presence of Alembic files, the `alembic` command, SQLAlchemy models import (`ai_server.dao.database.Base`) and existing migrations.

## 5. First run — apply migrations

### Case A — fresh database (no tables)

Apply all migrations from scratch:

```bash
make db-upgrade
```

This creates all tables defined by the initial migration `d2d0def68081_start.py` and any subsequent migrations.

### Case B — database already exists (tables created manually)

If tables already exist (e.g., legacy DB without Alembic tracking), do NOT run `upgrade` (it will try to recreate tables). Instead, mark the DB as at the current revision without executing SQL:

```bash
make db-stamp REV=head
```

## 6. Creating a new migration

After modifying a model in `server/ai_server/dao/database.py`:

```bash
make db-create MSG="Description of the change"
```

This generates a new file in `alembic/versions/` using `--autogenerate`. Always review the generated file (Alembic does not detect every change: renames, type changes, etc.). Then apply it:

```bash
make db-upgrade
```

## 7. Available commands (`make db-*`)

```bash
make db-init                      # Create alembic/ if missing
make db-create MSG="message"     # Auto-generated new migration
make db-upgrade                   # Apply pending migrations
make db-downgrade                 # Undo last migration
make db-history                   # Migration history
make db-current                   # Current revision
make db-stamp REV=<rev|head>      # Mark DB as a revision without applying SQL
```

These are wrappers around standard `alembic` commands. You can also use `alembic` directly from `server/db/`:

```bash
cd server/db
export DATABASE_URL='******127.0.0.1:3306/botcraft'
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "message"
```

## 8. With Docker Compose

The API Dockerfile copies the `db/` folder into the image (`/app/db`). Run migrations from inside the container:

```bash
make migrate
# equivalent to:
docker-compose exec -w /app/db api alembic upgrade head
```

> The `-w /app/db` flag is necessary: Alembic looks for `alembic.ini` in the current working directory, and the container default `WORKDIR` is `/app` while the file is at `/app/db`.

To create a migration from the container:

```bash
docker-compose exec -w /app/db api alembic revision --autogenerate -m "Description"
```

Note: Because the `db` container publishes MySQL on the host at `3306:3306`, the `make db-*` targets also work against the database started with `make db-only` / `make dev` without using `docker-compose exec`.

## 9. Reset the database completely (destructive)

```bash
cd server/db
./drop_table.sh   # or drop_table.bat on native Windows
```

⚠️ This deletes **all** tables from the database pointed by `DATABASE_URL`. Use only in development.

## Notes on moving files to `server/db/`

Several adjustments were applied when moving files into `server/db/`:
- `alembic.ini` now uses `%(here)s` for `script_location` to resolve paths reliably
- `alembic/env.py` sys.path calculation was updated to find the `ai_server` package from the new location
- `check_alembic.py` adds the parent `server/` directory to `sys.path` before importing models
- `drop_table.sh` adjusted relative paths to `../tool/drop_tables.py`
- `make db-*` wrappers now load `server/.env` and run `uv run alembic` from the correct directory
- Docker Compose commands must use `-w /app/db` to find `alembic.ini`
