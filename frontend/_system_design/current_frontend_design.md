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
- Catalog pages request paginated service results so large catalogs are sliced by the database before template rendering.
- The home page requests only the featured cards and latest listings it displays instead of loading every row first.
- Marketplace pages read real active `MarketListing` data.
- Card detail pages read real active listings and `PriceSnapshot` history.
- Listing detail purchases call the backend marketplace purchase workflow.
- The collection page reads authenticated inventory and collection valuation data through `frontend.services.backend_api`.
- Collection sell forms call the marketplace listing service through `create_marketplace_listing_for_user`, so stock reservation and ownership validation stay in the backend service layer.
- The active listings page reads the authenticated user's active `MarketListing` rows and labels them as listed inventory, not completed sales.
- The home page monthly showcase reads completed `PurchaseOrderLine` rows and displays the highest unit-price card sold during the current calendar month. If there are no completed sales in the current month, it falls back to the first featured catalog card.
- `frontend.services.backend_api` exposes service wrappers for current user,
  inventory management, marketplace listing creation, marketplace purchases,
  purchase/sales history, price history, and collection valuation.

Current frontend UI boundary:

- Catalog/listing/home/detail pages are wired to real backend data.
- `/collection/` is an authenticated frontend page for owned inventory, estimated value, and creating sale listings.
- `/my-listings/` is an authenticated frontend page for cards currently listed for sale.
- The collection and active-listings pages present inventory as set-based albums.
  The view still receives flat backend-backed inventory/listing records, but
  `frontend.services.album_service` projects them into set books, selected-set
  pages, top filters, and pagination data for templates.
- Catalog, marketplace listings, and collection pages now share a browser
  projection with three visualizations: card album pages, set book covers, and
  game shelves. Catalog and marketplace listings default to the card album
  view; collection defaults to set book covers.
- Shared browser rendering lives in
  `frontend/templates/components/browser_view_controls.html` and
  `frontend/templates/components/browser_results.html`. Page templates keep
  their own filters and page-specific actions, but the result layouts come from
  these shared components.
- Album templates preserve backend workflows: collection slots still post
  inventory item id, quantity, and price into the listing-creation path, while
  listing slots link to the existing listing detail page.
- The home search form submits to `/catalog/` with the `q` query parameter, so search uses the catalog filtering path.
- `frontend/templates/components/kinetic_card.html` owns the reusable physical-card visual treatment. It renders only the card surface so existing page components can decide whether the card is linked, listed, or surrounded by metadata.
- `frontend/static/js/kinetic-card.js` progressively enhances elements marked with `data-kinetic-card`; without JavaScript the card remains a normal image surface. The `data-kinetic-card` element is the stable pointer hitbox, while the nested `.kinetic-card__tilt` layer receives the 3D transform so corner pointer math does not reset when the card tilts.
- Card catalog tiles, listing cards, listing rows, detail pages, collection rows, active listing rows, similar cards, and the home monthly showcase all reuse `kinetic_card.html` for visual card rendering.
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
