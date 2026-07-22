# SIBER — API Endpoint Plan

Base URL: `/api/v1`

All responses follow a common envelope:

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": { "request_id": "..." }
}
```

Error responses:

```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Human-readable message",
    "details": []
  },
  "meta": { "request_id": "..." }
}
```

---

## Health (Phase 1) ✅

| Method | Path              | Auth | Description                    |
|--------|-------------------|------|--------------------------------|
| GET    | `/health`         | No   | Basic health check             |
| GET    | `/health/live`    | No   | Liveness probe                 |
| GET    | `/health/ready`   | No   | Readiness (DB + Redis)         |

---

## Authentication (Phase 2)

| Method | Path                        | Auth | Description                |
|--------|-----------------------------|------|----------------------------|
| POST   | `/auth/register`            | No   | User registration          |
| POST   | `/auth/login`               | No   | Login, return tokens       |
| POST   | `/auth/logout`              | Yes  | Revoke refresh token       |
| POST   | `/auth/refresh`             | No   | Rotate refresh token       |
| POST   | `/auth/verify-email`        | No   | Verify email with token    |
| POST   | `/auth/resend-verification` | Yes  | Resend verification email  |
| POST   | `/auth/forgot-password`     | No   | Request password reset     |
| POST   | `/auth/reset-password`      | No   | Reset password with token  |
| GET    | `/auth/me`                  | Yes  | Current user profile       |

---

## Users (Phase 2)

| Method | Path              | Auth | Role   | Description           |
|--------|-------------------|------|--------|-----------------------|
| GET    | `/users/me`       | Yes  | Any    | Get own profile       |
| PATCH  | `/users/me`       | Yes  | Any    | Update own profile    |
| PATCH  | `/users/me/password` | Yes | Any  | Change password       |

---

## Organizations (Phase 2)

| Method | Path                                    | Auth | Role          | Description              |
|--------|-----------------------------------------|------|---------------|--------------------------|
| POST   | `/organizations`                        | Yes  | Any           | Create organization      |
| GET    | `/organizations`                        | Yes  | Member        | List user's orgs         |
| GET    | `/organizations/{org_id}`               | Yes  | Member        | Get organization         |
| PATCH  | `/organizations/{org_id}`               | Yes  | Owner/Admin   | Update organization      |
| DELETE | `/organizations/{org_id}`               | Yes  | Owner         | Delete organization      |
| GET    | `/organizations/{org_id}/members`       | Yes  | Member        | List members             |
| POST   | `/organizations/{org_id}/members/invite`| Yes  | Owner/Admin   | Invite member            |
| PATCH  | `/organizations/{org_id}/members/{id}`  | Yes  | Owner/Admin   | Update member role       |
| DELETE | `/organizations/{org_id}/members/{id}`  | Yes  | Owner/Admin   | Remove member            |

---

## Projects (Phase 3)

| Method | Path                                          | Auth | Role              | Description        |
|--------|-----------------------------------------------|------|-------------------|--------------------|
| POST   | `/organizations/{org_id}/projects`          | Yes  | Admin+            | Create project     |
| GET    | `/organizations/{org_id}/projects`            | Yes  | Viewer+           | List projects      |
| GET    | `/organizations/{org_id}/projects/{id}`     | Yes  | Viewer+           | Get project        |
| PATCH  | `/organizations/{org_id}/projects/{id}`     | Yes  | Admin+            | Update project     |
| DELETE | `/organizations/{org_id}/projects/{id}`     | Yes  | Admin+            | Delete project     |

---

## Domains (Phase 3)

| Method | Path                                                    | Auth | Role              | Description              |
|--------|---------------------------------------------------------|------|-------------------|--------------------------|
| POST   | `/organizations/{org_id}/projects/{pid}/domains`      | Yes  | Admin+            | Add domain               |
| GET    | `/organizations/{org_id}/projects/{pid}/domains`      | Yes  | Viewer+           | List domains             |
| GET    | `/organizations/{org_id}/projects/{pid}/domains/{id}` | Yes  | Viewer+           | Get domain               |
| DELETE | `/organizations/{org_id}/projects/{pid}/domains/{id}` | Yes  | Admin+            | Remove domain            |
| POST   | `/organizations/{org_id}/projects/{pid}/domains/{id}/verify` | Yes | Admin+     | Trigger verification     |
| GET    | `/organizations/{org_id}/projects/{pid}/domains/{id}/verification-instructions` | Yes | Viewer+ | Get verification steps |

---

## Scan Profiles (Phase 4)

| Method | Path              | Auth | Role   | Description              |
|--------|-------------------|------|--------|--------------------------|
| GET    | `/scan-profiles`  | Yes  | Any    | List available profiles  |
| GET    | `/scan-profiles/{name}` | Yes | Any  | Get profile details      |

---

## Scans (Phase 4+)

| Method | Path                                          | Auth | Role              | Description              |
|--------|-----------------------------------------------|------|-------------------|--------------------------|
| POST   | `/organizations/{org_id}/scans`               | Yes  | Security Analyst+ | Start scan (requires authorization acceptance) |
| GET    | `/organizations/{org_id}/scans`               | Yes  | Viewer+           | List scans               |
| GET    | `/organizations/{org_id}/scans/{id}`          | Yes  | Viewer+           | Get scan details         |
| GET    | `/organizations/{org_id}/scans/{id}/status`   | Yes  | Viewer+           | Poll scan progress       |
| POST   | `/organizations/{org_id}/scans/{id}/cancel`   | Yes  | Security Analyst+ | Cancel running scan      |

---

## Findings (Phase 6)

| Method | Path                                                    | Auth | Role              | Description           |
|--------|---------------------------------------------------------|------|-------------------|-----------------------|
| GET    | `/organizations/{org_id}/findings`                      | Yes  | Viewer+           | List findings (filter)|
| GET    | `/organizations/{org_id}/findings/{id}`                 | Yes  | Viewer+           | Get finding detail    |
| PATCH  | `/organizations/{org_id}/findings/{id}`                 | Yes  | Developer+        | Update status/notes   |
| POST   | `/organizations/{org_id}/findings/{id}/retest`          | Yes  | Developer+        | Trigger retest        |
| GET    | `/organizations/{org_id}/findings/{id}/history`         | Yes  | Viewer+           | Finding history       |

---

## Reports (Phase 8)

| Method | Path                                          | Auth | Role    | Description          |
|--------|-----------------------------------------------|------|---------|----------------------|
| POST   | `/organizations/{org_id}/scans/{id}/reports`  | Yes  | Analyst+| Generate report      |
| GET    | `/organizations/{org_id}/reports`             | Yes  | Viewer+ | List reports         |
| GET    | `/organizations/{org_id}/reports/{id}`        | Yes  | Viewer+ | Get report metadata  |
| GET    | `/organizations/{org_id}/reports/{id}/download` | Yes | Viewer+ | Download report file |

---

## Notifications (Phase 2+)

| Method | Path                              | Auth | Role | Description        |
|--------|-----------------------------------|------|------|--------------------|
| GET    | `/notifications`                  | Yes  | Any  | List notifications |
| PATCH  | `/notifications/{id}/read`        | Yes  | Any  | Mark as read       |
| POST   | `/notifications/read-all`         | Yes  | Any  | Mark all as read   |

---

## Billing (Phase 9)

| Method | Path                                    | Auth | Role  | Description           |
|--------|-----------------------------------------|------|-------|-----------------------|
| GET    | `/organizations/{org_id}/subscription`  | Yes  | Owner | Get subscription      |
| GET    | `/organizations/{org_id}/usage`         | Yes  | Owner | Get usage metrics     |
| POST   | `/organizations/{org_id}/subscription/upgrade` | Yes | Owner | Upgrade plan    |

---

## Audit Logs (Phase 2)

| Method | Path                                    | Auth | Role          | Description     |
|--------|-----------------------------------------|------|---------------|-----------------|
| GET    | `/organizations/{org_id}/audit-logs`    | Yes  | Owner/Admin   | List audit logs |

---

## Admin (Phase 2+)

| Method | Path                        | Auth | Role           | Description              |
|--------|-----------------------------|------|----------------|--------------------------|
| GET    | `/admin/users`              | Yes  | Platform Admin | List all users           |
| PATCH  | `/admin/users/{id}`         | Yes  | Platform Admin | Suspend/activate user    |
| GET    | `/admin/organizations`      | Yes  | Platform Admin | List organizations       |
| GET    | `/admin/scan-jobs`          | Yes  | Platform Admin | List all scan jobs       |
| GET    | `/admin/workers`            | Yes  | Platform Admin | Worker status            |
| GET    | `/admin/system/health`      | Yes  | Platform Admin | Extended system health   |
| GET    | `/admin/audit-logs`         | Yes  | Platform Admin | Platform audit logs      |
| GET    | `/admin/abuse-reports`      | Yes  | Platform Admin | Abuse reports            |

---

## Rate Limiting Headers

All rate-limited endpoints return:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1620000000
```

## Pagination

List endpoints support:

```
?page=1&page_size=20&sort=-created_at
```

Response meta:

```json
{
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 150,
    "total_pages": 8
  }
}
```

## Phase Implementation Status

| Phase | Endpoints                                      | Status     |
|-------|------------------------------------------------|------------|
| 1     | Health checks                                  | Phase 1    |
| 2     | Auth, Users, Organizations, Audit, Notifications | Planned |
| 3     | Projects, Domains, Verification                | Planned    |
| 4     | Scan Profiles, Scans                           | Planned    |
| 6     | Findings                                       | Planned    |
| 8     | Reports, Retest                                | Planned    |
| 9     | Billing                                        | Planned    |
