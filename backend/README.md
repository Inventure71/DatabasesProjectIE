# Backend

## Setup

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in the repository root with:

```env
DJANGO_SECRET_KEY=dev-only-change-this-later
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

MYSQL_DATABASE=cards_marketplace
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
```

Create the database:

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS cards_marketplace CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
```

## Run

```bash
# Activate the virtual environment so Python uses this project's dependencies.
source .venv/bin/activate

# Validate Django configuration (apps, settings, database config, etc.).
python manage.py check

# Apply pending database migrations (create/update tables and schema in MySQL).
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
python manage.py test common catalog users inventory marketplace pricing
```

## Seed Catalog Data

After migrations have run, load the development catalog sample:

```bash
source .venv/bin/activate
python manage.py seed_catalog
```

The command is repeatable. Running it again updates the same sample rows instead of duplicating them.
