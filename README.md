# DatabasesProjectIE

## General Information

This project is a Django + PostgreSQL web application for browsing catalog data and managing a personal physical card collection.

The website includes `?` help buttons next to most query-driven features, each with a simple explanation of how that query works.

## Suggested Solution

Use the deployed solution from https://databases-project-ie.vercel.app/

## Local Setup

Run these commands from the repository root:

```bash
cd {Project Root}

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Start PostgreSQL locally. On macOS with Homebrew:

```bash
brew services start postgresql@14
pg_isready -h 127.0.0.1 -p 5432
```

`pg_isready` should report that PostgreSQL is accepting connections.

Create a PostgreSQL role and database for this project:

```bash
psql postgres
```

Inside the `psql` prompt, run:

```sql
CREATE ROLE cards_user WITH LOGIN PASSWORD 'choose-a-local-password';
CREATE DATABASE cards_marketplace OWNER cards_user;
\q
```

Important distinction:

- `cards_marketplace` is the database name.
- `cards_user` is the database role/user.
- The password belongs to `cards_user`, not to `cards_marketplace`.

If your `psql` prompt ends with `-#` instead of `=#`, PostgreSQL thinks you are
inside an unfinished SQL command. Press `Ctrl+C` to cancel the unfinished command
and return to a clean prompt.

If the role or database already exists, update them instead:

```sql
ALTER ROLE cards_user WITH PASSWORD 'choose-a-local-password';
ALTER DATABASE cards_marketplace OWNER TO cards_user;
```

Create `.env` in the repo root. Use the same password you assigned to
`cards_user`:

```bash
cat > .env <<'EOF'
DJANGO_SECRET_KEY=dev-only-change-this-later
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

POSTGRES_DATABASE=cards_marketplace
POSTGRES_USER=cards_user
POSTGRES_PASSWORD=choose-a-local-password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
EOF
```

Test the database credentials directly before running Django:

```bash
PGPASSWORD='choose-a-local-password' psql -h 127.0.0.1 -U cards_user -d cards_marketplace -c "select current_database(), current_user;"
```

Apply schema, then import the CSV dataset:

```bash
python manage.py check
python manage.py migrate
python manage.py import_pokemon_cards_dataset original_datasets/pokemon-cards/pokemon-cards.csv
```

or 

```bash
python manage.py import_pokemon_cards_dataset --all-source-sets
```

Verify the import:

```bash
python manage.py shell -c "from catalog.models import CardGame, CardSet, Card, CardVariant, CardImage; print('games', CardGame.objects.count()); print('sets', CardSet.objects.count()); print('cards', Card.objects.count()); print('variants', CardVariant.objects.count()); print('images', CardImage.objects.count())"
```

Expected current import scope: `Base` + `Jungle`, which should load `132` card variants. The import command is repeatable because it uses `update_or_create`, so rerunning it updates existing rows instead of duplicating them.

Run the local web app:

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

Run the test suite:

```bash
python manage.py test common catalog users inventory marketplace pricing frontend --keepdb
```