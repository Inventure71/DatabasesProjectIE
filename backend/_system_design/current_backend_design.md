# Current Backend Design

This file documents how the backend is currently structured. It should be updated as verified backend pieces are added.

## Foundation

- Django project root: `backend/`
- Django settings module: `config.settings`
- Database: MySQL
- API framework: Django REST Framework
- Auth foundation: Django built-in auth
- Shared infrastructure app: `common`

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

Rule:

- Catalog tables describe official card data.
- Inventory references `CardVariant` because users own exact variants, not abstract cards.
- Listings reference `InventoryItem` because users can only sell stock they own.
- Order lines snapshot `CardVariant`, quantity, and price so transaction history stays readable even if listings change later.

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

### Catalog Seed Command

Command:

```bash
python manage.py seed_catalog
```

Purpose:

- Load a small coherent catalog dataset for development and demos.
- Prove the catalog relationships work with real rows.
- Make local setup easier before inventory and marketplace features exist.

Seeded data:

- 1 game: Pokemon
- 1 set: Base Set
- 2 cards: Charizard and Blastoise
- 3 variants:
  - Charizard Base Set 4/102 Holo English
  - Charizard Base Set 4/102 Holo Japanese
  - Blastoise Base Set 2/102 Holo English
- 3 images, one per variant

Important behavior:

- The command uses `update_or_create`, so running it multiple times updates the same rows instead of creating duplicates.
- The command is tested by `SeedCatalogCommandTests`.

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

- `CardListView` lists cards and supports filters.
- `CardDetailView` returns one card with its variants.
- `CardVariantDetailView` returns one exact card variant with its image.
- `CardSetListView` lists catalog sets.

### Filters

`GET /api/catalog/cards/` supports:

- `name`: partial case-insensitive card-name search.
- `game`: filters by `CardGame.slug`.
- `set`: filters by `CardSet.code`.
- `rarity`: filters by `CardVariant.rarity`.

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
- The card list endpoint is tested to use a fixed query count for seeded data.

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

- `quantity` must be greater than zero.
- `reserved_quantity` cannot be negative.
- `reserved_quantity` cannot be greater than `quantity`.
- `purchase_price` can be empty, but cannot be negative when present.
- One user cannot have duplicate rows for the same `card_variant` and `condition`.

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
