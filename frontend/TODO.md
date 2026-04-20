# Frontend TODO

This file tracks frontend work now that `frontend/` is a sibling Django app.

## Current Status

- [x] Frontend app imported from `origin/Andres`
- [x] Frontend pages mounted at `/`
- [x] Fake catalog and listing data moved into `frontend/services/`
- [x] Mock JSON endpoints mounted under `/mock-api/`
- [x] Real backend APIs remain reserved under `/api/`

## Working Rules

- Keep templates and static assets in `frontend/`.
- Use `frontend/services/` as the boundary between pages and data.
- Use `/mock-api/...` only for simulated frontend JSON.
- Do not create fake endpoints under `/api/...`; that namespace belongs to the real backend.
- Replace mock service internals with real backend data one feature at a time.

## Next Steps

- [ ] Replace mock catalog/listing services with real backend-backed data contracts.
- [ ] Add frontend pages and service functions for authenticated inventory management.
- [ ] Add a real listing detail page and connect the buy flow to the backend purchase endpoint.
- [ ] Add purchase history and sales history pages for authenticated users.
- [ ] Add authenticated user/profile display using the backend current-user endpoint.
- [ ] Remove or clearly isolate mock-only price history and similar-card UI until backend support exists.
- [ ] Add service functions for inventory pages before building those templates.
- [ ] Add mock API endpoints only when frontend JavaScript needs JSON.
- [ ] Add tests for every frontend page or mock API contract used by templates or JavaScript.
