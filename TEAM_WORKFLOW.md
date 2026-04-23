# Team Workflow

This project is one Django application with two sibling source areas:

```text
backend/   real database models, business logic, and API endpoints
frontend/  templates, static files, page views, and service-backed page contracts
```

Run Django from the repository root:

```bash
source .venv/bin/activate
python manage.py check
python manage.py runserver
```

The local site runs at:

```text
http://127.0.0.1:8000/
```

## Shared Rules

- Do not merge another branch blindly if it changes both `backend/` and `frontend/`.
- Backend work and frontend work should be integrated through small pull requests or merge commits.
- Real backend endpoints always live under `/api/...`.
- `/mock-api/...` is not mounted now; add it only for a future JavaScript feature that needs temporary simulated JSON.
- Do not create fake endpoints under `/api/...`; that hides whether the real backend exists.
- Do not put large fake data lists directly in `frontend/views.py`.
- Keep frontend data-shaping code inside `frontend/services/`.
- When a backend feature becomes real, replace the internals of the relevant frontend service instead of rewriting templates first.

## Backend Developer Instructions

The backend developer owns:

```text
backend/config/
backend/common/
backend/users/
backend/catalog/
backend/inventory/
backend/marketplace/
backend/pricing/
requirements.txt
```

The backend developer should focus on:

- database models
- migrations
- service-layer business rules
- serializers
- real API views
- API route modules
- admin registration
- backend tests

Backend endpoints must use the `/api/` namespace.

Examples:

```text
/api/users/me/
/api/catalog/cards/
/api/inventory/items/
/api/marketplace/listings/
```

Before finishing backend work, run:

```bash
source .venv/bin/activate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test common catalog users inventory marketplace pricing
```

If a backend feature is not ready yet, do not create a fake `/api/...` endpoint.
Tell the frontend developer what data shape the future endpoint or service should
return, and let the frontend developer simulate it inside `frontend/services/`.

## Frontend Developer Instructions

The frontend developer owns:

```text
frontend/templates/
frontend/static/
frontend/views.py
frontend/urls.py
frontend/services/
frontend/tests.py
```

The frontend developer should focus on:

- page templates
- reusable template components
- CSS and static assets
- page-level Django views
- frontend service functions
- frontend tests

Frontend pages live at normal page routes.

Examples:

```text
/
/catalog/
/catalog/1/
/listings/
/listings/1/
/login/
/register/
```

When adding a new page, first create or update a service function in
`frontend/services/`.

Good pattern:

```python
from frontend.services.catalog_service import list_cards


def catalog(request):
    cards = list_cards(request.GET)
    return render(request, "catalog.html", {"cards": cards})
```

Avoid this pattern:

```python
def catalog(request):
    cards = [
        {"id": 1, "name": "Charizard"},
        {"id": 2, "name": "Blastoise"},
    ]
    return render(request, "catalog.html", {"cards": cards})
```

The first version has a clean replacement point. The second version mixes page
logic and fake backend data.

## How To Simulate Missing Backend Work

Use `frontend/services/` when a Django template needs data.

Example:

```python
# frontend/services/inventory_service.py

def list_inventory_items(user, filters):
    return [
        {
            "id": 1,
            "card_name": "Charizard",
            "condition": "Near Mint",
            "quantity": 2,
            "available_quantity": 2,
        }
    ]
```

If future browser JavaScript needs JSON before a real backend endpoint exists,
add a small temporary mock route deliberately and document when it should be
removed. Do not keep mock routes mounted after the matching backend-backed
service exists.

## Replacing A Mock With Real Backend Data

Use this sequence:

1. Backend developer implements the real model, service, serializer, view, URL, and tests.
2. Backend developer verifies the real `/api/...` endpoint or ORM flow.
3. Frontend developer updates the matching `frontend/services/...` function.
4. Frontend developer keeps the template context shape stable where possible.
5. Both developers run tests.
6. Remove obsolete mock data only after the real path is verified.

## Branch Workflow

Use focused branches:

```text
backend/<feature-name>
frontend/<feature-name>
integration/<topic>
```

Recommended flow:

```bash
git fetch origin
git switch merge-attempt
git pull
git switch -c backend/marketplace-listings
```

or:

```bash
git fetch origin
git switch merge-attempt
git pull
git switch -c frontend/inventory-pages
```

Before merging a branch back, check what it touches:

```bash
git status
git diff --name-status merge-attempt...HEAD
```

If a frontend branch changes backend models, migrations, or API services, stop
and discuss it first.

If a backend branch changes templates, CSS, or frontend services, stop and
discuss it first.

## Conflict Rule

If both people need the same file, agree on the ownership before editing.

Common shared files:

```text
backend/config/settings.py
backend/config/urls.py
frontend/services/
```

For shared files, prefer small changes and explain why the change belongs there.

## Current Contract

Currently available frontend simulation endpoints: none.

Currently available real backend API areas:

```text
/api/users/
/api/catalog/
/api/inventory/
/api/marketplace/
/api/pricing/
```

Some real API areas may be route skeletons until their backend phase is
implemented. If the real endpoint does not return the needed data yet, the
frontend should continue using `frontend/services/...` as the page boundary.
