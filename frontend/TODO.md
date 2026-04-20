# Frontend TODO

This file tracks frontend work now that `frontend/` is a sibling Django app.

## Current Status

- [x] Frontend app imported from `origin/Andres`
- [x] Frontend pages mounted at `/`
- [x] Fake catalog and listing data moved into `frontend/services/`
- [x] Mock JSON endpoints mounted under `/mock-api/`
- [x] Real backend APIs remain reserved under `/api/`
- [x] Catalog and marketplace pages now read real backend-backed data through frontend services
- [x] Listing detail buy form now uses the backend purchase workflow
- [x] Authenticated backend API wrappers exist for user, inventory, order history, and collection valuation

## Working Rules

- Keep templates and static assets in `frontend/`.
- Use `frontend/services/` as the boundary between pages and data.
- Use `/mock-api/...` only for simulated frontend JSON.
- Do not create fake endpoints under `/api/...`; that namespace belongs to the real backend.
- Replace mock service internals with real backend data one feature at a time.

## Next Steps

- [x] Replace mock catalog/listing services with real backend-backed data contracts.
- [x] Add service functions for authenticated inventory management.
- [x] Add a real listing detail page and connect the buy flow to the backend purchase endpoint.
- [ ] Add frontend pages for authenticated inventory management.
- [ ] Add purchase history and sales history pages for authenticated users.
- [ ] Add authenticated user/profile display in the navbar or account page using the backend current-user endpoint.
- [x] Replace mock-only price history with backend `PriceSnapshot` data.
- [x] Keep similar-card UI backend-backed by catalog metadata only; full similarity remains optional later work.
- [ ] Add mock API endpoints only when frontend JavaScript needs JSON.
- [x] Add tests for current frontend/backend wiring.
- [x] Verified frontend/backend wiring with `python manage.py test common.test_frontend_integration frontend`.
- [x] Verified full project checks with `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py migrate --check`, and `python manage.py test common catalog users inventory marketplace pricing frontend`.
