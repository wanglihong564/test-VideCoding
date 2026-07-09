# Prelaunch Static Scan

Root: `C:\projects\shop-api`
Files scanned: 148

## Manifests

- `package.json`: `package.json`
- `package-lock.json`: `package-lock.json`
- `Dockerfile`: `Dockerfile`

## Package Manager Notes

- JavaScript lockfile present: package-lock.json

## Package Scripts

- `package.json` scripts: build, lint, test, test:e2e

## Frameworks

- Express/Fastify-style routing
- Next.js API Routes

## Route Inventory

| Method | Path | Framework | File | Risk hints |
|---|---|---|---|---|
| POST | `/api/orders` | Express/Fastify-style routing | `src/routes/orders.ts:18` | money(strong:path), data(medium:handler) |
| POST | `/api/webhooks/payment` | Express/Fastify-style routing | `src/routes/webhooks.ts:11` | money(strong:path) |
| PATCH | `/api/admin/users/:id` | Express/Fastify-style routing | `src/routes/admin.ts:28` | permissions(strong:path), data(strong:method) |

## Route Candidates

- `src/routes/orders.ts`
- `src/routes/webhooks.ts`
- `src/routes/admin.ts`

## Test Candidates

- `tests/orders.spec.ts`
- `tests/admin.spec.ts`

## Config Candidates

- env_examples: `.env.example`
- ci: `.github/workflows/ci.yml`
- docker: `Dockerfile`
- migrations: `migrations/202607090001_create_orders.sql`

## Security Surface

Security/auth-related files:

- `src/middleware/auth.ts`
- `src/security/cors.ts`

High-risk route hints:

- `POST /api/orders` in `src/routes/orders.ts:18` (money(strong:path))
- `PATCH /api/admin/users/:id` in `src/routes/admin.ts:28` (permissions(strong:path), data(strong:method))

Security notes:

- Permission-sensitive routes detected; verify horizontal and vertical access control.
- Money/order/payment routes detected; verify backend-owned amounts, idempotency, and webhook signatures.

## Test Quality Warnings

- `tests/admin.spec.ts`: only HTTP status assertions (may not validate persisted business results)

## Potential Secret Hits

- None detected by heuristic scan

## Suggested Safe Commands

- `npm run build`
- `npm run lint`
- `npm run test`
- `npm run test:e2e`
- `npm audit`

## Suggested Next Checks

- Review route inventory for auth, authorization, validation, and sensitive response fields.
- Prioritize route tests for entries with money, permissions, data, or availability risk hints.
- Weak-test patterns detected; verify important tests assert real business outcomes.
- Review migrations for backup, rollback, idempotency, and old-data compatibility.

