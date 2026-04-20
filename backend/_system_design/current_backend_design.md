# Current Backend Design

This file documents how the backend is currently structured. It should be updated as verified backend pieces are added.

## Foundation

- Django command entrypoint: repository-root `manage.py`
- Backend source root: `backend/`
- Frontend source root: `frontend/`
- Django settings module: `config.settings`
- Database: MySQL
- API framework: Django REST Framework
- Auth foundation: Django built-in auth
- Shared infrastructure app: `common`

The root `manage.py` prepends `backend/` to `sys.path`. That keeps backend
apps importable as `common`, `catalog`, `inventory`, `users`, `marketplace`,
and `pricing` while allowing `frontend/` to live as a sibling folder.

## Frontend Integration Boundary

The project is still one Django application at runtime, but ownership is split
by folder:

- `backend/` owns persistence, business rules, and real API endpoints.
- `frontend/` owns templates, static assets, frontend views, and simulated
  frontend data contracts.

Routing convention:

- `/` and page routes such as `/catalog/` are served by `frontend.urls`.
- `/api/...` is reserved for real backend APIs.
- `/mock-api/...` is reserved for frontend simulation endpoints used while the
  real backend endpoint or model flow is not ready.

The frontend should keep fake data behind service modules such as
`frontend.services.catalog_service` and `frontend.services.listing_service`.
When backend functionality is ready, replace the service internals with real
queries or real API calls without changing templates first.

## Shared Infrastructure

### `common.models.TimeStampedModel`

Abstract base model for timestamped database records.

Fields:

- `created_at`
- `updated_at`

Important behavior:

- It is abstract, so Django does not create a `common_timestamps` table.
- Child models inherit the timestamp fields.

## Users

### `users.models.UserProfile`

`UserProfile` extends Django's built-in user model without replacing authentication.

Relationship:

- One `UserProfile` belongs to one Django user.
- The relation uses `related_name="profile"`, so profile access is `user.profile`.
- Deleting the user deletes the profile through cascade behavior.

Fields:

- `user`
- `display_name`
- `bio`
- `country`
- `avatar_url`
- `created_at`
- `updated_at`

Database table:

- `user_profile`

Admin:

- `UserProfile` is registered in Django admin.

Verified behavior:

- A profile belongs to exactly one user.
- `user.profile` resolves back to the profile.
- `str(profile)` returns `display_name`.
- Timestamps are populated on create.

### `GET /api/users/me/`

Returns the currently authenticated user's basic account and profile data.

Route name:

- `users-me`

Authentication:

- Requires an authenticated user.
- Anonymous requests are rejected by DRF permissions.

Response shape:

```json
{
  "id": 1,
  "username": "buyer",
  "email": "buyer@example.com",
  "profile": {
    "display_name": "Buyer One",
    "bio": "Collects rare cards.",
    "country": "Spain",
    "avatar_url": "https://example.com/avatar.png"
  }
}
```

Implementation:

- `users.views.CurrentUserView`
- `users.serializers.CurrentUserSerializer`
- `users.serializers.UserProfileSerializer`

## Planned Catalog, Inventory, And Marketplace References

The backend should reference cards through foreign keys, not by copying card names or text between tables.

Reference overview:

```text
CardSet.game_id                 -> CardGame.id
Card.game_id                    -> CardGame.id
CardVariant.card_id             -> Card.id
CardVariant.set_id              -> CardSet.id
CardImage.card_variant_id       -> CardVariant.id

InventoryItem.owner_id          -> User.id
InventoryItem.card_variant_id   -> CardVariant.id
InventoryHistory.inventory_item_id -> InventoryItem.id
InventoryHistory.created_by_id     -> User.id
MarketListing.inventory_item_id -> InventoryItem.id
MarketListing.seller_id         -> User.id

PurchaseOrder.buyer_id          -> User.id
PurchaseOrder.seller_id         -> User.id
PurchaseOrderLine.purchase_order_id -> PurchaseOrder.id
PurchaseOrderLine.listing_id        -> MarketListing.id
PurchaseOrderLine.card_variant_id   -> CardVariant.id
PriceSnapshot.card_variant_id       -> CardVariant.id
```

Important cross-references:

- `CardSet.game_id` points to `CardGame.id`.
- `Card.game_id` points to `CardGame.id`.
- `CardVariant.card_id` points to `Card.id`.
- `CardVariant.set_id` points to `CardSet.id`.
- `CardImage.card_variant_id` points to `CardVariant.id` and is unique because the relation is one-to-one.
- `InventoryItem.owner_id` points to the Django user table.
- `InventoryItem.card_variant_id` points to `CardVariant.id`.
- `InventoryHistory.inventory_item_id` points to `InventoryItem.id`.
- `InventoryHistory.created_by_id` points to the Django user table and can be null.
- `MarketListing.seller_id` points to the Django user table.
- `MarketListing.inventory_item_id` points to `InventoryItem.id`.
- `PurchaseOrder.buyer_id` points to the Django user table.
- `PurchaseOrder.seller_id` points to the Django user table.
- `PurchaseOrderLine.purchase_order_id` points to `PurchaseOrder.id`.
- `PurchaseOrderLine.listing_id` points to `MarketListing.id`.
- `PurchaseOrderLine.card_variant_id` points to `CardVariant.id`.
- `PriceSnapshot.card_variant_id` points to `CardVariant.id`.

Rule:

- Catalog tables describe official card data.
- Inventory references `CardVariant` because users own exact variants, not abstract cards.
- Listings reference `InventoryItem` because users can only sell stock they own.
- Order lines snapshot `CardVariant`, quantity, and price so transaction history stays readable even if listings change later.
- Pricing snapshots reference `CardVariant` because price history belongs to an exact variant, not to an abstract card.

Staged migration note:

- `InventoryHistory.related_listing_id` and `InventoryHistory.related_order_id` are intentionally not implemented yet.
- They should be added after `MarketListing` and `PurchaseOrder` exist.

## Catalog

The catalog stores official card data. It is the source of truth for what cards and variants exist.

### `catalog.models.CardGame`

Represents a trading card game or franchise.

Examples:

- Pokemon
- Magic
- Yu-Gi-Oh

Important fields:

- `name`
- `slug`
- `description`

### `catalog.models.CardSet`

Represents a release set inside a game.

Important relationship:

- `game` points to `CardGame`

Important fields:

- `name`
- `code`
- `release_date`
- `description`

Rule:

- A set code must be unique within one game.

### `catalog.models.Card`

Represents the stable card identity.

This is where we store information that belongs to the card itself, not to a specific printing.

Important relationship:

- `game` points to `CardGame`

Important fields:

- `name`
- `card_type`
- `subtype`
- `description`
- `artist_name`
- `attack`
- `defense`
- `hp`

### `catalog.models.CardVariant`

Represents a specific catalog version or printing of a card.

Important relationships:

- `card` points to `Card`
- `set` points to `CardSet`

Important fields:

- `collector_number`
- `rarity`
- `finish`
- `language`
- `edition_label`
- `is_first_edition`
- `current_value`

Rules:

- `current_value` cannot be negative.
- The same card printing identity cannot be duplicated for the same card, set, collector number, finish, language, edition label, and first-edition flag.

### `catalog.models.CardImage`

Represents an image attached to a specific variant.

Important relationship:

- `card_variant` points to `CardVariant` through a one-to-one relationship.
- Each `CardVariant` can have at most one `CardImage`.

Important fields:

- `image_url`
- `image_hash`
- `width`
- `height`

Decision:

- On 2026-04-20, we decided to use a single image per `CardVariant`.
- This is enforced with a one-to-one relationship from `CardImage` to `CardVariant`.
- Code should access the image from a variant as `variant.image`, not `variant.images.all()`.
- `is_primary` was removed because the concept is redundant when only one image can exist.

### Pokemon Cards Dataset Import Command

Command:

```bash
python manage.py import_pokemon_cards_dataset
```

Default source:

- `original_datasets/pokemon-cards/pokemon-cards.csv`

Default import scope:

- Source CSV `set_name`: `Base`
  - Stored catalog set name: `Base Set`
  - Stored catalog set code: `BASE`
  - Collector number denominator: `102`
- Source CSV `set_name`: `Jungle`
  - Stored catalog set name: `Jungle`
  - Stored catalog set code: `JUNGLE`
  - Collector number denominator: `64`

Purpose:

- Import the downloaded Pokemon card dataset into the catalog as ownable card variants.
- Start with the available Base and Jungle Pokemon cards from the downloaded CSV.
- Avoid duplicate catalog rows when the command is rerun.

Important mapping:

- `CardGame` is `Pokemon`.
- `CardSet` is chosen from the supported import set mapping.
- `Card.name` comes from CSV `name`.
- `Card.hp` comes from CSV `hp`.
- `Card.description` stores the CSV `caption`.
- `Card.subtype` is parsed from caption text like `of type Fire`.
- `CardVariant.collector_number` is parsed from CSV id, for example `base1-4` becomes `4/102` and `base2-4` becomes `4/64`.
- `CardVariant.rarity` is parsed from caption rarity text.
- `CardVariant.finish` is `HOLO` when the caption rarity contains `Holo`; otherwise it is `NORMAL`.
- `CardVariant.language` is `en`.
- `CardVariant.current_value` starts at `0.00`.
- `CardImage.image_url` comes from CSV `image_url`.

Important behavior:

- The command uses `update_or_create` for game, set, cards, variants, and images.
- Running it repeatedly updates existing rows instead of creating duplicates.
- The current downloaded CSV has 69 rows where `set_name` is `Base` and 63 rows where `set_name` is `Jungle`.
- The default import currently loads 132 ownable variants from those two sets.
- This is still a partial classic catalog because the Base import does not include Trainer/Energy cards.
- The command is tested by `ImportPokemonCardsDatasetCommandTests`.

## Catalog Read API

The catalog API is read-only. It exposes official catalog data before inventory and marketplace features exist.

### Routes

- `GET /api/catalog/cards/`
- `GET /api/catalog/cards/<id>/`
- `GET /api/catalog/variants/<id>/`
- `GET /api/catalog/sets/`

### Serializers

Serializers live in `catalog/serializers.py`.

- `CardGameSummarySerializer` returns small game objects.
- `CardSetSerializer` returns set data with nested game data.
- `CardImageSerializer` returns image fields for a variant.
- `CardSummarySerializer` returns small card objects.
- `CardVariantSummarySerializer` returns variant data for card detail pages.
- `CardListSerializer` returns compact card rows for the card list endpoint.
- `CardDetailSerializer` returns card details and all variants for that card.
- `CardVariantDetailSerializer` returns one exact variant, including card, set, and image data.

### Views

Views live in `catalog/views.py`.

- `CardListView` lists cards, supports filters, and uses page-number pagination.
- `CardDetailView` returns one card with its variants.
- `CardVariantDetailView` returns one exact card variant with its image.
- `CardSetListView` lists catalog sets.

### Filters

`GET /api/catalog/cards/` supports:

- `name`: partial case-insensitive card-name search.
- `game`: filters by `CardGame.slug`.
- `set`: filters by `CardSet.code`.
- `rarity`: filters by `CardVariant.rarity`.
- `page`: page number for result pagination.
- `page_size`: page size for result pagination, capped at 100.

Example:

```bash
GET /api/catalog/cards/?name=zard
GET /api/catalog/cards/?game=pokemon
GET /api/catalog/cards/?set=BASE
GET /api/catalog/cards/?rarity=RARE
```

### Query Behavior

- `select_related("game")` is used where the related object is a single foreign-key row.
- `prefetch_related("variants__set__game")` is used for card detail because one card can have many variants.
- The card list endpoint returns `count`, `next`, `previous`, and `results` so clients do not need to load the whole catalog.
- The card list endpoint is tested to use a fixed query count for representative fixture data.

## Inventory

Inventory stores what users own. Users own exact `CardVariant` rows, not abstract `Card` rows.

### `inventory.models.InventoryItem`

Represents one user's stock for one variant in one condition.

Important relationships:

- `owner` points to the Django user table.
- `card_variant` points to `CardVariant`.

Important fields:

- `condition`
- `quantity`
- `reserved_quantity`
- `is_for_sale`
- `acquired_at`
- `purchase_price`
- `created_at`
- `updated_at`

Rules:

- `quantity` cannot be negative.
- `reserved_quantity` cannot be negative.
- `reserved_quantity` cannot be greater than `quantity`.
- `purchase_price` can be empty, but cannot be negative when present.
- One user cannot have duplicate rows for the same `card_variant` and `condition`.

Important marketplace behavior:

- Inventory service functions that create or increase stock still require positive quantity.
- Persisted inventory rows may reach `quantity=0` after marketplace purchases.
- Keeping the row at zero preserves inventory history and protected listing/order references.

Computed property:

- `available_quantity` returns `quantity - reserved_quantity`.

Why the uniqueness rule exists:

- If one user owns the same variant in the same condition multiple times, we merge that into one row and increase `quantity`.
- If the condition differs, it gets a separate row because condition changes sale value.

### `inventory.models.InventoryHistory`

Records stock changes for an inventory item.

Important relationships:

- `inventory_item` points to `InventoryItem`.
- `created_by` points to the Django user table and can be null.

Important fields:

- `change_type`
- `quantity_delta`
- `note`
- `created_at`

Current change types:

- `ADD`
- `INCREASE`
- `DECREASE`
- `RESERVE`
- `RELEASE`
- `PURCHASE`
- `ADJUST`

Staged marketplace note:

- History does not yet link to listings or orders because marketplace tables do not exist yet.
- Those nullable links should be added in a later migration after marketplace models are created.

## Inventory Services

Inventory services live in `inventory/services.py`. They are the trusted entry point for stock changes.

Reason:

- Views and future admin actions should not manually edit inventory quantities.
- Central services keep validation, locking, saving, and history writing consistent.

### Service Functions

`add_inventory_item`

- Creates a new inventory row when the user does not already own that variant in that condition.
- If the row already exists, it increases `quantity` instead of creating a duplicate.
- Writes `ADD` history for new rows and `INCREASE` history for merges.

`increase_quantity`

- Adds to an existing inventory item's `quantity`.
- Writes `INCREASE` history.

`decrease_quantity`

- Removes from available stock.
- Rejects decreases larger than `available_quantity`.
- Writes `DECREASE` history with a negative `quantity_delta`.

`reserve_quantity`

- Moves stock from available to reserved.
- Rejects reservations larger than available stock.
- Writes `RESERVE` history.

`release_reserved_quantity`

- Moves stock from reserved back to available.
- Rejects releases larger than reserved stock.
- Writes `RELEASE` history with a negative `quantity_delta`.

`merge_purchased_item`

- Adds purchased stock into the buyer's inventory.
- Creates or merges into the buyer's existing owner/variant/condition row.
- Writes `PURCHASE` history.

### Transaction Behavior

- Every service uses `transaction.atomic()`.
- Services that modify an existing item reload it with `select_for_update()`.
- `select_for_update()` locks the inventory row during the transaction so concurrent operations cannot safely modify the same stock at the same time.

### Validation Behavior

- Every quantity argument must be greater than zero.
- Services call `full_clean()` before saving changed inventory rows.
- Invalid operations raise `ValidationError`.

### History Meaning

- `ADD`: first creation of an inventory row.
- `INCREASE`: owned quantity increased after the row already existed.
- `DECREASE`: owned quantity decreased.
- `RESERVE`: quantity moved into reserved stock.
- `RELEASE`: reserved quantity released back to available stock.
- `PURCHASE`: stock added to a buyer after purchase.
- `ADJUST`: reserved for future manual corrections.

## Inventory API

The inventory API lets an authenticated user manage only their own inventory.

Routes:

- `GET /api/inventory/my/`
- `POST /api/inventory/my/add/`
- `POST /api/inventory/my/<id>/update/`
- `POST /api/inventory/my/<id>/remove/`

Authentication:

- Every inventory API endpoint uses DRF `IsAuthenticated`.
- Anonymous requests are rejected before inventory data is returned or changed.

Ownership rule:

- Inventory views query only rows where `owner=request.user`.
- If a user requests another user's inventory item id, the API returns `404 Not Found`.
- This avoids revealing whether another user's inventory row exists.

### Response Serializer

`InventoryItemSerializer` returns the owned row plus compact catalog data for the exact variant.

Important response fields:

- `id`
- `card_variant`
- `condition`
- `quantity`
- `reserved_quantity`
- `available_quantity`
- `is_for_sale`
- `acquired_at`
- `purchase_price`

Nested variant data includes:

- variant id
- card id and card name
- set id, set name, and set code
- collector number
- rarity
- finish
- language

### `GET /api/inventory/my/`

Lists inventory rows for the logged-in user.

Implementation:

- View: `inventory.views.MyInventoryListView`
- Serializer: `inventory.serializers.InventoryItemSerializer`
- Query behavior: filters by owner and uses `select_related("card_variant__card", "card_variant__set")`.

### `POST /api/inventory/my/add/`

Creates or merges inventory for the logged-in user.

Expected request body:

```json
{
  "card_variant_id": 1,
  "condition": "NEAR_MINT",
  "quantity": 2,
  "purchase_price": "100.00"
}
```

Implementation:

- Request serializer: `inventory.serializers.AddInventoryItemSerializer`
- Service: `inventory.services.add_inventory_item`

Behavior:

- If no matching owner, variant, and condition row exists, the service creates one.
- If a matching row already exists, the service increases its quantity.
- The service writes inventory history.

### `POST /api/inventory/my/<id>/update/`

Applies a stock action to one owned inventory row.

Expected request body:

```json
{
  "action": "RESERVE",
  "quantity": 1
}
```

Supported actions:

- `INCREASE`
- `DECREASE`
- `RESERVE`
- `RELEASE`

Implementation:

- Request serializer: `inventory.serializers.InventoryUpdateSerializer`
- Services:
  - `inventory.services.increase_quantity`
  - `inventory.services.decrease_quantity`
  - `inventory.services.reserve_quantity`
  - `inventory.services.release_reserved_quantity`

Behavior:

- Serializer validation checks request shape and positive quantity.
- Service validation checks business rules, such as not reserving more than available quantity.
- Service validation failures return `400 Bad Request`.
- Successful changes write inventory history.

### `POST /api/inventory/my/<id>/remove/`

Safely reduces available stock for one owned inventory row.

Expected request body:

```json
{
  "quantity": 1
}
```

Implementation:

- Request serializer: `inventory.serializers.RemoveInventoryQuantitySerializer`
- Service: `inventory.services.decrease_quantity`

Behavior:

- The endpoint reduces quantity only through the service layer.
- It rejects attempts to remove more than available stock.
- It writes `DECREASE` history.
- It does not delete the final inventory row yet.

Why full row deletion is deferred:

- `InventoryHistory` currently belongs to `InventoryItem`.
- Deleting an `InventoryItem` would also delete its history because the foreign key uses cascade behavior.
- We will revisit full deletion after marketplace/order history exists, because audit history should not disappear accidentally.

## Marketplace

Marketplace stores listings and purchase records. Listings point to inventory because sellers can only sell cards they own.

### `marketplace.models.MarketListing`

Represents one seller listing part of one owned inventory row for sale.

Important relationships:

- `seller` points to the Django user table.
- `inventory_item` points to `InventoryItem`.

Important fields:

- `status`
- `quantity`
- `quantity_available`
- `unit_price`
- `currency`
- `created_at`
- `updated_at`

Statuses:

- `ACTIVE`
- `PAUSED`
- `SOLD_OUT`
- `CANCELLED`

Rules:

- `quantity` must be greater than zero.
- `quantity_available` cannot be negative.
- `quantity_available` cannot be greater than `quantity`.
- `unit_price` cannot be negative.
- `SOLD_OUT` listings must have `quantity_available=0`.
- The listing `seller` must be the same user as `inventory_item.owner`.

Why listings reference inventory:

- A listing is not just "Charizard for sale".
- A listing is "this seller is selling this quantity from this exact owned inventory row".
- That keeps marketplace stock tied to real ownership.

Quantity design:

- `quantity` is the original amount listed.
- `quantity_available` is the amount still available to buy from this listing.
- These are stored on the listing instead of being calculated only from inventory, because a listing needs its own marketplace state.
- Future listing services must keep listing quantities and inventory reservations consistent.

Current stock rule:

- Creating an active listing immediately reserves inventory.
- Cancelling a listing releases the remaining available reserved inventory.
- Sold-out listing transitions require `quantity_available=0`.
- Purchase services will later be responsible for reducing listing availability and seller inventory together.

### `marketplace.models.PurchaseOrder`

Represents one buyer-to-seller purchase transaction.

Important relationships:

- `buyer` points to the Django user table.
- `seller` points to the Django user table.

Important fields:

- `status`
- `total_amount`
- `currency`
- `created_at`
- `updated_at`

Statuses:

- `PENDING`
- `COMPLETED`
- `CANCELLED`
- `FAILED`

Rules:

- `total_amount` cannot be negative.
- `buyer` and `seller` must be different users.

Why orders are separate from listings:

- Listings describe what is currently for sale.
- Orders describe a transaction that happened or was attempted.
- Keeping them separate lets listings change without losing transaction history.

### `marketplace.models.PurchaseOrderLine`

Represents one purchased listing line inside an order.

Important relationships:

- `purchase_order` points to `PurchaseOrder`.
- `listing` points to `MarketListing`.
- `card_variant` points to `CardVariant`.

Important fields:

- `quantity`
- `unit_price`
- `created_at`
- `updated_at`

Computed property:

- `line_total` returns `quantity * unit_price`.

Rules:

- `quantity` must be greater than zero.
- `unit_price` cannot be negative.
- `card_variant` must match the listed inventory item's card variant.
- The listing seller must match the order seller.

Why order lines snapshot card and price:

- `PurchaseOrderLine.card_variant` stores the exact card variant that was bought.
- `PurchaseOrderLine.unit_price` stores the price at purchase time.
- This keeps purchase history readable even if the listing price or catalog value changes later.

### Marketplace Admin

Registered models:

- `MarketListing`
- `PurchaseOrder`
- `PurchaseOrderLine`

Purpose:

- Inspect listings, orders, and order lines during development.
- Validate marketplace relationships while services and APIs are built.

### Marketplace Migration

Initial marketplace migration:

- `marketplace.0001_initial`

Tables created:

- `market_listing`
- `purchase_order`
- `purchase_order_line`

## Listing Services

Listing services live in `marketplace/services.py`. They are the trusted entry point for listing state changes.

Reason:

- Listing changes affect inventory reservations.
- Views and future APIs should not manually set listing status or reserved inventory fields.
- Keeping this logic in services gives us one place to enforce ownership, stock checks, and transition rules.

### Service Functions

`create_listing`

- Creates an active `MarketListing`.
- Requires the seller to own the `InventoryItem`.
- Requires positive quantity.
- Requires non-negative unit price.
- Requires requested quantity to be no greater than `InventoryItem.available_quantity`.
- Reserves the listed quantity immediately using `inventory.services.reserve_quantity`.
- Sets both `quantity` and `quantity_available` to the requested listing quantity.

`pause_listing`

- Changes an active listing to `PAUSED`.
- Rejects listings that do not belong to the seller.
- Rejects listings that are not currently `ACTIVE`.
- Does not release inventory because a paused listing may be resumed later.

`cancel_listing`

- Changes an active or paused listing to `CANCELLED`.
- Rejects listings that do not belong to the seller.
- Releases the listing's remaining `quantity_available` from reserved inventory using `inventory.services.release_reserved_quantity`.
- Sets `quantity_available` to zero.

`mark_listing_sold_out`

- Changes an active or paused listing to `SOLD_OUT`.
- Rejects listings that do not belong to the seller.
- Requires `quantity_available` to already be zero.
- Does not release inventory, because sold-out means the listed quantity was consumed by purchases.

### Transaction Behavior

- Every listing service uses `transaction.atomic()`.
- `create_listing` locks the inventory row with `select_for_update()`.
- Listing transition services lock the listing row with `select_for_update()`.
- Inventory reservation and release happen in the same transaction as the listing change.

### Current Boundary

- Listing services exist.
- Listing read API endpoints exist.
- Listing write API endpoints do not exist yet.
- Purchase services do not exist yet.
- Resume-listing behavior is intentionally not implemented yet; we will add it only if the frontend or marketplace flow needs it.

## Marketplace Read API

The marketplace read API exposes public listing browsing and authenticated order history.

Routes:

- `GET /api/marketplace/listings/`
- `GET /api/marketplace/listings/<id>/`
- `GET /api/marketplace/my/sales/`
- `GET /api/marketplace/my/purchases/`

### Public Listing Reads

`GET /api/marketplace/listings/`

- Lists public marketplace listings.
- Does not require authentication.
- Returns only listings with `status=ACTIVE`.
- Returns only listings with `quantity_available > 0`.

Supported filters:

- `seller`: filters by seller id.
- `card_variant`: filters by exact `CardVariant.id`.
- `status`: only `ACTIVE` can return results; other status values return an empty list.
- `price_min`: filters by `unit_price >= price_min`.
- `price_max`: filters by `unit_price <= price_max`.

`GET /api/marketplace/listings/<id>/`

- Returns one public listing.
- Does not require authentication.
- Uses the same public visibility rule as the list endpoint.
- Returns `404 Not Found` for paused, cancelled, sold-out, or unavailable listings.

Listing response data includes:

- listing id
- seller id and username
- nested card variant data
- inventory condition
- status
- quantity
- quantity available
- unit price
- currency

### Private Order History Reads

`GET /api/marketplace/my/sales/`

- Requires authentication.
- Returns only orders where `seller=request.user`.
- Includes nested order lines.

`GET /api/marketplace/my/purchases/`

- Requires authentication.
- Returns only orders where `buyer=request.user`.
- Includes nested order lines.

Order response data includes:

- order id
- buyer id and username
- seller id and username
- status
- total amount
- currency
- created timestamp
- order lines

Order line response data includes:

- line id
- listing id
- nested card variant data
- quantity
- unit price
- line total

### Query Behavior

- Listing reads use `select_related` for seller, inventory item, card variant, card, and set.
- Order history reads use `select_related` for buyer and seller.
- Order history reads use `prefetch_related` for order lines and their card variant data.

### Current Boundary

- Marketplace read API exists.
- Marketplace listing creation/update API does not exist yet.
- Purchase workflow exists.
- Buy endpoint exists.

## Purchase Workflow

The purchase workflow lives in `marketplace/services.py` as `purchase_listing`.

Purpose:

- Safely buy quantity from one active listing.
- Keep listing availability, seller inventory, buyer inventory, orders, and history consistent.
- Roll back all changes if validation fails.

### `purchase_listing`

Inputs:

- `buyer`
- `listing`
- `quantity`

Validation:

- Purchase quantity must be greater than zero.
- Buyer cannot be the listing seller.
- Listing must be `ACTIVE`.
- Requested quantity cannot exceed `listing.quantity_available`.
- Seller inventory must still have enough reserved quantity for the listing.

Transaction behavior:

- Runs inside `transaction.atomic()`.
- Locks the listing row with `select_for_update()`.
- Locks the seller inventory row with `select_for_update()`.
- Creates the order, order line, inventory updates, history rows, and listing update in one transaction.
- If an exception is raised, Django rolls back the whole purchase attempt.

Successful purchase steps:

- Create a `PurchaseOrder` for buyer and seller.
- Create a `PurchaseOrderLine` snapshot with listing, card variant, quantity, and unit price.
- Decrease seller `InventoryItem.quantity`.
- Decrease seller `InventoryItem.reserved_quantity`.
- Write seller `InventoryHistory` with `DECREASE`.
- Create or merge buyer inventory using `inventory.services.merge_purchased_item`.
- Write buyer `InventoryHistory` with `PURCHASE`.
- Decrease `MarketListing.quantity_available`.
- If listing availability reaches zero, mark listing `SOLD_OUT`.
- Mark the order `COMPLETED`.

Failure behavior:

- Inactive listing: raises `ValidationError`; no order or inventory changes remain.
- Insufficient listing availability: raises `ValidationError`; no order or inventory changes remain.
- Seller buying own listing: raises `ValidationError`; no order or inventory changes remain.
- Database error: transaction rolls back automatically.

Inventory zero-quantity rule:

- A seller can sell their final owned quantity.
- In that case, seller inventory becomes `quantity=0` and `reserved_quantity=0`.
- The inventory row is kept instead of deleted because listings and history reference it.

Current boundary:

- Purchase service exists.
- HTTP buy endpoint exists.

## Buy Endpoint

The buy endpoint exposes the purchase workflow through one authenticated API entry point.

Route:

- `POST /api/marketplace/listings/<id>/buy/`

Authentication:

- Requires an authenticated user.
- Anonymous requests are rejected before purchase logic runs.

Expected request body:

```json
{
  "quantity": 1
}
```

Implementation:

- Request serializer: `marketplace.serializers.BuyListingSerializer`
- View: `marketplace.views.BuyListingView`
- Service: `marketplace.services.purchase_listing`
- Response serializer: `marketplace.serializers.PurchaseOrderSerializer`

Behavior:

- The view fetches the listing by id.
- The serializer validates request shape and positive quantity.
- The view calls `purchase_listing`.
- The view does not directly edit inventory, listings, or orders.
- On success, the endpoint returns the completed order with nested order lines and HTTP `201 Created`.
- On serializer validation failure, DRF returns `400 Bad Request`.
- On service validation failure, the endpoint returns `400 Bad Request` with a `detail` field.

Failure examples:

- Inactive listing.
- Purchase quantity above listing availability.
- Seller attempting to buy their own listing.

Current boundary:

- Users can buy through the backend API.
- Payment, shipping, notifications, and external checkout are still out of scope.

## Pricing

The pricing module stores historical prices for card variants and provides service functions for valuation logic.

Purpose:

- Keep a timeline of observed prices.
- Keep `CardVariant.current_value` as a fast current estimate.
- Estimate a user's collection value from owned quantity and current variant values.

### `pricing.models.PriceSnapshot`

Represents one observed price for one card variant at one point in time.

Important relationship:

- `card_variant` points to `CardVariant`

Important fields:

- `price`
- `currency`
- `source_name`
- `captured_at`
- `created_at`
- `updated_at`

Rules:

- `price` cannot be negative.
- `currency` defaults to `EUR`.
- Snapshots are ordered newest first by `captured_at`, then id.
- A card variant can have many snapshots over time.

Why snapshots are separate from `CardVariant.current_value`:

- `PriceSnapshot` keeps historical evidence.
- `CardVariant.current_value` stores the latest usable estimate for fast reads.
- The current value can be recalculated from the newest snapshot.

### Pricing Services

Pricing write and valuation logic lives in `pricing/services.py`.

`record_price_snapshot`

- Creates a new `PriceSnapshot`.
- Validates the snapshot before saving.
- Updates `CardVariant.current_value` by default.
- Can skip the current-value update for historical imports by passing `update_current_value=False`.

`update_current_value_from_latest_snapshot`

- Finds the newest snapshot for a card variant.
- Locks the variant row before updating it.
- Copies the newest snapshot price into `CardVariant.current_value`.
- Raises `ValidationError` if the variant has no snapshots.

`get_variant_price_history`

- Returns snapshots for one card variant newest first.
- Supports an optional positive `limit`.

`estimate_collection_value`

- Reads a user's `InventoryItem` rows.
- Sums `InventoryItem.quantity * InventoryItem.card_variant.current_value`.
- Uses total owned quantity, not only available quantity, because reserved items are still owned until sold.

Current boundary:

- Pricing model and services exist.
- Pricing API endpoints exist.
- External pricing imports do not exist yet.

## Pricing API

The pricing API exposes read-only price information and the authenticated user's collection valuation.

Routes:

- `GET /api/pricing/variants/<variant_id>/history/`
- `GET /api/pricing/my/collection-value/`

### `GET /api/pricing/variants/<variant_id>/history/`

Purpose:

- Return historical price snapshots for one card variant.

Authentication:

- Public read-only endpoint.
- Uses `AllowAny`.

Behavior:

- Looks up the `CardVariant` by id.
- Returns `404 Not Found` if the variant does not exist.
- Returns `PriceSnapshot` rows newest first.

Response item shape:

```json
{
  "id": 1,
  "card_variant": 10,
  "price": "125.50",
  "currency": "EUR",
  "source_name": "manual",
  "captured_at": "2026-04-20T13:35:00Z"
}
```

Implementation:

- View: `pricing.views.VariantPriceHistoryView`
- Serializer: `pricing.serializers.PriceSnapshotSerializer`
- Query service: `pricing.services.get_variant_price_history`

### `GET /api/pricing/my/collection-value/`

Purpose:

- Return the authenticated user's estimated collection value.

Authentication:

- Requires an authenticated user.
- Uses `IsAuthenticated`.

Behavior:

- Reads the authenticated user's inventory rows.
- Uses `pricing.services.estimate_collection_value`.
- Returns the total based on `quantity * card_variant.current_value`.
- Uses total owned quantity because reserved cards are still owned until sold.

Response shape:

```json
{
  "total_value": "251.00",
  "currency": "EUR"
}
```

Implementation:

- View: `pricing.views.MyCollectionValueView`
- Serializer: `pricing.serializers.CollectionValueSerializer`
- Valuation service: `pricing.services.estimate_collection_value`

Current boundary:

- Pricing API is read-only.
- There is no API endpoint yet for creating price snapshots.
- Snapshot creation remains service/admin/internal-code driven for now.

## Testing Strategy

The backend test suite is organized around behavior boundaries instead of only file coverage.

Test layers:

- Model tests verify database relationships, constraints, and model validation.
- Service tests verify business rules and state transitions.
- API tests verify HTTP routes, authentication, response shape, and permission boundaries.
- Integration-style tests verify multi-step flows where several services and models must stay consistent together.

Current test tools:

- Django `TestCase` for normal model and service tests.
- Django `TransactionTestCase` where database DDL behavior matters.
- DRF `APITestCase` for API endpoints.
- Django's test runner creates and destroys the test database.

High-risk behavior covered:

- Catalog uniqueness, variant/image relationships, dataset import behavior, paginated list responses, and read API filters.
- Inventory ownership, quantity constraints, reserved quantity, service mutations, history writing, and authenticated API isolation.
- Marketplace listing creation, listing state transitions, order constraints, purchase transaction behavior, order history reads, and buy endpoint behavior.
- Pricing snapshots, current value recalculation, price history ordering, and authenticated collection valuation.

Purchase-flow integration coverage:

- Creating a listing from owned inventory reserves stock.
- Buying through the API creates a completed order and updates listing/inventory state.
- Buying through the API writes seller `DECREASE` history and buyer `PURCHASE` history.
- Buying more than listing availability returns `400 Bad Request`.
- Failed over-quantity API purchase does not create an order, does not mutate listing availability, does not mutate seller stock, and does not create buyer inventory.

Current boundary:

- Core backend MVP behavior is covered by model, service, API, and integration-style tests.
- Concurrency behavior is guarded by row locks in services but is not stress-tested with parallel transactions.
- Production deployment behavior is not covered yet.

## Admin Inspectability

Django admin is used as an inspection and debugging tool for backend development.

Current admin goals:

- Make foreign-key-heavy models easier to search.
- Avoid unnecessary database queries in admin list pages.
- Keep audit-like records difficult to mutate accidentally.
- Preserve timestamps as read-only inspection data.

Implemented admin conventions:

- FK-heavy admin pages use `list_select_related` for common relationship paths.
- FK-heavy forms use `autocomplete_fields` where the related admin has useful search fields.
- Timestamp fields inherited from `TimeStampedModel` are read-only in admin.
- `InventoryHistory` cannot be manually added or deleted through admin.
- `PurchaseOrderLine` cannot be manually added or deleted through direct admin.
- `PurchaseOrderLine` is shown read-only inside `PurchaseOrder` admin.

Current boundary:

- Admin configuration exists for catalog, inventory, marketplace, and pricing.
- Admin is for inspection and controlled manual review, not for replacing service-layer workflows.
- Seed/demo data is intentionally deferred until the real dataset strategy is designed.
