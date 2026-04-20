# Frontend

The frontend is a Django app that lives beside `backend/`.

```text
backend/   real data models, services, and APIs
frontend/  templates, static files, frontend views, and mock API contracts
```

Run the project from the repository root:

```bash
source .venv/bin/activate
python manage.py runserver
```

Routing convention:

- `/` and pages such as `/catalog/` are frontend template routes.
- `/api/...` is real backend API space.
- `/mock-api/...` is frontend simulation space for unfinished backend features.

Mock data should live in `frontend/services/`, not directly in views. When a
backend feature is ready, replace the service internals with real data access
without changing templates first.
