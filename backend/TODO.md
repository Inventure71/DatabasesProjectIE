# Backend TODO

This file is the step-by-step plan for building the backend together.

Scope:
- Backend only
- Frontend ignored completely for now
- Primary stack: Django + Django REST Framework + MySQL

Working principles:
- Finish one phase before starting the next
- Verify behavior before claiming a phase is done
- Keep business logic out of views
- Prefer small, focused apps and services
- Learn the reason behind each step, not just the syntax

## Phase 0: Project Framing

Goal:
- Lock the backend shape before writing application code

What you should learn:
- How to decompose a backend into bounded modules
- What belongs in models, services, serializers, and views

Steps:
- [x] Confirm the backend stack:
  - Django
  - Django REST Framework
  - MySQL
  - Django built-in auth
- [x] Confirm the backend apps:
  - `users`
  - `catalog`
  - `inventory`
  - `marketplace`
  - `pricing`
  - `similarity` as optional later phase
- [x] Confirm the MVP boundary:
  - Catalog management
  - User inventory
  - Listings
  - Buying flow
  - Price history
  - Exclude similarity from the first working MVP if time gets tight
- [ ] Define the key invariant for stock:
  - A listing can only sell cards the seller actually owns
  - Stock updates must happen inside a transaction
  - Reserved quantity rules must be explicit

Exit criteria:
- We agree on module boundaries and MVP scope

Current status:
- [x] Confirmed backend stack and implemented project foundation with Django, Django REST Framework, MySQL, and Django built-in auth
- [x] Confirmed backend app boundaries: `common`, `users`, `catalog`, `inventory`, `marketplace`, and `pricing`
- [x] Confirmed similarity is optional later work and not part of the first transactional marketplace slice
- [ ] Reserved quantity behavior still needs a precise rule before listing services are implemented

## Phase 1: Backend Foundation

Goal:
- Create the backend project and make it runnable locally

What you should learn:
- Django project structure
- Environment-based configuration
- How Django connects to MySQL

Steps:
- [x] Create the backend Django project structure
- [x] Create a Python virtual environment or project dependency setup
- [x] Add core dependencies:
  - `django`
  - `djangorestframework`
  - `mysqlclient` or another MySQL adapter we choose explicitly
  - optional dev tools later
- [x] Create `.env` file and strategy for:
  - database host
  - database port
  - database name
  - database user
  - database password
  - secret key
  - debug flag
- [x] Configure `settings.py` for:
  - installed apps
  - MySQL database
  - timezone
  - static defaults
  - REST framework defaults
- [x] Create local run instructions
- [x] Verify the Django server starts successfully
- [x] Verify Django connects to MySQL successfully

Verification:
- [x] `python manage.py check` passes
- [x] `python manage.py migrate` runs successfully
- [x] Local server boots without configuration errors

Current status:
- [x] Verified on 2026-04-20 that `python manage.py check` passes with no issues
- [x] Verified that Django apps exist under `backend/`
- [x] Verified that `requirements.txt` includes Django, Django REST Framework, MySQL client, and python-dotenv
- [x] Verified on 2026-04-20 that `.env` exists with the expected keys
- [x] Verified on 2026-04-20 that no migrations are pending with `python manage.py migrate --check`
- [x] Verified from user run output that the Django development server starts on `http://127.0.0.1:8000/`
- [x] Verified on 2026-04-20 that `backend/README.md` documents setup, database creation, checks, migrations, and local server startup

## Phase 2: Shared Backend Conventions

Goal:
- Set the rules that every app will follow

What you should learn:
- Why shared conventions reduce future chaos
- How to separate reusable infrastructure from domain logic

Steps:
- [x] Create a shared base model or common mixin for timestamps
- [x] Decide where enums will live
- [x] Decide where services will live inside each app
- [x] Decide where serializers will live
- [x] Decide URL organization:
  - per-app routes
  - root API router
- [x] Decide error handling style for API responses
- [x] Decide whether to use custom permissions now or later
- [x] Decide admin convention for model inspection

Verification:
- [x] Shared model conventions are in place
- [x] API layout is consistent before feature work begins

Current status:
- [x] Verified on 2026-04-20 that `common.models.TimeStampedModel` provides abstract `created_at` and `updated_at` fields
- [x] Verified on 2026-04-20 that `python manage.py test common` passes
- [x] Verified on 2026-04-20 that `python manage.py check` passes after adding `common`
- [x] Verified on 2026-04-20 that `python manage.py makemigrations --check --dry-run` reports no changes for the abstract base model
- [x] Agreed on 2026-04-20 that model-owned enums live in each app's `models.py` using Django `TextChoices`
- [x] Agreed on 2026-04-20 that business logic and state changes live in each app's `services.py`
- [x] Agreed on 2026-04-20 that API serializers live in each app's `serializers.py`
- [x] Agreed on 2026-04-20 that each app owns `urls.py` and `config/urls.py` includes app route modules
- [x] Agreed on 2026-04-20 that admin registration happens as models are created
- [x] Documented agreed backend rules in `backend/_system_design/backend_rules.md`
- [x] Created `serializers.py`, `services.py`, and `urls.py` convention files for domain apps on 2026-04-20
- [x] Wired root API route groups in `config/urls.py` on 2026-04-20
- [x] Agreed on 2026-04-20 to keep service error handling simple and translate service validation failures into DRF `400 Bad Request` responses for now
- [x] Agreed on 2026-04-20 to use DRF built-in permissions first and defer custom permissions until ownership rules require them
- [x] Verified on 2026-04-20 that `python manage.py check`, `python manage.py test common`, and `python manage.py makemigrations --check --dry-run` pass after URL skeleton setup

## Phase 3: Users Module

Goal:
- Have authenticated users with a profile layer

What you should learn:
- Django auth basics
- When to extend auth with a profile instead of replacing the user model

Steps:
- [x] Decide whether to use default Django `User` plus `user_profile`
- [x] Create the `users` app
- [x] Create the `user_profile` model
- [x] Add fields:
  - display name
  - bio
  - country
  - avatar URL
- [x] Register user-related models in Django admin
- [x] Decide authentication approach for the API:
  - session auth for early development
  - token or JWT later if needed
- [x] Add a basic authenticated endpoint to confirm user access works

Verification:
- [x] Can create users from admin
- [x] Can create and view profiles
- [x] Authenticated endpoint rejects anonymous access and accepts logged-in users

Current status:
- [x] Agreed to use Django built-in `User` plus `users.UserProfile`
- [x] Implemented `UserProfile` with `OneToOneField` to `settings.AUTH_USER_MODEL`
- [x] Implemented profile fields: `display_name`, `bio`, `country`, and `avatar_url`
- [x] `UserProfile` inherits `common.models.TimeStampedModel`
- [x] Registered `UserProfile` in Django admin
- [x] Created and applied `users.0001_initial`
- [x] Verified on 2026-04-20 that the initial `users` test failed before implementation because `UserProfile` did not exist
- [x] Verified on 2026-04-20 that `python manage.py test users` passes
- [x] Verified on 2026-04-20 that `python manage.py test common` passes
- [x] Verified on 2026-04-20 that `python manage.py check` passes
- [x] Verified on 2026-04-20 that `python manage.py makemigrations --check --dry-run` reports no changes
- [x] Implemented `GET /api/users/me/` using `CurrentUserView`
- [x] Implemented `UserProfileSerializer` and `CurrentUserSerializer`
- [x] Verified on 2026-04-20 that anonymous requests to `users-me` are rejected
- [x] Verified on 2026-04-20 that authenticated requests to `users-me` return user and profile data
- [x] Verified on 2026-04-20 that `python manage.py test users`, `python manage.py test common`, `python manage.py check`, and `python manage.py makemigrations --check --dry-run` pass after adding the endpoint
- [x] Verified on 2026-04-20 that Django admin has both built-in `User` and `UserProfile` registered

## Phase 4: Catalog Data Model

Goal:
- Build the official card catalog schema first

What you should learn:
- Relational modeling
- Foreign keys, normalization, and indexing
- Why catalog data must exist before inventory or listings

Steps:
- [x] Create the `catalog` app
- [x] Create the `card_game` model
- [x] Create the `card_set` model
- [x] Create the `card` model
- [x] Create the `card_variant` model
- [x] Create the `card_image` model
- [x] Add field constraints and validation rules
- [x] Add indexes for search and filtering
- [x] Create and run migrations
- [x] Register catalog models in admin
- [x] Seed a small but coherent sample catalog dataset

Substeps for model review:
- [x] Confirm each relationship direction is correct
- [x] Confirm catalog foreign keys:
  - `CardSet.game_id` references `CardGame.id`
  - `Card.game_id` references `CardGame.id`
  - `CardVariant.card_id` references `Card.id`
  - `CardVariant.set_id` references `CardSet.id`
  - `CardImage.card_variant_id` references `CardVariant.id`
- [x] Confirm nullable fields are justified
- [x] Confirm uniqueness rules where needed:
  - set code
  - collector number within the right scope
  - one image per card variant is enforced with `CardImage.card_variant` as `OneToOneField`
- [x] Confirm the conceptual split:
  - `Card` stores stable card identity, text, and stats
  - `CardVariant` stores set-specific, print-specific, language-specific, and market-specific data

Verification:
- [x] Catalog migrations apply cleanly
- [x] Admin can browse games, sets, cards, variants, and images
- [x] Seeded data produces valid relations

Current status:
- [x] Implemented catalog models: `CardGame`, `CardSet`, `Card`, `CardVariant`, and `CardImage`
- [x] Verified that the `catalog` app exists and is included in project structure
- [x] Implemented catalog foreign-key chain from game/set/card to variant and variant images
- [x] Implemented `CardVariant.Rarity` and `CardVariant.Finish` using Django `TextChoices`
- [x] Implemented indexes for card name, card game/name, variant set/rarity, and variant current value
- [x] Implemented uniqueness for set code per game and variant printing identity
- [x] Implemented non-negative `CardVariant.current_value` database constraint
- [x] Registered catalog models in Django admin
- [x] Created and applied `catalog.0001_initial`
- [x] Verified on 2026-04-20 that `python manage.py test catalog`, `python manage.py test users`, `python manage.py test common`, `python manage.py check`, and `python manage.py makemigrations --check --dry-run` pass
- [x] Verified on 2026-04-20 that `catalog.0001_initial` is applied in the development database
- [x] Verified on 2026-04-20 that all catalog models are registered in Django admin
- [x] Decided on 2026-04-20 that each `CardVariant` should have at most one `CardImage`
- [x] Enforced one `CardImage` per `CardVariant` with `OneToOneField`
- [x] Created and applied `catalog.0002_alter_cardimage_options_alter_cardimage_card_variant`
- [x] Removed redundant `CardImage.is_primary` field because only one image can exist per variant
- [x] Created and applied `catalog.0003_remove_cardimage_is_primary`
- [x] Verified on 2026-04-20 that creating a duplicate `CardImage` for the same `CardVariant` raises `IntegrityError`
- [x] Verified on 2026-04-20 that `python manage.py test catalog`, `python manage.py test users`, `python manage.py test common`, `python manage.py check`, `python manage.py makemigrations --check --dry-run`, and `python manage.py migrate --check` pass after enforcing the rule
- [x] Implemented repeatable `seed_catalog` management command
- [x] Seed command creates 1 game, 1 set, 2 cards, 3 variants, and 3 images
- [x] Verified on 2026-04-20 that running `python manage.py seed_catalog` twice does not duplicate catalog rows
- [x] Verified on 2026-04-20 that seeded variants reference the expected game, set, cards, and one-to-one images
- [x] Verified on 2026-04-20 that the development database has 1 game, 1 set, 2 cards, 3 variants, and 3 images after seeding

## Phase 5: Catalog Read API

Goal:
- Expose catalog data through clean read-only endpoints

What you should learn:
- Serializers
- Query filtering
- Why read APIs should be stable and explicit

Steps:
- [x] Add serializers for catalog models
- [x] Add list endpoint for cards
- [x] Add detail endpoint for a card
- [x] Add detail endpoint for a variant
- [x] Add list endpoint for sets
- [x] Add filtering for:
  - name
  - game
  - set
  - rarity
- [x] Add ordering where useful
- [x] Avoid N+1 query problems with `select_related` and `prefetch_related`

Verification:
- [x] Endpoints return correct JSON shape
- [x] Filters behave correctly
- [x] Query count stays reasonable for common requests

Current status:
- [x] Implemented catalog serializers for games, sets, cards, variants, and images
- [x] Implemented `GET /api/catalog/cards/`
- [x] Implemented `GET /api/catalog/cards/<id>/`
- [x] Implemented `GET /api/catalog/variants/<id>/`
- [x] Implemented `GET /api/catalog/sets/`
- [x] Implemented card filters for `name`, `game`, `set`, and `rarity`
- [x] Ordered card list by card name and set list by game/name
- [x] Used `select_related` and `prefetch_related` for catalog read queries
- [x] Verified on 2026-04-20 that new API tests first failed because catalog routes were missing
- [x] Verified on 2026-04-20 that `python manage.py test catalog`, `python manage.py test users`, `python manage.py test common`, `python manage.py check`, `python manage.py makemigrations --check --dry-run`, and `python manage.py migrate --check` pass after adding catalog read API

## Phase 6: Inventory Data Model

Goal:
- Represent what each user owns

What you should learn:
- Ownership modeling
- State constraints
- Why inventory history matters in transactional systems

Steps:
- [x] Create the `inventory` app
- [x] Create the `inventory_item` model
- [x] Create the `inventory_history` model
- [x] Add inventory foreign keys:
  - `InventoryItem.owner_id` references the Django user table
  - `InventoryItem.card_variant_id` references `CardVariant.id`
  - `InventoryHistory.inventory_item_id` references `InventoryItem.id`
  - `InventoryHistory.created_by_id` references the Django user table
- [x] Defer marketplace-related inventory history foreign keys until marketplace models exist:
  - `InventoryHistory.related_listing_id` should reference `MarketListing.id` after marketplace models exist
  - `InventoryHistory.related_order_id` should reference `PurchaseOrder.id` after marketplace models exist
- [x] Add inventory fields:
  - owner
  - card variant
  - condition
  - quantity
  - reserved quantity
  - is for sale
  - acquired at
  - purchase price
- [x] Define hard rules:
  - quantity must be greater than 0
  - reserved quantity cannot be negative
  - reserved quantity cannot exceed quantity
- [x] Decide whether the same owner can have multiple rows for the same variant and condition
- [x] Add indexes for owner and variant lookups
- [x] Register models in admin

Verification:
- [x] Invalid inventory states are blocked
- [x] Inventory rows can be created and inspected cleanly
- [x] Inventory references exact `CardVariant` rows, not abstract `Card` rows

Current status:
- [x] Implemented `InventoryItem`
- [x] Implemented `InventoryHistory`
- [x] `InventoryItem.owner` references the Django user table
- [x] `InventoryItem.card_variant` references `CardVariant`
- [x] `InventoryHistory.inventory_item` references `InventoryItem`
- [x] `InventoryHistory.created_by` references the Django user table and allows null when the actor is deleted
- [x] Enforced one row per owner, card variant, and condition
- [x] Enforced positive quantity
- [x] Enforced non-negative reserved quantity
- [x] Enforced reserved quantity not above total quantity
- [x] Enforced non-negative purchase price when purchase price is present
- [x] Added `available_quantity` property as `quantity - reserved_quantity`
- [x] Added indexes for owner/variant, owner/sale state, inventory history by item/date, and inventory history by actor/date
- [x] Registered `InventoryItem` and `InventoryHistory` in Django admin
- [x] Created and applied `inventory.0001_initial`
- [x] Verified on 2026-04-20 that inventory tests first failed because inventory models/tables did not exist
- [x] Verified on 2026-04-20 that `python manage.py test inventory`, `python manage.py test catalog`, `python manage.py test users`, `python manage.py test common`, `python manage.py check`, `python manage.py makemigrations --check --dry-run`, and `python manage.py migrate --check` pass
- [x] Verified on 2026-04-20 that `inventory.0001_initial` is applied
- [x] Verified on 2026-04-20 that inventory models are registered in Django admin

## Phase 7: Inventory Services

Goal:
- Put stock logic into services instead of views

What you should learn:
- Service-layer design
- Why state changes should have one trusted entry point

Steps:
- [x] Create inventory service functions for:
  - add inventory item
  - increase quantity
  - decrease quantity
  - reserve quantity
  - release reserved quantity
  - merge purchased items into buyer inventory
- [x] Make each service write `inventory_history`
- [x] Decide what each history `change_type` means
- [x] Make services validate business rules before saving
- [x] Keep services reusable by both API endpoints and future admin actions

Verification:
- [x] Service tests cover normal updates
- [x] Service tests cover invalid updates
- [x] History rows are written consistently

Current status:
- [x] Implemented `add_inventory_item`
- [x] Implemented `increase_quantity`
- [x] Implemented `decrease_quantity`
- [x] Implemented `reserve_quantity`
- [x] Implemented `release_reserved_quantity`
- [x] Implemented `merge_purchased_item`
- [x] Each service uses a database transaction
- [x] Services that modify existing inventory lock rows with `select_for_update`
- [x] Each successful service call writes an `InventoryHistory` row
- [x] Invalid service inputs raise `ValidationError`
- [x] Verified on 2026-04-20 that service tests first failed because inventory service functions did not exist
- [x] Verified on 2026-04-20 that `python manage.py test inventory`, `python manage.py test catalog`, `python manage.py test users`, `python manage.py test common`, `python manage.py check`, `python manage.py makemigrations --check --dry-run`, and `python manage.py migrate --check` pass after adding inventory services

## Phase 8: Inventory API

Goal:
- Let users manage their own inventory through the API

What you should learn:
- Auth-scoped endpoints
- Validation at the serializer and service layers

Steps:
- [x] Add endpoint to list the logged-in user inventory
- [x] Add endpoint to create inventory entries
- [x] Add endpoint to update inventory entries
- [x] Add endpoint to remove or reduce inventory safely
- [x] Ensure users cannot access or mutate another user inventory
- [x] Ensure endpoints call services instead of mutating models directly

Verification:
- [x] Authenticated user can manage only their own inventory
- [x] Invalid requests return explicit errors
- [x] Inventory changes produce history records

Current status:
- [x] Implemented `GET /api/inventory/my/`
- [x] Implemented `POST /api/inventory/my/add/`
- [x] Implemented `POST /api/inventory/my/<id>/update/`
- [x] Implemented `POST /api/inventory/my/<id>/remove/`
- [x] Added inventory serializers for list responses, add requests, update actions, and remove requests
- [x] Inventory API endpoints require authentication with DRF `IsAuthenticated`
- [x] Inventory API querysets are scoped to `owner=request.user`
- [x] Requests for another user's inventory row return `404 Not Found`
- [x] API views call inventory service functions instead of changing model fields directly
- [x] Update endpoint supports `INCREASE`, `DECREASE`, `RESERVE`, and `RELEASE`
- [x] Remove endpoint safely reduces available stock through `decrease_quantity`
- [x] Full row deletion is intentionally deferred because `InventoryHistory` currently belongs to `InventoryItem`
- [x] Verified on 2026-04-20 that inventory API tests first failed because routes were missing
- [x] Verified on 2026-04-20 that `python manage.py test inventory`, `python manage.py test catalog`, `python manage.py test users`, `python manage.py test common`, `python manage.py check`, `python manage.py makemigrations --check --dry-run`, and `python manage.py migrate --check` pass after adding inventory API

## Phase 9: Marketplace Data Model

Goal:
- Represent listings and purchase orders cleanly

What you should learn:
- Marketplace entity design
- Status modeling
- Why listing and order records must be separate from inventory rows

Steps:
- [ ] Create the `marketplace` app
- [ ] Create the `market_listing` model
- [ ] Create the `purchase_order` model
- [ ] Create the `purchase_order_line` model
- [ ] Add marketplace foreign keys:
  - `MarketListing.seller_id` references the Django user table
  - `MarketListing.inventory_item_id` references `InventoryItem.id`
  - `PurchaseOrder.buyer_id` references the Django user table
  - `PurchaseOrder.seller_id` references the Django user table
  - `PurchaseOrderLine.purchase_order_id` references `PurchaseOrder.id`
  - `PurchaseOrderLine.listing_id` references `MarketListing.id`
  - `PurchaseOrderLine.card_variant_id` references `CardVariant.id`
- [ ] Define listing statuses:
  - ACTIVE
  - PAUSED
  - SOLD_OUT
  - CANCELLED
- [ ] Define order statuses:
  - PENDING
  - COMPLETED
  - CANCELLED
  - FAILED
- [ ] Add indexes for seller, status, and price lookups
- [ ] Decide whether a listing references one inventory row directly
- [ ] Decide whether listing quantity is independent from inventory quantity or derived from it

Verification:
- [ ] Marketplace schema reflects the intended workflow without ambiguity
- [ ] Status fields and indexes support the planned queries
- [ ] Listings reference owned stock through `InventoryItem`, not generic catalog rows
- [ ] Order lines snapshot `CardVariant`, quantity, and price for stable transaction history

## Phase 10: Listing Services

Goal:
- Safely create and manage listings from owned inventory

What you should learn:
- Precondition checks
- Why listing creation must validate ownership and available stock

Steps:
- [ ] Create service to create a listing
- [ ] Validate:
  - seller owns the inventory item
  - listing quantity is positive
  - enough unreserved quantity exists
- [ ] Decide what happens to stock when listing is created:
  - reserve immediately
  - or reserve only during purchase
- [ ] Create service to pause a listing
- [ ] Create service to cancel a listing
- [ ] Create service to mark a listing sold out
- [ ] Ensure state transitions are explicit and not scattered across views

Verification:
- [ ] Cannot list cards not owned by the seller
- [ ] Cannot list more than available stock
- [ ] Pause and cancel transitions behave predictably

## Phase 11: Marketplace Read API

Goal:
- Let users browse listings and their order history

What you should learn:
- Public vs private API boundaries
- Efficient listing queries

Steps:
- [ ] Add endpoint to browse active listings
- [ ] Add endpoint to view listing details
- [ ] Add endpoint for the seller own sales history
- [ ] Add endpoint for the buyer own order history
- [ ] Add filtering for:
  - seller
  - card variant
  - status
  - price range
- [ ] Optimize common marketplace queries

Verification:
- [ ] Public listing endpoints expose only intended data
- [ ] Private history endpoints are properly scoped to the logged-in user

## Phase 12: Purchase Transaction Workflow

Goal:
- Implement the core buy flow safely and correctly

What you should learn:
- Database transactions
- Row locking
- Why concurrency bugs are the real backend difficulty here

Steps:
- [ ] Design the purchase service before coding it
- [ ] Write the purchase workflow in exact order:
  - begin transaction
  - lock listing row
  - lock seller inventory row
  - validate listing is active
  - validate requested quantity is available
  - create order
  - create order line
  - update seller inventory
  - create or update buyer inventory
  - write inventory history
  - update listing status or remaining quantity
  - mark order completed
  - commit
- [ ] Define failure behavior clearly:
  - insufficient stock
  - inactive listing
  - seller buying own listing if disallowed
  - database error
- [ ] Keep the whole state transition in a service function
- [ ] Ensure rollback happens automatically on failure

Verification:
- [ ] Successful purchase updates seller inventory correctly
- [ ] Successful purchase creates buyer inventory correctly
- [ ] Successful purchase creates order and order line records
- [ ] Failed purchase leaves data unchanged

## Phase 13: Buy Endpoint

Goal:
- Expose the purchase workflow through one safe API entry point

What you should learn:
- Why thin views matter
- How request validation should feed a service layer

Steps:
- [ ] Add buy endpoint for a listing
- [ ] Validate request payload
- [ ] Call the purchase service
- [ ] Return clear success and error responses
- [ ] Prevent direct model mutation from the view

Verification:
- [ ] Endpoint succeeds on valid purchases
- [ ] Endpoint fails cleanly on invalid purchases
- [ ] Responses are consistent and understandable

## Phase 14: Pricing Module

Goal:
- Track historical values and compute simple valuations

What you should learn:
- Historical data modeling
- Why current value and historical value serve different purposes

Steps:
- [ ] Create the `pricing` app
- [ ] Create the `price_snapshot` model
- [ ] Define fields:
  - card variant
  - price
  - currency
  - source name
  - captured at
- [ ] Create service to insert a price snapshot
- [ ] Create service to update `card_variant.current_value` from the newest snapshot
- [ ] Create query logic to read price history for a variant
- [ ] Create query logic to estimate a user collection total value

Verification:
- [ ] New snapshots are stored correctly
- [ ] Current value updates correctly
- [ ] Price history endpoint returns records in the correct order

## Phase 15: Pricing API

Goal:
- Expose price history in a simple way

What you should learn:
- How to expose historical data without overcomplicating the API

Steps:
- [ ] Add endpoint for variant price history
- [ ] Decide whether collection valuation belongs in MVP or a later extension
- [ ] If included, add authenticated collection valuation endpoint

Verification:
- [ ] Price history endpoint works for seeded data
- [ ] Collection valuation is correct if implemented

## Phase 16: Testing Strategy

Goal:
- Prove the backend works instead of assuming it works

What you should learn:
- The difference between model tests, service tests, and API tests
- Why the purchase flow needs stronger testing than the rest

Steps:
- [ ] Set up the test framework and test database strategy
- [ ] Write model tests for:
  - catalog constraints
  - inventory constraints
  - listing status rules
- [ ] Write service tests for:
  - inventory changes
  - listing creation
  - purchase flow
  - pricing updates
- [ ] Write API tests for:
  - catalog reads
  - inventory endpoints
  - listings endpoints
  - buy endpoint
- [ ] Add integration tests for:
  - create listing from owned inventory
  - successful purchase
  - failed purchase due to insufficient quantity
  - inventory history correctness

Verification:
- [ ] Core business logic is covered by tests
- [ ] Purchase flow has both success and failure coverage
- [ ] Test suite passes consistently

## Phase 17: Admin and Seed Data

Goal:
- Make the system demoable and inspectable

What you should learn:
- Why admin tooling matters for backend development
- Why seed data helps debugging and demos

Steps:
- [ ] Improve admin configuration for catalog, inventory, and marketplace models
- [ ] Create a repeatable seed command or fixture strategy
- [ ] Seed:
  - users
  - cards
  - variants
  - inventory
  - listings
  - price snapshots
- [ ] Verify seeded data makes the app usable immediately

Verification:
- [ ] Fresh setup can be seeded successfully
- [ ] Demo flows work on seeded data

## Phase 18: Optional Similarity Module

Goal:
- Add image-based similar-card search only after the core backend is stable

What you should learn:
- How to add an ML-adjacent feature without polluting core transactional logic

Steps:
- [ ] Create the `similarity` app
- [ ] Create the `card_embedding` model
- [ ] Optionally create `card_similarity_cache`
- [ ] Decide where embeddings are generated:
  - offline script
  - batch command
- [ ] Store embedding vectors in a simple format first
- [ ] Implement cosine similarity service
- [ ] Add endpoint for similar cards by variant
- [ ] Keep this feature isolated from marketplace transactions

Verification:
- [ ] Similarity endpoint returns plausible results
- [ ] Core backend still works unchanged

## Recommended Build Order

Strict order:
- [ ] Phase 0
- [x] Phase 1
- [x] Phase 2
- [x] Phase 3
- [x] Phase 4
- [x] Phase 5
- [x] Phase 6
- [x] Phase 7
- [x] Phase 8
- [ ] Phase 9
- [ ] Phase 10
- [ ] Phase 11
- [ ] Phase 12
- [ ] Phase 13
- [ ] Phase 14
- [ ] Phase 15
- [ ] Phase 16
- [ ] Phase 17
- [ ] Phase 18 only if time remains

## What We Should Do First Together

Immediate next steps:
- [x] Decide exact backend dependency stack
- [x] Scaffold the backend project
- [x] Configure MySQL and environment variables
- [x] Create the Django apps
- [x] Add shared settings
- [x] Add shared backend conventions
- [x] Run the initial migrations

## Done Definition For The MVP

The backend MVP is done when all of the following are true:
- [ ] Users can authenticate
- [ ] Catalog data exists and is queryable
- [x] Users can manage inventory
- [ ] Sellers can create listings from owned cards
- [ ] Buyers can buy listed cards safely
- [ ] Inventory updates remain consistent after purchase
- [ ] Orders are recorded
- [ ] Price history is stored and readable
- [ ] Core tests pass

## Important Non-Goals For Now

We are explicitly not prioritizing these right now:
- [ ] Frontend integration
- [ ] Payments
- [ ] Shipping
- [ ] Notifications
- [ ] Recommendation systems beyond optional similarity
- [ ] Complex analytics dashboards
