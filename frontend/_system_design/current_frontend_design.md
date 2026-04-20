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
- The catalog page is the canonical card browsing surface. Marketplace browsing
  is represented as the same catalog browser with `available=1`, which filters
  cards down to variants that have active, quantity-available marketplace
  listings.
- Card detail pages read real active listings and `PriceSnapshot` history.
- Listing detail purchases call the backend marketplace purchase workflow.
- The collection page reads authenticated inventory and collection valuation data through `frontend.services.backend_api`.
- Collection sell forms call the marketplace listing service through `create_marketplace_listing_for_user`, so stock reservation and ownership validation stay in the backend service layer.
- The legacy `/listings/` route is retained as a compatibility entry point, but
  it redirects to `/catalog/?available=1#browser` instead of rendering a
  separate marketplace browser.
- The home page monthly showcase reads completed `PurchaseOrderLine` rows and displays the highest unit-price card sold during the current calendar month. If there are no completed sales in the current month, it falls back to the first featured catalog card.
- The home page monthly showcase uses a centered two-column content group on desktop so the sale copy stays visually paired with the kinetic card instead of drifting toward the left edge. On mobile, the same showcase stacks with centered copy above the card.
- `frontend.services.backend_api` exposes service wrappers for current user,
  inventory management, marketplace listing creation, marketplace purchases,
  purchase/sales history, price history, and collection valuation.

Current frontend UI boundary:

- Catalog/listing/home/detail pages are wired to real backend data.
- `/collection/` is an authenticated frontend page for owned inventory, estimated value, listed-inventory discovery, and opening owned cards as an album.
- Card detail pages own the listing-creation UI for authenticated owners. A user opens a card from the collection album, chooses one of their owned copies, and submits inventory item id, quantity, and price from that card-specific page.
- `/my-listings/` is retained as a compatibility route, but authenticated users are redirected to `/collection/?view=card&my_listings=listed#browser`.
- Listed inventory is treated as collection state, not a separate top-level area. Collection cards with active listings remain visible in the collection browser with a strong gray listed treatment and an over-image listed-count badge, and the collection sidebar includes a `My Listings` filter for listed-only inventory.
- Frontend owned-inventory views intentionally exclude zero-quantity `InventoryItem` rows. Sold-out rows remain in the database so protected marketplace listing and purchase-history references stay intact, but they no longer appear as owned cards.
- The collection page presents inventory as set-based albums.
  The view still receives flat backend-backed inventory/listing records, but
  `frontend.services.album_service` projects them into set books, selected-set
  pages, top filters, and pagination data for templates.
- Catalog and collection pages now share a browser projection with three
  visualizations: card album pages, set book covers, and game shelves. Catalog
  defaults to the card album view; collection defaults to set book covers.
- The catalog sidebar owns the `Only available` filter. Turning it on keeps the
  user on the same browser and filters to cards that can currently be bought.
- Shared browser controls avoid carrying stale grouping filters into views where
  they are misleading: switching to set book covers clears the selected set,
  switching to shelves clears the selected game, and manually editing a sidebar
  search field sets the submitted view back to card album mode.
- Shared browser GET actions and links append the `#browser` fragment. This
  keeps URL state shareable while asking the browser to restore the user's
  vertical context near the active results instead of reloading at the page top.
  Global anchor scrolling is intentionally instant, because smooth scrolling
  makes full-page GET refreshes look like a delayed animated jump.
- Shared browser rendering lives in
  `frontend/templates/components/browser_view_controls.html` and
  `frontend/templates/components/browser_results.html`. Page templates keep
  their own filters and page-specific actions, but the result layouts come from
  these shared components.
- Shared card album entries are intentionally compact: each listing/catalog
  slot keeps the card image, name, rarity, set, one page-specific metadata line,
  essential counts/prices, and the primary action only.
- Catalog card album slots bias more space toward the image: language and finish
  remain side by side, while value moves onto its own row below them.
- Card image surfaces are navigational when the surrounding component has a
  natural detail target. Catalog album images link to card detail pages, and
  home latest-listing images link to listing detail pages.
- Collection card view is intentionally different from listing/catalog card
  view: it renders sleeve-style album slots with only the large card image and
  short caption, so it feels like looking through a physical binder. The sell
  action is not available in collection album slots.
- Listing creation from owned stock happens on the card detail page. That page
  lists the authenticated owner's copies for the selected card and posts through
  `create_marketplace_listing_for_user`, preserving backend ownership and stock
  reservation rules.
- Card detail also monitors active listings for owned copies in `Your Copies`,
  so a seller can see which copies are already listed without leaving the card
  workflow. Already-listed copies show monitoring state instead of another sell
  form, while unlisted available copies can still be listed from the same
  section. Buying remains in the active marketplace listings area on the same
  card detail page.
- The home search form submits to `/catalog/` with the `q` query parameter, so search uses the catalog filtering path.
- On the home page, latest active listings appear above featured catalog cards.
  The latest-listings browse link opens the catalog browser with `available=1`
  so listed cards and catalog cards use one shared page.
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
