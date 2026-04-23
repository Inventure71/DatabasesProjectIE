# Frontend

The frontend is a Django app that lives beside `backend/`.

```text
backend/   real data models, services, and APIs
frontend/  templates, static files, frontend views, and service-backed page contracts
```

Run the project from the repository root:

```bash
source .venv/bin/activate
python manage.py runserver
```

Routing convention:

- `/` and pages such as `/catalog/` are frontend template routes.
- `/api/...` is real backend API space.
- `/mock-api/...` is not mounted now; add it back only for a future JavaScript feature that needs temporary simulated JSON.

Page data shaping should live in `frontend/services/`, not directly in views.
Current catalog, listing, collection, and card-detail pages use real backend
models/services through that boundary.
