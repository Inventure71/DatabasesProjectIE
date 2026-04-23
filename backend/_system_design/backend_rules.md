# Backend Rules

This file records backend architectural rules and decisions. Treat it as a system-decision file: change it only after explicit user approval.

## Current Backend Scope

- Backend only. Ignore frontend work while following this backend plan.
- Stack: Django, Django REST Framework, PostgreSQL, Django built-in auth.
- Backend code lives under `backend/`.
- Backend planning and status lives in `backend/TODO.md`.
- Backend system design documentation lives under `backend/_system_design/`.

## Module Boundaries

- `common` owns shared backend infrastructure.
- `users` owns authentication-related profile data and user-facing identity extensions.
- `catalog` owns official card, set, variant, and image data.
- `inventory` owns user-owned card stock and inventory history.
- `marketplace` owns listings, orders, and purchase workflows.
- `pricing` owns price snapshots and value calculations.
- `similarity` is optional later work and must not be mixed into core marketplace transactions.

## File Conventions Per App

Each domain app should follow this structure:

```text
app_name/
├── models.py
├── serializers.py
├── services.py
├── views.py
├── urls.py
└── tests.py
```

Responsibilities:

- `models.py`: database schema, model constraints, and model-owned enums.
- `serializers.py`: request and response JSON shape.
- `services.py`: business logic, validation that spans model operations, and state changes.
- `views.py`: thin API layer that validates request shape, calls services, and returns responses.
- `urls.py`: app-specific routes.
- `tests.py`: app tests initially. Split into a `tests/` package later if the file becomes too large.

## Enum Convention

- Use Django `TextChoices` for stable string statuses and categories.
- Keep enums close to the model that owns the state.
- Avoid global enum modules unless multiple apps truly share the same concept.

## Service Layer Convention

- Views must not directly perform business workflows.
- State-changing workflows belong in service functions.
- Services should be the single trusted entry point for important business rules.
- Purchase and inventory workflows must use database transactions where consistency matters.

## Serializer Convention

- Serializers live in each app's `serializers.py`.
- Serializers define API input and output shape.
- Serializers may validate request-local data.
- Cross-row or transactional business validation belongs in services, not serializers.

## URL Convention

- Each app owns its routes in `app_name/urls.py`.
- `config/urls.py` includes app route modules.
- Prefer clear route groupings over putting all routes in the project-level URL file.

Current API route groups:

- `api/users/`
- `api/catalog/`
- `api/inventory/`
- `api/marketplace/`
- `api/pricing/`

## Admin Convention

- Register models in admin as they are created.
- Admin is for inspection, seed-data checking, and development support.
- Admin must not become the only way core workflows can run.

## Error Handling Convention

- Keep error handling simple until real services exist.
- Service-layer validation failures should become DRF `400 Bad Request` responses at the API boundary.
- Introduce custom domain exceptions only when plain exceptions stop being clear enough.

## Permission Convention

- Use DRF built-in permissions first.
- Add custom permissions only when inventory ownership or marketplace rules require them.

## Pending Decisions

- Exact error response body shape once the first state-changing service exists.
