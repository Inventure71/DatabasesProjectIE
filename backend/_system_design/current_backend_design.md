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
- `CardImage.card_variant_id` points to `CardVariant.id`.
- `InventoryItem.owner_id` points to the Django user table.
- `InventoryItem.card_variant_id` points to `CardVariant.id`.
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
