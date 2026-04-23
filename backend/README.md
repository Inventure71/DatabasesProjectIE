# Backend

## Setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start PostgreSQL locally:

```bash
brew services start postgresql@14
pg_isready -h 127.0.0.1 -p 5432
```

Create a dedicated PostgreSQL role and database:

```bash
psql postgres
```

Inside `psql`:

```sql
CREATE ROLE cards_user WITH LOGIN PASSWORD 'choose-a-local-password';
CREATE DATABASE cards_marketplace OWNER cards_user;
\q
```

The password belongs to the role/user, `cards_user`. The database is
`cards_marketplace`; databases do not have passwords by themselves.

If the `psql` prompt ends with `-#`, press `Ctrl+C` before running the commands.
That prompt means PostgreSQL is waiting for the rest of an unfinished SQL
statement.

If the role or database already exists:

```sql
ALTER ROLE cards_user WITH PASSWORD 'choose-a-local-password';
ALTER DATABASE cards_marketplace OWNER TO cards_user;
```

Create `.env` in the repository root with the same password:

```env
DJANGO_SECRET_KEY=dev-only-change-this-later
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

POSTGRES_DATABASE=cards_marketplace
POSTGRES_USER=cards_user
POSTGRES_PASSWORD=choose-a-local-password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
```

Check the credentials before running Django:

```bash
PGPASSWORD='choose-a-local-password' psql -h 127.0.0.1 -U cards_user -d cards_marketplace -c "select current_database(), current_user;"
```

## Run

```bash
# Activate the virtual environment so Python uses this project's dependencies.
source .venv/bin/activate

# Validate Django configuration (apps, settings, database config, etc.).
python manage.py check

# Apply pending database migrations (create/update tables and schema in PostgreSQL).
python manage.py migrate

# Start the local Django development server (usually at http://127.0.0.1:8000).
python manage.py runserver
```

The Django command entrypoint now lives at the repository root. Keep backend
domain apps in `backend/` and frontend pages in `frontend/`.

## Test

From the repository root:

```bash
source .venv/bin/activate
python manage.py test common catalog users inventory marketplace pricing frontend --keepdb
```

## Import Catalog Data

After migrations have run, import the downloaded Pokemon card dataset:

```bash
source .venv/bin/activate
python manage.py import_pokemon_cards_dataset
```

By default, the importer loads the curated Base and Jungle subset used for the
MVP demo. To import every `set_name` present in the CSV, run:

```bash
source .venv/bin/activate
python manage.py import_pokemon_cards_dataset --all-source-sets
```

The command is repeatable. Running it again updates the same imported rows
instead of duplicating them. In all-set mode, set codes and collector-number
denominators are inferred for sets that are not part of the curated Base/Jungle
mapping, while alphanumeric collector numbers such as `H1` are preserved.

## Vercel Notes

Production deploys should use `DATABASE_URL` instead of the local `POSTGRES_*`
variables:

```env
DJANGO_SECRET_KEY=<production-secret>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=.vercel.app
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DBNAME?sslmode=require
```

Use a hosted PostgreSQL database for `DATABASE_URL`. Vercel cannot connect to a
database running on your laptop at `127.0.0.1`; from Vercel, `127.0.0.1` means
the function container itself.

After `vercel link`, prepare the remote database with:

```bash
vercel env run -- python manage.py migrate
vercel env run -- python manage.py import_pokemon_cards_dataset --all-source-sets
```
