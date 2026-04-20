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

- `frontend.services.backend_api`
- `frontend.services.catalog_service`
- `frontend.services.listing_service`

These services now use real backend-backed data contracts. Because the frontend
and backend run in the same Django process, server-rendered pages do not make
HTTP requests back into the same server. Instead, frontend services call backend
models, serializers, and service-layer functions while preserving the same
business rules exposed by `/api/...`.

Current backend wiring:

- Catalog pages read real `Card`, `CardVariant`, `CardSet`, and `CardImage` data.
- Marketplace pages read real active `MarketListing` data.
- Card detail pages read real active listings and `PriceSnapshot` history.
- Listing detail purchases call the backend marketplace purchase workflow.
- `frontend.services.backend_api` exposes service wrappers for current user,
  inventory management, marketplace purchases, purchase/sales history, price
  history, and collection valuation.

Current frontend UI boundary:

- Catalog/listing/home/detail pages are wired to real backend data.
- Inventory, purchase history, sales history, and account/profile pages do not
  have full frontend templates yet.
- The service functions for those authenticated APIs exist before the templates
  are built.
- Full image-based similarity is still optional later work; current similar-card
  display uses catalog metadata only.

## Routing

- `/` serves frontend pages.
- `/api/...` is reserved for real backend APIs.
- `/mock-api/...` is reserved for simulated frontend endpoints.

This split lets frontend work continue without pretending that unfinished real
backend APIs already exist.
