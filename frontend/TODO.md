# Frontend TODO

This file tracks frontend work now that `frontend/` is a sibling Django app.

## Current Status

- [x] Frontend app imported from `origin/Andres`
- [x] Frontend pages mounted at `/`
- [x] Fake catalog and listing data moved into `frontend/services/`
- [x] Mock JSON endpoints mounted under `/mock-api/`
- [x] Real backend APIs remain reserved under `/api/`
- [x] Catalog and marketplace pages now read real backend-backed data through frontend services
- [x] Home search submits to catalog filtering instead of staying on the home page
- [x] Catalog page results are paginated so large card sets are sliced by the database
- [x] Home featured cards and latest listings are limited in the database before rendering
- [x] Listing detail buy form now uses the backend purchase workflow
- [x] Authenticated users can view their collection, estimated value, owned quantities, available stock, and reserved stock
- [x] Authenticated users can create sale listings from owned inventory through the collection page
- [x] Active listing cards use "Listed by" language so listed inventory is not confused with completed sales
- [x] Authenticated sellers can view their active listings on a dedicated page
- [x] Collection and active listing pages use set-based album books with selected-set pages, filters, and pagination.
- [x] Catalog, marketplace listings, and collection share the same card/set/shelf browser system.
- [x] Authenticated backend API wrappers exist for user, inventory, order history, and collection valuation
- [x] Login creates a Django session and the navbar logout form clears it through a CSRF-protected POST
- [x] Reusable kinetic card visual component is shared by card image surfaces across the frontend
- [x] Kinetic cards subtly scale up and brighten their rainbow glass border on hover/focus
- [x] Home central showcase displays the most expensive card sold in the current month, with a featured-card fallback when no monthly sale exists

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
- [x] Add frontend pages for authenticated inventory management.
- [x] Add frontend page for authenticated active listing management visibility.
- [x] Convert collection and active listing management surfaces from flat rows into set album views.
- [x] Add shared visualization controls for card album, collection book cover, and game shelf views.
- [ ] Add purchase history and sales history pages for authenticated users.
- [ ] Add authenticated user/profile display in the navbar or account page using the backend current-user endpoint.
- [x] Replace mock-only price history with backend `PriceSnapshot` data.
- [x] Keep similar-card UI backend-backed by catalog metadata only; full similarity remains optional later work.
- [ ] Add mock API endpoints only when frontend JavaScript needs JSON.
- [x] Add tests for current frontend/backend wiring.
- [x] Add regression tests for login session creation and navbar logout behavior.
- [x] Replace existing catalog/listing/detail/collection card image surfaces with the reusable kinetic card component.
- [x] Verified monthly home showcase and shared kinetic card rendering with focused frontend tests and browser checks.
- [x] Verified frontend/backend wiring with `python manage.py test common.test_frontend_integration frontend`.
- [x] Verified full project checks with `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py migrate --check`, and `python manage.py test common catalog users inventory marketplace pricing frontend`.
