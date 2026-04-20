# Current Frontend Design

The frontend is a Django app at repository-root `frontend/`. It is loaded by
the same Django runtime as the backend, but it has separate ownership.

## Responsibilities

- `frontend/templates/` owns server-rendered HTML.
- `frontend/static/` owns CSS and browser assets.
- `frontend/views.py` owns page orchestration only.
- `frontend/services/` owns the data contract used by frontend views.
- `frontend/mock_api/` owns simulated JSON endpoints for frontend JavaScript.

## Data Boundary

Frontend views should call service functions instead of hardcoding data or
querying backend models directly in templates.

Current service modules:

- `frontend.services.catalog_service`
- `frontend.services.listing_service`

These services currently use mock data. As backend features become ready, the
service internals can switch to real ORM queries or real API calls while the
template-facing shape stays stable.

## Routing

- `/` serves frontend pages.
- `/api/...` is reserved for real backend APIs.
- `/mock-api/...` is reserved for simulated frontend endpoints.

This split lets frontend work continue without pretending that unfinished real
backend APIs already exist.
