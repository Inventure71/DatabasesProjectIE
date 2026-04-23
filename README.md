# DatabasesProjectIE

From the repo root:

```bash
cd /Users/inventure71/VSProjects/School/DatabasesProjectIE

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create `.env` in the repo root:

```bash
cat > .env <<'EOF'
DJANGO_SECRET_KEY=dev-only-change-this-later
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost

MYSQL_DATABASE=cards_marketplace
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
EOF
```

Create a fresh MySQL database:

```bash
mysql -u root -p -e "DROP DATABASE IF EXISTS cards_marketplace; CREATE DATABASE cards_marketplace CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
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