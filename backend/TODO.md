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
- [ ] Confirm the backend stack:
  - Django
  - Django REST Framework
  - MySQL
  - Django built-in auth
- [ ] Confirm the backend apps:
  - `users`
  - `catalog`
  - `inventory`
  - `marketplace`
  - `pricing`
  - `similarity` as optional later phase
- [ ] Confirm the MVP boundary:
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
- [ ] Create a shared base model or common mixin for timestamps
- [ ] Decide where enums will live
- [ ] Decide where services will live inside each app
- [ ] Decide where serializers will live
- [ ] Decide URL organization:
  - per-app routes
  - root API router
- [ ] Decide error handling style for API responses
- [ ] Decide whether to use custom permissions now or later
- [ ] Enable Django admin and prepare it for catalog data inspection

Verification:
- [ ] Shared model conventions are in place
- [ ] API layout is consistent before feature work begins

## Phase 3: Users Module

Goal:
- Have authenticated users with a profile layer

What you should learn:
- Django auth basics
- When to extend auth with a profile instead of replacing the user model

Steps:
- [ ] Decide whether to use default Django `User` plus `user_profile`
- [ ] Create the `users` app
- [ ] Create the `user_profile` model
- [ ] Add fields:
  - display name
  - bio
  - country
  - avatar URL
- [ ] Register user-related models in Django admin
- [ ] Decide authentication approach for the API:
  - session auth for early development
  - token or JWT later if needed
- [ ] Add a basic authenticated endpoint to confirm user access works

Verification:
- [ ] Can create users from admin
- [ ] Can create and view profiles
- [ ] Authenticated endpoint rejects anonymous access and accepts logged-in users

## Phase 4: Catalog Data Model

Goal:
- Build the official card catalog schema first

What you should learn:
- Relational modeling
- Foreign keys, normalization, and indexing
- Why catalog data must exist before inventory or listings

Steps:
- [ ] Create the `catalog` app
- [ ] Create the `card_game` model
- [ ] Create the `card_set` model
- [ ] Create the `card` model
- [ ] Create the `card_variant` model
- [ ] Create the `card_image` model
- [ ] Add field constraints and validation rules
- [ ] Add indexes for search and filtering
- [ ] Create and run migrations
- [ ] Register catalog models in admin
- [ ] Seed a small but coherent sample catalog dataset

Substeps for model review:
- [ ] Confirm each relationship direction is correct
- [ ] Confirm nullable fields are justified
- [ ] Confirm uniqueness rules where needed:
  - set code
  - collector number within the right scope
  - one primary image rule if enforced

Verification:
- [ ] Catalog migrations apply cleanly
- [ ] Admin can browse games, sets, cards, variants, and images
- [ ] Seeded data produces valid relations

## Phase 5: Catalog Read API

Goal:
- Expose catalog data through clean read-only endpoints

What you should learn:
- Serializers
- Query filtering
- Why read APIs should be stable and explicit

Steps:
- [ ] Add serializers for catalog models
- [ ] Add list endpoint for cards
- [ ] Add detail endpoint for a card
- [ ] Add detail endpoint for a variant
- [ ] Add list endpoint for sets
- [ ] Add filtering for:
  - name
  - game
  - set
  - rarity
- [ ] Add ordering where useful
- [ ] Avoid N+1 query problems with `select_related` and `prefetch_related`

Verification:
- [ ] Endpoints return correct JSON shape
- [ ] Filters behave correctly
- [ ] Query count stays reasonable for common requests

## Phase 6: Inventory Data Model

Goal:
- Represent what each user owns

What you should learn:
- Ownership modeling
- State constraints
- Why inventory history matters in transactional systems

Steps:
- [ ] Create the `inventory` app
- [ ] Create the `inventory_item` model
- [ ] Create the `inventory_history` model
- [ ] Add inventory fields:
  - owner
  - card variant
  - condition
  - quantity
  - reserved quantity
  - is for sale
  - acquired at
  - purchase price
- [ ] Define hard rules:
  - quantity must be greater than 0
  - reserved quantity cannot be negative
  - reserved quantity cannot exceed quantity
- [ ] Decide whether the same owner can have multiple rows for the same variant and condition
- [ ] Add indexes for owner and variant lookups
- [ ] Register models in admin

Verification:
- [ ] Invalid inventory states are blocked
- [ ] Inventory rows can be created and inspected cleanly

## Phase 7: Inventory Services

Goal:
- Put stock logic into services instead of views

What you should learn:
- Service-layer design
- Why state changes should have one trusted entry point

Steps:
- [ ] Create inventory service functions for:
  - add inventory item
  - increase quantity
  - decrease quantity
  - reserve quantity
  - release reserved quantity
  - merge purchased items into buyer inventory
- [ ] Make each service write `inventory_history`
- [ ] Decide what each history `change_type` means
- [ ] Make services validate business rules before saving
- [ ] Keep services reusable by both API endpoints and future admin actions

Verification:
- [ ] Service tests cover normal updates
- [ ] Service tests cover invalid updates
- [ ] History rows are written consistently

## Phase 8: Inventory API

Goal:
- Let users manage their own inventory through the API

What you should learn:
- Auth-scoped endpoints
- Validation at the serializer and service layers

Steps:
- [ ] Add endpoint to list the logged-in user inventory
- [ ] Add endpoint to create inventory entries
- [ ] Add endpoint to update inventory entries
- [ ] Add endpoint to remove or reduce inventory safely
- [ ] Ensure users cannot access or mutate another user inventory
- [ ] Ensure endpoints call services instead of mutating models directly

Verification:
- [ ] Authenticated user can manage only their own inventory
- [ ] Invalid requests return explicit errors
- [ ] Inventory changes produce history records

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
- [ ] Phase 1
- [ ] Phase 2
- [ ] Phase 3
- [ ] Phase 4
- [ ] Phase 5
- [ ] Phase 6
- [ ] Phase 7
- [ ] Phase 8
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
- [ ] Add shared backend conventions
- [x] Run the initial migrations

## Done Definition For The MVP

The backend MVP is done when all of the following are true:
- [ ] Users can authenticate
- [ ] Catalog data exists and is queryable
- [ ] Users can manage inventory
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
