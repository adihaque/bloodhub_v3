# Blood Hub Admin Console

Production-oriented Next.js App Router companion for the Blood Hub admin API. It is intentionally dependency-light and lives independently under `web/admin-console`.

## Setup

```bash
cd web/admin-console
copy .env.example .env.local
# Set NEXT_PUBLIC_API_BASE_URL to the API origin (for example http://localhost:8000)
npm install
npm run dev
```

Open http://localhost:3000. Sign in with an account whose API role is `ADMIN`. The browser stores access and refresh tokens in localStorage under `bloodhub.admin.auth`; clear site data to revoke local client state. API requests attach the stored access token to the Authorization header and rotate tokens through `/api/v1/auth/refresh` when a request returns 401.

## Supported API paths

- `POST /api/v1/auth/login`, `POST /api/v1/auth/refresh`, `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`
- `GET /api/v1/admin/metrics`, `/requests`, `/requests/:id/inspection`, `/algorithm`
- `PUT /api/v1/admin/algorithm`, `POST /api/v1/admin/algorithm/reset`
- `POST /api/v1/admin/requests/:id/trigger-wave`

This is source scaffolding: no `node_modules` or build artifacts are included. It expects the backend CORS configuration to allow the deployed console origin.

