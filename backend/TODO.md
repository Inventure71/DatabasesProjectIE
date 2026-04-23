# Backend TODO

This file is the step-by-step plan for building the backend together.

Scope:
- Backend domain apps own data, business rules, persistence, and real APIs
- Frontend lives as a sibling Django app at `frontend/`
- Frontend pages use `frontend/services/`; mock JSON APIs were removed after real backend-backed services became canonical
- Real backend APIs live under `/api/`
- Primary stack: Django + Django REST Framework + PostgreSQL

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
  - PostgreSQL
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
- [x] Define the key invariant for stock:
  - A listing can only sell cards the seller actually owns
  - Stock updates must happen inside a transaction
  - Reserved quantity rules must be explicit

Exit criteria:
- We agree on module boundaries and MVP scope

Current status:
- [x] Confirmed backend stack and implemented project foundation with Django, Django REST Framework, PostgreSQL, and Django built-in auth
- [x] Confirmed backend app boundaries: `common`, `users`, `catalog`, `inventory`, `marketplace`, and `pricing`
- [x] Confirmed similarity is optional later work and not part of the first transactional marketplace slice
- [x] Inventory uses an aggregate stock rule: one row per owner, card variant, and condition; duplicate additions increase quantity on that row.
- [x] Listing creation reserves quantity from aggregate inventory, and purchase/cancel flows update reserved stock transactionally.

## Phase 1: Backend Foundation

Goal:
- Create the backend project and make it runnable locally

What you should learn:
- Django project structure
- Environment-based configuration
- How Django connects to PostgreSQL

Steps:
- [x] Create the backend Django project structure
- [x] Create a Python virtual environment or project dependency setup
- [x] Add core dependencies:
  - `django`
  - `djangorestframework`
  - `psycopg` or another PostgreSQL adapter we choose explicitly
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
  - PostgreSQL database
  - timezone
  - static defaults
  - REST framework defaults
- [x] Create local run instructions
- [x] Verify the Django server starts successfully
- [ ] Verify Django connects to the chosen PostgreSQL database successfully

Verification:
- [x] `python manage.py check` passes
- [ ] `python manage.py migrate` runs successfully against PostgreSQL
- [ ] Local server boots without PostgreSQL configuration errors

Current status:
- [x] Verified on 2026-04-20 that `python manage.py check` passes with no issues
- [x] Verified on 2026-04-23 that `python manage.py check` passes after switching settings to PostgreSQL.
- [x] Verified on 2026-04-23 that `python manage.py makemigrations --check --dry-run` reports no model changes after the PostgreSQL/Vercel config change; the command warned that no local PostgreSQL server was listening on `127.0.0.1:5432`.
- [ ] Verify `python manage.py migrate` against the final local or remote PostgreSQL database.
- [ ] Verify the full test suite against PostgreSQL after the database is available.
- [x] Updated Django runtime module paths on 2026-04-23 so Vercel can resolve the nested WSGI app as `backend.config.wsgi.application` instead of looking for root `config/wsgi.py`.
- [x] Verified on 2026-04-23 that `python manage.py migrate --check` exits successfully after the Vercel module-path fix.
- [ ] Full PostgreSQL test suite is currently blocked by the local database role lacking `CREATEDB`; Django reached PostgreSQL but failed with `permission denied to create database`.
- [x] Updated and verified static-file settings on 2026-04-23 to use Django 6 `STORAGES["staticfiles"]` with WhiteNoise compressed manifest storage instead of removed `STATICFILES_STORAGE`.
- [x] Added and verified Vercel production config guards on 2026-04-23 so deployments fail clearly if `DJANGO_DEBUG=True` or `DATABASE_URL` is missing.
- [x] Moved Django command entrypoint to repository-root `manage.py` so `backend/` and `frontend/` can be sibling folders
- [x] Verified on 2026-04-20 that root `python manage.py check` passes with no issues
- [x] Verified on 2026-04-20 that `python manage.py test common catalog users inventory marketplace pricing` runs 46 tests successfully
- [x] Verified on 2026-04-20 that the broader suite `python manage.py test common catalog users inventory marketplace pricing frontend --keepdb` runs 148 tests successfully after choosing the aggregate inventory model.
- [x] Verified that Django apps exist under `backend/`
- [x] Verified that `requirements.txt` includes Django, Django REST Framework, PostgreSQL client, WhiteNoise, and python-dotenv
- [ ] Update local `.env` to use PostgreSQL keys or `DATABASE_URL`.
- [x] Verified on 2026-04-20 that no migrations are pending with `python manage.py migrate --check`
- [x] Verified from user run output that the Django development server starts on `http://127.0.0.1:8000/`
- [x] Verified on 2026-04-20 that `backend/README.md` documents setup, database creation, checks, migrations, and local server startup
- [x] Updated setup docs on 2026-04-23 to explain the PostgreSQL role/user password, `cards_marketplace` database ownership, direct `psql` credential check, and local run/test commands.

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
- [x] Removed the old `seed_catalog` sample command so development data comes from the real dataset import path
- [x] Kept catalog tests independent from sample seed data by creating explicit test fixtures
- [x] Added `python manage.py import_pokemon_cards_dataset --all-source-sets` for a fuller dataset import path.
- [x] Documented that all-set mode infers unknown set codes and collector denominators from the CSV, while the default import keeps the curated Base/Jungle MVP scope.
- [x] Verified the current `pokemon-cards.csv` can be parsed for all-set mode: 13,139 rows, 147 source sets, and 0 unparseable id suffixes.
- [x] Optimized `import_pokemon_cards_dataset --all-source-sets` on 2026-04-23 to use batched set/card/variant/image upserts instead of per-row ORM `update_or_create` calls, making remote PostgreSQL imports practical.
- [x] Added a regression test proving the all-set importer uses bounded batched database writes for repeated card names.
- [x] Fixed duplicate import rows resolving to the same `CardVariant` so image bulk upsert creates or updates only one `CardImage` per variant, preserving one-to-one idempotency.
- [x] Verified on 2026-04-24 that `python manage.py test catalog --keepdb` passes after the duplicate-row image upsert fix.

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
- [x] Added page-number pagination for `GET /api/catalog/cards/`
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
  - quantity cannot be negative
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
- [x] Enforced non-negative quantity
- [x] Direct inventory creation services still require positive quantity
- [x] Inventory rows may reach zero quantity after marketplace sales so history and listing references remain intact
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
- [x] Created `inventory.0002_remove_inventoryitem_inventory_quantity_positive_and_more`
- [x] Updated inventory quantity constraint from `quantity > 0` to `quantity >= 0` for marketplace purchases

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
- [x] Create the `marketplace` app
- [x] Create the `market_listing` model
- [x] Create the `purchase_order` model
- [x] Create the `purchase_order_line` model
- [x] Add marketplace foreign keys:
  - `MarketListing.seller_id` references the Django user table
  - `MarketListing.inventory_item_id` references `InventoryItem.id`
  - `PurchaseOrder.buyer_id` references the Django user table
  - `PurchaseOrder.seller_id` references the Django user table
  - `PurchaseOrderLine.purchase_order_id` references `PurchaseOrder.id`
  - `PurchaseOrderLine.listing_id` references `MarketListing.id`
  - `PurchaseOrderLine.card_variant_id` references `CardVariant.id`
- [x] Define listing statuses:
  - ACTIVE
  - PAUSED
  - SOLD_OUT
  - CANCELLED
- [x] Define order statuses:
  - PENDING
  - COMPLETED
  - CANCELLED
  - FAILED
- [x] Add indexes for seller, status, and price lookups
- [x] Decide whether a listing references one inventory row directly
- [x] Decide whether listing quantity is independent from inventory quantity or derived from it

Verification:
- [x] Marketplace schema reflects the intended workflow without ambiguity
- [x] Status fields and indexes support the planned queries
- [x] Listings reference owned stock through `InventoryItem`, not generic catalog rows
- [x] Order lines snapshot `CardVariant`, quantity, and price for stable transaction history

Current status:
- [x] Implemented `MarketListing`
- [x] Implemented `PurchaseOrder`
- [x] Implemented `PurchaseOrderLine`
- [x] `MarketListing.seller` references the Django user table
- [x] `MarketListing.inventory_item` references `InventoryItem`
- [x] `PurchaseOrder.buyer` references the Django user table
- [x] `PurchaseOrder.seller` references the Django user table
- [x] `PurchaseOrderLine.purchase_order` references `PurchaseOrder`
- [x] `PurchaseOrderLine.listing` references `MarketListing`
- [x] `PurchaseOrderLine.card_variant` references `CardVariant`
- [x] Listings store `quantity` and `quantity_available`
- [x] Listing quantity is stored on the listing, but future listing services must keep it consistent with inventory reservation rules
- [x] Listing model validation rejects inventory owned by a different seller
- [x] Listing model validation rejects zero quantity, over-available quantity, negative price, and sold-out rows with available quantity
- [x] Order model validation rejects negative totals and buyer=seller orders
- [x] Order line model validation rejects invalid quantity, invalid price, mismatched card variant, and listings from the wrong seller
- [x] Registered marketplace models in Django admin
- [x] Created `marketplace.0001_initial`
- [x] Verified on 2026-04-20 that marketplace tests first failed because marketplace models did not exist
- [x] Verified on 2026-04-20 that `python manage.py test marketplace` passes after adding marketplace models

## Phase 10: Listing Services

Goal:
- Safely create and manage listings from owned inventory

What you should learn:
- Precondition checks
- Why listing creation must validate ownership and available stock

Steps:
- [x] Create service to create a listing
- [x] Validate:
  - seller owns the inventory item
  - listing quantity is positive
  - enough unreserved quantity exists
- [x] Decide what happens to stock when listing is created:
  - reserve immediately
- [x] Create service to pause a listing
- [x] Create service to cancel a listing
- [x] Create service to mark a listing sold out
- [x] Ensure state transitions are explicit and not scattered across views

Verification:
- [x] Cannot list cards not owned by the seller
- [x] Cannot list more than available stock
- [x] Pause and cancel transitions behave predictably

Current status:
- [x] Implemented `create_listing`
- [x] Implemented `pause_listing`
- [x] Implemented `cancel_listing`
- [x] Implemented `mark_listing_sold_out`
- [x] `create_listing` locks the inventory row inside a transaction
- [x] `create_listing` rejects inventory owned by another user
- [x] `create_listing` rejects quantity above `InventoryItem.available_quantity`
- [x] `create_listing` reserves inventory immediately through `inventory.services.reserve_quantity`
- [x] `pause_listing` allows only active listings to become paused
- [x] `cancel_listing` allows active or paused listings to become cancelled
- [x] `cancel_listing` releases remaining available reserved quantity through `inventory.services.release_reserved_quantity`
- [x] `mark_listing_sold_out` requires `quantity_available=0`
- [x] Listing transition services reject the wrong seller
- [x] Verified on 2026-04-20 that marketplace service tests first failed because listing service functions did not exist
- [x] Verified on 2026-04-20 that `python manage.py test marketplace` passes after adding listing services

## Phase 11: Marketplace Read API

Goal:
- Let users browse listings and their order history

What you should learn:
- Public vs private API boundaries
- Efficient listing queries

Steps:
- [x] Add endpoint to browse active listings
- [x] Add endpoint to view listing details
- [x] Add endpoint for the seller own sales history
- [x] Add endpoint for the buyer own order history
- [x] Add filtering for:
  - seller
  - card variant
  - status
  - price range
- [x] Optimize common marketplace queries

Verification:
- [x] Public listing endpoints expose only intended data
- [x] Private history endpoints are properly scoped to the logged-in user

Current status:
- [x] Implemented `GET /api/marketplace/listings/`
- [x] Implemented `GET /api/marketplace/listings/<id>/`
- [x] Implemented `GET /api/marketplace/my/sales/`
- [x] Implemented `GET /api/marketplace/my/purchases/`
- [x] Public listing endpoints expose only active listings with `quantity_available > 0`
- [x] Listing detail returns `404 Not Found` for paused, cancelled, sold-out, or unavailable listings
- [x] Listing list supports filters for seller id, card variant id, active status, minimum price, and maximum price
- [x] Private sales history is scoped to `seller=request.user`
- [x] Private purchase history is scoped to `buyer=request.user`
- [x] Marketplace read serializers return seller/buyer summaries, nested card variant data, listing data, order data, and order lines
- [x] Marketplace read views use `select_related` and `prefetch_related` for common listing and order history queries
- [x] Verified on 2026-04-20 that marketplace API tests first failed because marketplace route names did not exist
- [x] Verified on 2026-04-20 that `python manage.py test marketplace` passes after adding marketplace read API

## Phase 12: Purchase Transaction Workflow

Goal:
- Implement the core buy flow safely and correctly

What you should learn:
- Database transactions
- Row locking
- Why concurrency bugs are the real backend difficulty here

Steps:
- [x] Design the purchase service before coding it
- [x] Write the purchase workflow in exact order:
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
- [x] Define failure behavior clearly:
  - insufficient stock
  - inactive listing
  - seller buying own listing if disallowed
  - database error
- [x] Keep the whole state transition in a service function
- [x] Ensure rollback happens automatically on failure

Verification:
- [x] Successful purchase updates seller inventory correctly
- [x] Successful purchase creates buyer inventory correctly
- [x] Successful purchase creates order and order line records
- [x] Failed purchase leaves data unchanged

Current status:
- [x] Implemented `purchase_listing`
- [x] `purchase_listing` validates positive purchase quantity
- [x] `purchase_listing` locks the listing row
- [x] `purchase_listing` locks the seller inventory row
- [x] `purchase_listing` rejects inactive listings
- [x] `purchase_listing` rejects purchases above `quantity_available`
- [x] `purchase_listing` rejects sellers buying their own listings
- [x] `purchase_listing` creates a completed `PurchaseOrder`
- [x] `purchase_listing` creates a `PurchaseOrderLine` snapshot with listing, variant, quantity, and unit price
- [x] `purchase_listing` decreases seller `quantity` and `reserved_quantity`
- [x] `purchase_listing` creates or merges buyer inventory with `merge_purchased_item`
- [x] `purchase_listing` writes seller `DECREASE` history and buyer `PURCHASE` history
- [x] `purchase_listing` decreases listing `quantity_available`
- [x] `purchase_listing` marks listings `SOLD_OUT` when `quantity_available` reaches zero
- [x] `purchase_listing` records a `marketplace_sale` `PriceSnapshot` for completed sales and refreshes the variant current value from that sale
- [x] Failed purchase validations happen inside one transaction and leave order, listing, and inventory state unchanged
- [x] Verified on 2026-04-20 that purchase workflow tests first failed because `purchase_listing` did not exist
- [x] Verified on 2026-04-20 that targeted inventory and marketplace purchase tests pass after adding purchase workflow
- [x] Verified on 2026-04-20 that purchase workflow tests first failed because completed purchases did not create price snapshots, then passed after wiring marketplace purchases into pricing snapshots

## Phase 13: Buy Endpoint

Goal:
- Expose the purchase workflow through one safe API entry point

What you should learn:
- Why thin views matter
- How request validation should feed a service layer

Steps:
- [x] Add buy endpoint for a listing
- [x] Validate request payload
- [x] Call the purchase service
- [x] Return clear success and error responses
- [x] Prevent direct model mutation from the view

Verification:
- [x] Endpoint succeeds on valid purchases
- [x] Endpoint fails cleanly on invalid purchases
- [x] Responses are consistent and understandable

Current status:
- [x] Implemented `POST /api/marketplace/listings/<id>/buy/`
- [x] Buy endpoint requires authentication
- [x] Buy endpoint validates `quantity` with `BuyListingSerializer`
- [x] Buy endpoint calls `marketplace.services.purchase_listing`
- [x] Buy endpoint returns the created completed order with nested order lines
- [x] Buy endpoint returns serializer errors for invalid request shape
- [x] Buy endpoint returns `400 Bad Request` for service validation failures
- [x] Buy endpoint rejects anonymous purchases
- [x] Buy endpoint rejects inactive listing purchases
- [x] Buy endpoint rejects seller self-purchases
- [x] Verified on 2026-04-20 that buy endpoint tests first failed because the route did not exist
- [x] Verified on 2026-04-20 that `python manage.py test marketplace` passes after adding the buy endpoint
- [x] Verified on 2026-04-20 that full backend verification passes: `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py migrate --check`, and `python manage.py test common catalog users inventory marketplace pricing`

## Phase 14: Pricing Module

Goal:
- Track historical values and compute simple valuations

What you should learn:
- Historical data modeling
- Why current value and historical value serve different purposes

Steps:
- [x] Confirm the `pricing` app exists
- [x] Create the `price_snapshot` model
- [x] Define fields:
  - card variant
  - price
  - currency
  - source name
  - captured at
- [x] Create service to insert a price snapshot
- [x] Create service to update `card_variant.current_value` from recent price history
- [x] Create query logic to read price history for a variant
- [x] Create query logic to estimate a user collection total value

Verification:
- [x] New snapshots are stored correctly
- [x] Current value updates correctly
- [x] Price history query returns records in the correct order

Current status:
- [x] Implemented `pricing.models.PriceSnapshot`
- [x] `PriceSnapshot.card_variant_id` references `catalog.CardVariant.id`
- [x] `PriceSnapshot.price` is constrained to be non-negative
- [x] `PriceSnapshot.currency` defaults to `EUR`
- [x] `PriceSnapshot.source_name` records where the price came from
- [x] `PriceSnapshot.captured_at` records when the price was captured
- [x] Implemented `record_price_snapshot`
- [x] Implemented `update_current_value_from_latest_snapshot`
- [x] Implemented `get_variant_price_history`
- [x] Implemented `estimate_collection_value`
- [x] Marketplace purchases now create price snapshots with source `marketplace_sale`
- [x] `card_variant.current_value` now uses the average of the last 100 `marketplace_sale` prices when sale snapshots exist, with newest snapshot fallback only when there are no sale snapshots yet
- [x] Existing completed marketplace order lines are backfilled into `PriceSnapshot` by `pricing.0002_backfill_marketplace_sale_price_snapshots`
- [x] Existing variant current values are recalculated from recent marketplace sale snapshots by `pricing.0003_recalculate_current_value_from_recent_sales`
- [x] Registered `PriceSnapshot` in Django admin
- [x] Created `pricing.0001_initial`
- [x] Created `pricing.0002_backfill_marketplace_sale_price_snapshots`
- [x] Created `pricing.0003_recalculate_current_value_from_recent_sales`
- [x] Verified on 2026-04-20 that pricing tests first failed because `PriceSnapshot` did not exist
- [x] Verified on 2026-04-20 that `python manage.py check` and `python manage.py test pricing` pass after adding the pricing model and services
- [x] Verified on 2026-04-20 that full backend verification passes: `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py migrate --check`, and `python manage.py test common catalog users inventory marketplace pricing`

## Phase 15: Pricing API

Goal:
- Expose price history in a simple way

What you should learn:
- How to expose historical data without overcomplicating the API

Steps:
- [x] Add endpoint for variant price history
- [x] Decide whether collection valuation belongs in MVP or a later extension
- [x] If included, add authenticated collection valuation endpoint

Verification:
- [x] Price history endpoint works for representative catalog data
- [x] Collection valuation is correct if implemented

Current status:
- [x] Implemented `GET /api/pricing/variants/<variant_id>/history/`
- [x] Variant price history endpoint is public read-only data
- [x] Variant price history returns snapshots newest first
- [x] Variant price history is paginated with the same default page size as catalog cards
- [x] Variant price history returns `404 Not Found` for missing variants
- [x] Included collection valuation in the MVP because Phase 14 already has the service and users need a portfolio total
- [x] Implemented `GET /api/pricing/my/collection-value/`
- [x] Collection valuation endpoint requires authentication
- [x] Collection valuation returns the authenticated user's total current collection value
- [x] Verified on 2026-04-20 that pricing API tests first failed because pricing route names did not exist
- [x] Verified on 2026-04-20 that `python manage.py test pricing` passes after adding pricing API endpoints
- [x] Verified on 2026-04-20 that full backend verification passes: `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py migrate --check`, and `python manage.py test common catalog users inventory marketplace pricing`

## Phase 16: Testing Strategy

Goal:
- Prove the backend works instead of assuming it works

What you should learn:
- The difference between model tests, service tests, and API tests
- Why the purchase flow needs stronger testing than the rest

Steps:
- [x] Set up the test framework and test database strategy
- [x] Write model tests for:
  - catalog constraints
  - inventory constraints
  - listing status rules
- [x] Write service tests for:
  - inventory changes
  - listing creation
  - purchase flow
  - pricing updates
- [x] Write API tests for:
  - catalog reads
  - inventory endpoints
  - listings endpoints
  - buy endpoint
- [x] Add integration tests for:
  - create listing from owned inventory
  - successful purchase
  - failed purchase due to insufficient quantity
  - inventory history correctness

Verification:
- [x] Core business logic is covered by tests
- [x] Purchase flow has both success and failure coverage
- [x] Test suite passes consistently

Current status:
- [x] Test framework uses Django `TestCase`, `TransactionTestCase`, and DRF `APITestCase`
- [x] Test database is created and destroyed by Django test runner
- [x] Catalog model/API tests cover catalog constraints, variants, images, seed data, filters, and query count
- [x] Inventory model/service/API tests cover ownership, quantities, reservations, history, and user isolation
- [x] Marketplace model/service/API tests cover listing rules, order rules, listing reads, order history, and buy endpoint behavior
- [x] Pricing model/service/API tests cover snapshots, current value updates, history ordering, and collection valuation
- [x] Added buy endpoint integration coverage for successful purchase inventory history
- [x] Added buy endpoint integration coverage for failed over-quantity purchase with no side effects
- [x] Verified on 2026-04-20 that `python manage.py test marketplace.tests.BuyEndpointTests` passes with 7 tests
- [x] Verified on 2026-04-20 that full backend verification passes: `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py migrate --check`, and `python manage.py test common catalog users inventory marketplace pricing`

## Phase 17: Admin Improvements

Goal:
- Make the system easier to inspect through Django admin

What you should learn:
- Why admin tooling matters for backend development
- How admin configuration can make relational data easier to inspect safely

Steps:
- [x] Improve admin configuration for catalog, inventory, marketplace, and pricing models
- [x] Add admin tests for important inspection behavior
- [x] Keep audit-like records protected from accidental admin creation/deletion
- [x] Defer seed/demo data work until the real dataset strategy is designed

Verification:
- [x] Admin configuration passes Django system checks
- [x] Admin tests verify FK-heavy pages use `list_select_related` and autocomplete where useful
- [x] Admin tests verify inventory history and order-line records are read-only/audit-oriented in admin

Current status:
- [x] Catalog admin uses autocomplete and `list_select_related` for variant/image inspection
- [x] Inventory admin uses autocomplete and `list_select_related` for owner/card lookups
- [x] Inventory history admin is read-only for add/delete operations
- [x] Marketplace admin uses autocomplete and `list_select_related` for listings and orders
- [x] Purchase order lines are read-only in order admin and direct order-line admin
- [x] Pricing admin uses autocomplete and `list_select_related` for snapshot inspection
- [x] Verified on 2026-04-20 that admin tests first failed because optimized admin configuration was missing
- [x] Verified on 2026-04-20 that `python manage.py check` and targeted admin tests pass after admin improvements
- [x] Verified on 2026-04-20 that full backend verification passes: `python manage.py check`, `python manage.py makemigrations --check --dry-run`, `python manage.py migrate --check`, and `python manage.py test common catalog users inventory marketplace pricing`

## Future Dataset Work

Goal:
- Create real repeatable data once the dataset shape is decided

Deferred steps:
- [x] Create a repeatable dataset import command for the downloaded Pokemon cards CSV
- [x] Import available Base Set and Jungle Pokemon cards as ownable catalog variants
- [x] Avoid duplicate catalog rows when the import command is rerun
- [x] Clear old sample-only image metadata when imported rows are refreshed from the CSV
- [ ] Expand the dataset import later when we choose the source for missing Trainer/Energy cards
- [ ] Seed or import later:
  - users
  - cards
  - variants
  - inventory
  - listings
  - price snapshots

Deferred verification:
- [x] Fresh setup can load the partial Base Set and Jungle card dataset successfully
- [x] Running the partial Base Set and Jungle import twice does not duplicate imported rows
- [ ] Demo flows work on loaded dataset

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

## Frontend Integration Track

Goal:
- Let the frontend developer build pages in parallel without replacing backend structure.

Current status:
- [x] Imported the frontend Django app from `origin/Andres` without importing its separate `project/` backend layout
- [x] Registered `frontend` in `INSTALLED_APPS`
- [x] Mounted frontend pages at `/`
- [x] Kept real backend endpoints under `/api/`
- [x] Removed stale `/mock-api/` routes after catalog/listing pages moved to real backend-backed services
- [x] Removed stale frontend fake catalog/listing data
- [x] Added integration tests for root `manage.py`, `/`, and verifying `/mock-api/` is no longer mounted

Next steps:
- [x] Replace frontend catalog/listing service internals with real backend queries once the matching backend module is complete
- [x] Keep stale simulated JSON endpoints out of the running URL config
- [ ] Add frontend tests for each new page or real service contract the frontend depends on

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
- [x] Phase 9
- [x] Phase 10
- [x] Phase 11
- [x] Phase 12
- [x] Phase 13
- [x] Phase 14
- [x] Phase 15
- [x] Phase 16
- [x] Phase 17
- [ ] Phase 18 only if time remains

## What We Should Do First Together

Immediate next steps:
- [x] Decide exact backend dependency stack
- [x] Scaffold the backend project
- [x] Configure PostgreSQL and environment variables
- [x] Create the Django apps
- [x] Add shared settings
- [x] Add shared backend conventions
- [x] Run the initial migrations

## Done Definition For The MVP

The backend MVP is done when all of the following are true:
- [ ] Users can authenticate
- [ ] Catalog data exists and is queryable
- [x] Users can manage inventory
- [x] Sellers can create listings from owned cards
- [x] Buyers can buy listed cards safely
- [x] Inventory updates remain consistent after purchase
- [x] Orders are recorded
- [ ] Price history is stored and readable
- [ ] Core tests pass

## Important Non-Goals For Now

We are explicitly not prioritizing these right now:
- [ ] Payments
- [ ] Shipping
- [ ] Notifications
- [ ] Recommendation systems beyond optional similarity
- [ ] Complex analytics dashboards

## Backend Cleanup Audit

Recorded on 2026-04-20 after reviewing backend code for outdated code, leftovers, backward-compatibility migration paths, and unnecessary repetition.

- [x] Removed `InventoryItem.is_for_sale`; marketplace listing state now lives on `MarketListing.status` plus `quantity_available`.
- [ ] Remove generated `__pycache__/` directories from the backend working tree if they are not needed locally.
- [ ] Clean Django startapp boilerplate in empty scaffold files, especially `common.views` and the current placeholder `pricing` files.
- [ ] Decide whether `backend/PLAN.md` is still authoritative; it now conflicts with the implemented marketplace field names, routes, and MVP scope.
- [ ] Consider consolidating repeated compact card/set/user serializer shapes after inventory, marketplace, and pricing API shapes stabilize.
- [ ] Consider extracting repeated catalog/user/listing fixture builders in backend tests once the next backend phase adds more tests.
