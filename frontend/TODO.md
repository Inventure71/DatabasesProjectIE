# Frontend TODO

This file tracks frontend work now that `frontend/` is a sibling Django app.

## Current Status

- [x] Frontend app imported from `origin/Andres`
- [x] Frontend pages mounted at `/`
- [x] Real catalog and listing data are provided through `frontend/services/`
- [x] Stale mock JSON endpoints under `/mock-api/` were removed
- [x] Real backend APIs remain reserved under `/api/`
- [x] Catalog and marketplace pages now read real backend-backed data through frontend services
- [x] Home search submits to catalog filtering instead of staying on the home page
- [x] Catalog page results are paginated so large card sets are sliced by the database
- [x] Home featured cards show the current month's top sold variants and latest listings are limited in the database before rendering
- [x] Listing detail buy form now uses the backend purchase workflow
- [x] Authenticated users can view their collection, estimated value, owned quantities, available stock, and reserved stock
- [x] Authenticated users can add a card they already own from the card detail page through an `Own this card?` secondary action.
- [x] Authenticated users can create sale listings from owned inventory on the card detail page, after opening a card from the collection album
- [x] The collection page now owns listed-inventory discovery: collection cards show owned/listed quantity pills, partially listed buckets keep the normal image treatment, and fully listed buckets use the strong gray image treatment.
- [x] Active listing cards use "Listed by" language so listed inventory is not confused with completed sales
- [x] The old `My Listings` page now redirects authenticated sellers to the collection listed filter instead of splitting listing management into a separate surface.
- [x] Collection pages use set-based album books with selected-set pages, filters, and pagination.
- [x] Catalog, marketplace listings, and collection share the same card/set/shelf browser system.
- [x] Catalog is now the canonical marketplace browsing page; `/listings/` redirects to catalog with the `Only available` filter enabled.
- [x] Shared card album entries are compact enough for practical page-by-page scanning.
- [x] Catalog album card entries use a larger card image and place value on its own row for easier scanning.
- [x] Catalog album card images and home latest-listing images link to their detail pages.
- [x] Catalog/detail navigation is variant-aware, so a selected printing opens by `CardVariant.id` instead of falling back to the first variant for a card.
- [x] My Collection card view renders as a sleeve-only album page; selling is no longer exposed inside collection album slots.
- [x] Shared browser controls clear stale Set/Game filters when moving to book-cover or shelf views, and sidebar search input switches the shared browser back to card view.
- [x] Shared browser filter, pagination, set-book, shelf, and visualization links target the browser results anchor so full-page GET refreshes return near the active browsing controls instead of the page top.
- [x] Anchor navigation is instant instead of smooth so filter/view refreshes do not visibly glide down to the browser area.
- [x] Authenticated backend API wrappers exist for user, inventory, order history, and collection valuation
- [x] Login creates a Django session and the navbar logout form clears it through a CSRF-protected POST
- [x] Reusable kinetic card visual component is shared by card image surfaces across the frontend
- [x] Kinetic cards subtly scale up and brighten their rainbow glass border on hover/focus
- [x] Home central showcase displays the most expensive card sold in the current month, with a featured-card fallback when no monthly sale exists
- [x] Home central showcase copy/card layout is centered as a paired group, with tighter desktop spacing and a centered mobile stack
- [x] Home latest listings now appear above featured cards, and their browse link opens the shared catalog browser filtered to available cards.
- [x] Database-backed frontend sections now include query walkthrough popups that explain the relevant Django ORM path, tables, filtering steps, ordering, and limits.
- [x] Visible website brand and page-title references now use `TCGNET`.

## Working Rules

- Keep templates and static assets in `frontend/`.
- Use `frontend/services/` as the boundary between pages and data.
- Do not mount `/mock-api/...` routes unless a future JavaScript feature explicitly needs temporary simulated JSON.
- Do not create fake endpoints under `/api/...`; that namespace belongs to the real backend.
- Keep service internals backed by real Django models/services when the backend feature exists.

## Next Steps

- [x] Replace mock catalog/listing services with real backend-backed data contracts.
- [x] Add service functions for authenticated inventory management.
- [x] Add a real listing detail page and connect the buy flow to the backend purchase endpoint.
- [x] Add frontend pages for authenticated inventory management.
- [x] Add frontend page for authenticated active listing management visibility.
- [x] Convert collection and active listing management surfaces from flat rows into set album views.
- [x] Add shared visualization controls for card album, collection book cover, and game shelf views.
- [x] Add an `Only available` catalog filter for cards with active marketplace listings and route marketplace browsing through it.
- [x] Move the collection sell action from album cards to the opened card detail page.
- [x] Show owned active listings inside the card detail `Your Copies` section so selling and monitoring listed copies share one workflow, without exposing another sell form for already-listed copies.
- [x] Hide sold-out zero-quantity inventory rows from frontend owned collection/detail views while preserving backend listing and purchase history references.
- [ ] Add purchase history and sales history pages for authenticated users.
- [ ] Add authenticated user/profile display in the navbar or account page using the backend current-user endpoint.
- [x] Replace mock-only price history with backend `PriceSnapshot` data.
- [x] Keep similar-card UI backend-backed by catalog metadata only; full similarity remains optional later work.
- [x] Removed stale mock API endpoints and fake catalog/listing data.
- [ ] Add a temporary mock API only if future frontend JavaScript needs JSON before the matching backend endpoint exists.
- [x] Add tests for current frontend/backend wiring.
- [x] Add regression tests for login session creation and navbar logout behavior.
- [x] Replace existing catalog/listing/detail/collection card image surfaces with the reusable kinetic card component.
- [x] Verified monthly home showcase and shared kinetic card rendering with focused frontend tests and browser checks.
- [x] Verified monthly home showcase desktop and mobile spacing with browser geometry checks.
- [x] Verified shared browser filter reset behavior with focused frontend regression tests.
- [x] Verified shared browser anchor preservation with focused frontend regression tests.
- [x] Verified current browser unification, listed-card overlay, sold-out ownership, and card-detail listing regressions with focused frontend tests.
- [x] Verified partial-versus-full listed collection card treatment with focused frontend regression tests.
- [x] Verified catalog/listings unification and home latest-listings ordering with focused frontend regression tests.
- [x] Verified query walkthrough popups render on home, catalog, card detail, collection, and listing detail pages with focused frontend regression tests.
- [x] Verified `TCGNET` website-name replacement with a frontend text scan and focused frontend tests.
- [x] Restore the collection add-inventory POST flow using the aggregate inventory model; duplicate owner/card/condition additions merge into one quantity bucket.
- [x] Add a dedicated `POST /collection/add/` route and card-detail `Own this card?` disclosure for adding owned cards without asking for purchase price.
