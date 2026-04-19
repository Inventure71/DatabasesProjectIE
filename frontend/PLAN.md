# Frontend Implementation Plan

## 1. Project Scope

The frontend will implement the user-facing experience for a **buy-and-sell trading card marketplace**.

It must support:

* browsing cards
* viewing card details
* managing owned inventory
* creating sale listings
* buying cards
* viewing order and sales history
* viewing visually similar cards from image embeddings

The frontend should be clean and functional. The goal is not visual complexity, but a strong interface for database-backed workflows.

---

## 2. Frontend Goals

The frontend must make the following flows easy to use:

1. discover cards in the catalog
2. inspect a card and its variants
3. manage personal inventory
4. list owned cards for sale
5. buy cards from listings
6. inspect value and rarity
7. discover similar cards visually

---

## 3. Frontend Architecture

Recommended approach:

* Django templates with reusable components, or a lightweight frontend consuming Django endpoints
* simple server-rendered pages are enough for MVP
* limited JavaScript for filters, confirmations, and dynamic similarity display

The UI should emphasize:

* card image
* card name
* rarity
* current value
* listing price
* available quantity
* seller identity

---

## 4. Main Frontend Sections

## 4.1 Public / Shared Pages

### Home / Landing page

Purpose:

* explain the system briefly
* show featured cards or latest listings
* provide entry points to catalog and marketplace

Main elements:

* search bar
* featured cards carousel or grid
* latest active listings
* login/register links

### Catalog page

Purpose:

* browse all cards and variants

Main elements:

* search input
* filters: game, set, rarity, language, price range
* sort: name, value, newest
* grid/list of cards

Each result card should show:

* image
* card name
* rarity
* current value
* set name

### Card detail page

Purpose:

* show all relevant information for one card or one variant

Main elements:

* large image
* card metadata
* rarity
* estimated value
* set and edition info
* active listings for this card
* similar cards section
* price history summary

### Listings page

Purpose:

* browse active sale listings

Main elements:

* listing filters
* card image
* card name
* rarity
* seller name
* unit price
* quantity available
* button to buy

---

## 4.2 Authenticated User Pages

### My inventory page

Purpose:

* let the user manage owned cards

Main elements:

* table or card grid of owned inventory
* filters by set, rarity, condition, for-sale state
* quantity display
* condition display
* action buttons: edit, list for sale, remove
* summary stats at top

Summary stats should include:

* total cards owned
* unique variants owned
* estimated collection value
* number of listed cards

### Add inventory page / modal

Purpose:

* manually add owned cards

Main elements:

* searchable card variant selector
* quantity input
* condition selector
* purchase price input
* save button

### Create listing page / modal

Purpose:

* turn owned inventory into a sale listing

Main elements:

* selected inventory item summary
* quantity to list
* unit price input
* currency display
* submit button
* validation feedback

### My listings page

Purpose:

* manage cards currently for sale

Main elements:

* active listings
* paused listings
* sold out listings
* quantity and price
* actions: pause, cancel, view

### Purchase history page

Purpose:

* show cards the user bought

Main elements:

* order cards or table
* purchased card name
* quantity
* total price
* seller
* order status
* purchase date

### Sales history page

Purpose:

* show cards the user sold

Main elements:

* sold card name
* quantity
* buyer
* total price
* order date

---

## 5. Detailed Frontend Feature Plan

## 5.1 Catalog discovery

The user must be able to:

* search cards by text
* filter by rarity
* filter by set
* filter by language
* sort by current value
* open a detailed view

Frontend tasks:

* build reusable search/filter bar
* build card result component
* build pagination or load-more behavior

## 5.2 Card detail display

The detail page must show:

* main image
* card name
* rarity
* current estimated value
* variant information
* set information
* active sale listings
* similar cards
* optional simple chart or table for price history

Frontend tasks:

* build card hero section
* build metadata panel
* build active listings section
* build similar cards component

## 5.3 Inventory management

The user must be able to:

* view owned cards
* add inventory
* update quantity and condition
* mark a card for sale by creating a listing

Frontend tasks:

* build inventory table/grid
* build add inventory form
* build edit inventory form
* build inventory summary cards

## 5.4 Listing management

The user must be able to:

* create a listing from owned inventory
* see current listings
* pause or cancel a listing
* inspect listing status

Frontend tasks:

* build create listing modal/page
* build listing management view
* build status badge component
* build price and quantity validation UI

## 5.5 Buying flow

The user must be able to:

* open a listing
* choose quantity
* confirm purchase
* see purchase success or error state

Frontend tasks:

* build purchase form
* build confirmation state
* build error state when quantity no longer available
* redirect to order history or updated inventory

## 5.6 Similar card discovery

The user must be able to:

* click “similar cards” from a card detail page
* see top visually similar results
* navigate to similar card pages

Frontend tasks:

* build similar cards strip/grid
* show similarity score optionally
* show image + rarity + value for each result

---

## 6. Component Plan

The frontend should be built from reusable UI components.

### Core components

* Navbar
* Search bar
* Filter bar
* Card tile
* Card detail header
* Listing card
* Inventory row
* Status badge
* Summary stat card
* Modal form
* Pagination controls

### Feature-specific components

* Similar cards carousel/grid
* Price history table or mini chart
* Purchase confirmation panel
* Listing action menu

---

## 7. Page-by-Page Implementation Order

### Phase 1. Shared layout and navigation

Tasks:

* base layout
* navbar
* footer if needed
* auth navigation
* page container styling

### Phase 2. Catalog browsing

Tasks:

* catalog page
* search + filters
* card grid
* card detail page

### Phase 3. Inventory pages

Tasks:

* my inventory page
* add inventory form
* edit inventory flow
* inventory summary section

### Phase 4. Marketplace pages

Tasks:

* listings browse page
* create listing page/modal
* my listings page
* listing detail / quick buy flow

### Phase 5. Orders and sales

Tasks:

* purchase history page
* sales history page
* success/failure states

### Phase 6. Similarity UI

Tasks:

* similar cards section on variant detail page
* navigation to similar results
* fallback empty state

### Phase 7. Polish

Tasks:

* better validation messages
* loading and empty states
* better mobile layout
* consistency pass

---

## 8. Required Frontend Data per Page

### Catalog page needs

* cards or variants list
* available filters
* current estimated values
* rarity labels

### Card detail page needs

* variant details
* image
* rarity
* current value
* listings for this variant
* price history
* similar cards results

### Inventory page needs

* owned inventory rows
* quantity
* condition
* for-sale state
* estimated item value

### Listings page needs

* listing rows
* seller
* price
* quantity
* linked card data

### Orders page needs

* order data
* purchased lines
* status
* totals

---

## 9. UX Rules

The frontend should follow these rules:

* card image must always be visible in card-focused views
* rarity and value must always be easy to see
* buying actions must be explicit and confirmed
* inventory editing must validate quantity clearly
* listing status must always be visible
* error states must explain what happened, especially when a listing is no longer available

---

## 10. Validation and Error States

Important frontend states:

### Inventory errors

* invalid quantity
* missing condition
* failed save

### Listing errors

* listed quantity exceeds available quantity
* invalid price
* listing already inactive

### Purchase errors

* listing sold out
* requested quantity unavailable
* purchase failed due to backend validation

### Similarity errors

* no embedding available
* no similar cards found

Each of these should have a clear message and a safe recovery path.

---

## 11. Frontend Testing Plan

### Functional testing

* search and filters work
* card detail renders correctly
* inventory add/edit works
* create listing flow works
* purchase flow works
* similar cards section loads

### UI testing

* pages work on desktop and tablet widths
* empty states render correctly
* validation messages display correctly

### End-to-end flows

* user adds inventory
* user creates listing
* second user buys listing
* listing disappears or updates
* both users see updated histories

---

## 12. Frontend Milestone Plan

### Milestone 1

Base layout + navigation + shared components

### Milestone 2

Catalog browsing and card detail pages

### Milestone 3

Inventory management pages

### Milestone 4

Listings browse and create listing flow

### Milestone 5

Buying flow + order and sales history

### Milestone 6

Similarity UI + final polish

---

## 13. Frontend MVP Definition

The frontend MVP is complete when a user can:

* browse the catalog
* open a card detail page
* see rarity and current value
* add cards to inventory
* list owned cards for sale
* browse listings
* buy a listed card
* see updated order history
* view similar cards on a card page

---

## 14. Final Frontend Positioning

The frontend should be presented as a clean marketplace interface built to expose the relational backend clearly, with strong support for catalog discovery, inventory management, buy/sell workflows, and a small visual similarity feature based on card images.
