# Backend Implementation Plan

## 1. Project Scope

The backend will implement a **buy-and-sell trading card marketplace** using **Django + MySQL**.

This version removes card trading between users and focuses on:

* card catalog management
* card rarity and card value
* user collections / owned inventory
* listing cards for sale
* buying cards from other users
* historical price snapshots
* image-based similar card search using embeddings

The backend should be designed as a clean relational system with clear business rules and transactional safety.

---

## 2. Backend Goals

The backend must support five core capabilities:

1. maintain the card catalog
2. track what each user owns
3. let sellers list owned cards for sale
4. let buyers purchase listed cards safely
5. let users discover similar cards from image embeddings

---

## 3. Main Backend Modules

### 3.1 Users

Responsible for authentication and user profiles.

Deliverables:

* user model or Django auth integration
* profile table
* registration/login if needed
* seller and buyer identity support

### 3.2 Catalog

Responsible for the official card data.

Deliverables:

* card game table
* card set table
* card table
* card variant table
* rarity field
* current estimated value field
* catalog admin tools

### 3.3 Inventory

Responsible for what each user owns.

Deliverables:

* inventory item table
* quantity and condition management
* inventory history log
* mark items available for sale

### 3.4 Marketplace

Responsible for listings and purchases.

Deliverables:

* create listing
* browse listings
* listing status changes
* purchase workflow
* transaction-safe inventory updates
* purchase history

### 3.5 Pricing

Responsible for value tracking.

Deliverables:

* current value on card variant
* price snapshot history
* basic analytics queries

### 3.6 Similarity

Responsible for the embedding feature.

Deliverables:

* card image table
* embedding table
* offline embedding generation script
* similar cards endpoint
* optional similarity cache

---

## 4. Data Model Implementation Order

The backend should be implemented in this order.

### Phase 1. Foundation

Create the Django project, configure MySQL, create apps, and define shared base models.

Tasks:

* create Django project
* connect MySQL
* configure environments
* create apps: `users`, `catalog`, `inventory`, `marketplace`, `pricing`, `similarity`
* define timestamp mixin / shared abstract base model
* configure Django admin

### Phase 2. Core catalog schema

Implement the master data first.

Tables:

* `card_game`
* `card_set`
* `card`
* `card_variant`
* `card_image`

Tasks:

* define models
* define foreign keys and indexes
* enforce the catalog reference pattern: `CardVariant` connects one `Card` to one `CardSet`
* define rarity enum
* define current value field
* create migrations
* seed sample data
* expose admin pages

### Phase 3. User and inventory schema

After catalog exists, implement ownership.

Tables:

* `user_profile`
* `inventory_item`
* `inventory_history`

Tasks:

* define inventory rules
* reference owned cards through `inventory_item.card_variant_id`
* enforce quantity > 0
* expose add/update/remove inventory actions
* write service methods for stock changes

### Phase 4. Marketplace schema

Implement selling and buying.

Tables:

* `market_listing`
* `purchase_order`
* `purchase_order_line`

Tasks:

* make listings reference owned stock through `market_listing.inventory_item_id`
* listing creation
* listing browse endpoint
* purchase service
* order history endpoint
* status transitions

### Phase 5. Pricing schema

Implement value tracking.

Tables:

* `price_snapshot`

Tasks:

* snapshot insertion flow
* query latest price per card variant
* support collection valuation queries

### Phase 6. Similarity schema

Implement the advanced feature.

Tables:

* `card_embedding`
* optional `card_similarity_cache`

Tasks:

* offline script to generate embeddings from images
* storage of embedding vectors
* similarity calculation service
* API endpoint for similar cards

---

## 5. Final Backend Schema

### 5.1 Catalog tables

#### `card_game`

Fields:

* id
* name
* slug
* description
* created_at
* updated_at

#### `card_set`

Fields:

* id
* game_id
* name
* code
* release_date
* description
* created_at
* updated_at

#### `card`

Fields:

* id
* game_id
* name
* card_type
* subtype
* description
* artist_name
* attack
* defense
* hp
* created_at
* updated_at

#### `card_variant`

Fields:

* id
* card_id
* set_id
* collector_number
* rarity
* finish
* language
* edition_label
* is_first_edition
* current_value
* created_at
* updated_at

#### `card_image`

Relationship:

* `card_variant_id` is a one-to-one reference to `card_variant.id`
* each card variant can have at most one image

Fields:

* id
* card_variant_id
* image_url
* image_hash
* width
* height
* created_at
* updated_at

### 5.2 User tables

#### `user_profile`

Fields:

* id
* user_id
* display_name
* bio
* country
* avatar_url
* created_at
* updated_at

### 5.3 Inventory tables

#### `inventory_item`

Fields:

* id
* owner_id
* card_variant_id
* condition
* quantity
* reserved_quantity
* is_for_sale
* acquired_at
* purchase_price
* created_at
* updated_at

#### `inventory_history`

Fields:

* id
* inventory_item_id
* change_type
* quantity_delta
* created_by_id
* note
* created_at

Later marketplace migration:

* add nullable `related_listing_id` after `market_listing` exists
* add nullable `related_order_id` after `purchase_order` exists

### 5.4 Marketplace tables

#### `market_listing`

Fields:

* id
* seller_id
* inventory_item_id
* quantity
* price_per_unit
* currency
* status
* created_at
* updated_at
* closed_at

Suggested status values:

* ACTIVE
* PAUSED
* SOLD_OUT
* CANCELLED

#### `purchase_order`

Fields:

* id
* buyer_id
* seller_id
* status
* total_price
* currency
* created_at
* updated_at
* completed_at

Suggested status values:

* PENDING
* COMPLETED
* CANCELLED
* FAILED

#### `purchase_order_line`

Fields:

* id
* purchase_order_id
* listing_id
* card_variant_id
* quantity
* unit_price
* line_total
* created_at

### 5.5 Cross-table reference map

The backend must reference cards with foreign keys. Do not copy card names, set names, or variant labels into inventory or marketplace tables as the source of truth.

Catalog references:

* `card_set.game_id` -> `card_game.id`
* `card.game_id` -> `card_game.id`
* `card_variant.card_id` -> `card.id`
* `card_variant.set_id` -> `card_set.id`
* `card_image.card_variant_id` -> `card_variant.id`, one-to-one

Ownership references:

* `inventory_item.owner_id` -> Django user table
* `inventory_item.card_variant_id` -> `card_variant.id`
* `inventory_history.inventory_item_id` -> `inventory_item.id`
* `inventory_history.created_by_id` -> Django user table

Later marketplace references:

* `inventory_history.related_listing_id` -> `market_listing.id`, nullable
* `inventory_history.related_order_id` -> `purchase_order.id`, nullable

Marketplace references:

* `market_listing.seller_id` -> Django user table
* `market_listing.inventory_item_id` -> `inventory_item.id`
* `purchase_order.buyer_id` -> Django user table
* `purchase_order.seller_id` -> Django user table
* `purchase_order_line.purchase_order_id` -> `purchase_order.id`
* `purchase_order_line.listing_id` -> `market_listing.id`
* `purchase_order_line.card_variant_id` -> `card_variant.id`

Design rule:

* `Card` stores the abstract card identity and stable card text / stats.
* `CardVariant` stores the exact catalog version: set, collector number, rarity, finish, language, edition, and current value.
* `InventoryItem` stores user-owned stock of a `CardVariant`.
* `MarketListing` stores a sale offer for a specific `InventoryItem`.
* `PurchaseOrderLine` snapshots the bought `CardVariant`, quantity, and price so order history stays accurate even if the listing later changes.

### 5.6 Pricing tables

#### `price_snapshot`

Fields:

* id
* card_variant_id
* price
* currency
* source_name
* captured_at
* created_at

### 5.7 Similarity tables

#### `card_embedding`

Fields:

* id
* card_image_id
* model_name
* embedding_json
* embedding_dimension
* created_at
* updated_at

#### `card_similarity_cache` (optional)

Fields:

* id
* source_card_variant_id
* similar_card_variant_id
* score
* created_at

---

## 6. Business Logic Services

The backend should not place all logic in views. Core workflows should be implemented in service functions.

Required services:

### 6.1 Catalog services

* search cards
* filter variants
* get card details
* get variant details

### 6.2 Inventory services

* add inventory item
* increase quantity
* decrease quantity
* reserve quantity
* release reserved quantity
* move purchased item to buyer inventory

### 6.3 Marketplace services

* create listing
* pause listing
* cancel listing
* purchase listing
* complete order

### 6.4 Pricing services

* create snapshot
* update current value from latest snapshot
* calculate collection value

### 6.5 Similarity services

* generate embedding record
* compute cosine similarity
* fetch top similar cards
* cache similarity results

---

## 7. Required API / View Endpoints

These can be implemented as Django views or REST endpoints.

### Catalog

* `GET /cards/`
* `GET /cards/<id>/`
* `GET /variants/<id>/`
* `GET /sets/`

### Inventory

* `GET /my/inventory/`
* `POST /my/inventory/add/`
* `POST /my/inventory/<id>/update/`
* `POST /my/inventory/<id>/remove/`

### Marketplace

* `GET /listings/`
* `GET /listings/<id>/`
* `POST /listings/create/`
* `POST /listings/<id>/pause/`
* `POST /listings/<id>/cancel/`
* `POST /listings/<id>/buy/`
* `GET /my/orders/`
* `GET /my/sales/`

### Pricing

* `GET /variants/<id>/price-history/`

### Similarity

* `GET /variants/<id>/similar/`

---

## 8. Critical Transactional Workflow

## Buying a card

This is the most important backend workflow and must be transaction-safe.

Steps:

1. begin MySQL transaction
2. lock target listing row
3. lock seller inventory row
4. validate listing is active
5. validate requested quantity is available
6. create purchase order and order line
7. reduce seller inventory quantity
8. create or update buyer inventory item
9. write inventory history rows
10. mark listing as sold out or update remaining quantity
11. mark order as completed
12. commit

If any validation fails, rollback the transaction.

---

## 9. Indexing Plan

Must-have indexes:

* all foreign keys
* `card(name)`
* `card_variant(set_id, rarity)`
* `card_variant(current_value)`
* `inventory_item(owner_id, card_variant_id)`
* `inventory_item(owner_id, is_for_sale)`
* `market_listing(status, price_per_unit)`
* `market_listing(seller_id, status)`
* `price_snapshot(card_variant_id, captured_at)`

Optional:

* `card_similarity_cache(source_card_variant_id, score)`

---

## 10. Backend Testing Plan

### Unit tests

* model constraints
* service methods
* price calculations
* similarity scoring function

### Integration tests

* create listing from owned inventory
* buy listing successfully
* fail purchase when quantity unavailable
* inventory history written correctly
* similar card endpoint returns results

### Admin / data tests

* seed data loads correctly
* catalog relations are valid

---

## 11. Backend Milestone Plan

### Milestone 1

Project setup + MySQL + catalog schema

### Milestone 2

Inventory system complete

### Milestone 3

Marketplace listing and buying complete

### Milestone 4

Pricing history and analytics complete

### Milestone 5

Similarity feature complete

### Milestone 6

Testing, bug fixing, demo data, polish

---

## 12. Backend MVP Definition

The backend MVP is complete when it can:

* store cards, sets, variants, rarity, and value
* store user inventory
* create active sale listings
* allow another user to buy a listed card safely
* update inventories correctly
* show basic price history
* return visually similar cards using embeddings

---

## 13. Final Backend Positioning

The backend should be presented as a relational marketplace system built on MySQL, with a transaction-safe buy/sell workflow and a small modern similarity feature layered on top of structured catalog and inventory data.
