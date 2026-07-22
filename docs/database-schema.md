# SIBER — Database Schema

## Entity Relationship Overview

```
users ──┬── organization_members ── organizations
        │                              │
        └── refresh_tokens             ├── projects ── domains
                                       │              └── domain_verifications
                                       ├── scan_jobs ── scan_job_tools
                                       │              └── authorization_acceptances
                                       ├── findings ── finding_history
                                       ├── reports
                                       ├── subscriptions
                                       ├── notifications
                                       └── audit_logs
```

## Tables

### users

| Column            | Type         | Constraints                    |
|-------------------|--------------|--------------------------------|
| id                | UUID         | PK, default gen_random_uuid()  |
| email             | VARCHAR(255) | UNIQUE, NOT NULL               |
| password_hash     | VARCHAR(255) | NOT NULL                       |
| full_name         | VARCHAR(255) |                                |
| is_active         | BOOLEAN      | DEFAULT true                   |
| is_email_verified | BOOLEAN      | DEFAULT false                  |
| is_platform_admin | BOOLEAN      | DEFAULT false                  |
| mfa_secret        | VARCHAR(255) | NULL (encrypted)               |
| mfa_enabled       | BOOLEAN      | DEFAULT false                  |
| failed_login_count| INTEGER      | DEFAULT 0                      |
| locked_until      | TIMESTAMPTZ  | NULL                           |
| created_at        | TIMESTAMPTZ  | NOT NULL, DEFAULT now()        |
| updated_at        | TIMESTAMPTZ  | NOT NULL, DEFAULT now()        |

**Indexes**: `email`, `is_active`

---

### email_verification_tokens

| Column     | Type        | Constraints                   |
|------------|-------------|-------------------------------|
| id         | UUID        | PK                            |
| user_id    | UUID        | FK → users.id, NOT NULL       |
| token_hash | VARCHAR(64) | NOT NULL                      |
| expires_at | TIMESTAMPTZ | NOT NULL                      |
| used_at    | TIMESTAMPTZ | NULL                          |
| created_at | TIMESTAMPTZ | NOT NULL                      |

---

### password_reset_tokens

| Column     | Type        | Constraints                   |
|------------|-------------|-------------------------------|
| id         | UUID        | PK                            |
| user_id    | UUID        | FK → users.id, NOT NULL       |
| token_hash | VARCHAR(64) | NOT NULL                      |
| expires_at | TIMESTAMPTZ | NOT NULL                      |
| used_at    | TIMESTAMPTZ | NULL                          |
| created_at | TIMESTAMPTZ | NOT NULL                      |

---

### refresh_tokens

| Column     | Type        | Constraints                   |
|------------|-------------|-------------------------------|
| id         | UUID        | PK                            |
| user_id    | UUID        | FK → users.id, NOT NULL       |
| token_hash | VARCHAR(64) | NOT NULL, UNIQUE              |
| expires_at | TIMESTAMPTZ | NOT NULL                      |
| revoked_at | TIMESTAMPTZ | NULL                          |
| created_at | TIMESTAMPTZ | NOT NULL                      |

**Indexes**: `user_id`, `token_hash`

---

### organizations

| Column      | Type         | Constraints                   |
|-------------|--------------|-------------------------------|
| id          | UUID         | PK                            |
| name        | VARCHAR(255) | NOT NULL                      |
| slug        | VARCHAR(100) | UNIQUE, NOT NULL              |
| owner_id    | UUID         | FK → users.id, NOT NULL       |
| is_active   | BOOLEAN      | DEFAULT true                  |
| created_at  | TIMESTAMPTZ  | NOT NULL                      |
| updated_at  | TIMESTAMPTZ  | NOT NULL                      |

---

### organization_members

| Column          | Type        | Constraints                          |
|-----------------|-------------|--------------------------------------|
| id              | UUID        | PK                                   |
| organization_id | UUID        | FK → organizations.id, NOT NULL      |
| user_id         | UUID        | FK → users.id, NOT NULL              |
| role            | VARCHAR(50) | NOT NULL (owner/admin/security_analyst/developer/viewer) |
| invited_by      | UUID        | FK → users.id                        |
| joined_at       | TIMESTAMPTZ | NOT NULL                             |

**Unique**: `(organization_id, user_id)`

---

### projects

| Column          | Type         | Constraints                   |
|-----------------|--------------|-------------------------------|
| id              | UUID         | PK                            |
| organization_id | UUID         | FK → organizations.id         |
| name            | VARCHAR(255) | NOT NULL                      |
| description     | TEXT         |                               |
| environment     | VARCHAR(50)  | production/staging/development|
| is_active       | BOOLEAN      | DEFAULT true                  |
| created_at      | TIMESTAMPTZ  | NOT NULL                      |
| updated_at      | TIMESTAMPTZ  | NOT NULL                      |

**Indexes**: `organization_id`

---

### domains

| Column          | Type         | Constraints                   |
|-----------------|--------------|-------------------------------|
| id              | UUID         | PK                            |
| project_id      | UUID         | FK → projects.id              |
| organization_id | UUID         | FK → organizations.id         |
| hostname        | VARCHAR(255) | NOT NULL                      |
| is_verified     | BOOLEAN      | DEFAULT false                 |
| verified_at     | TIMESTAMPTZ  | NULL                          |
| last_checked_at | TIMESTAMPTZ  | NULL                          |
| created_at      | TIMESTAMPTZ  | NOT NULL                      |
| updated_at      | TIMESTAMPTZ  | NOT NULL                      |

**Unique**: `(project_id, hostname)`
**Indexes**: `organization_id`, `is_verified`

---

### domain_verifications

| Column          | Type         | Constraints                          |
|-----------------|--------------|--------------------------------------|
| id              | UUID         | PK                                   |
| domain_id       | UUID         | FK → domains.id, NOT NULL            |
| token           | VARCHAR(64)  | NOT NULL, UNIQUE                     |
| method          | VARCHAR(50)  | dns_txt/well_known_file/meta_tag     |
| expires_at      | TIMESTAMPTZ  | NOT NULL                             |
| verified_at     | TIMESTAMPTZ  | NULL                                 |
| last_attempt_at | TIMESTAMPTZ  | NULL                                 |
| attempt_count   | INTEGER      | DEFAULT 0                            |
| created_at      | TIMESTAMPTZ  | NOT NULL                             |

---

### authorization_acceptances

| Column          | Type         | Constraints                   |
|-----------------|--------------|-------------------------------|
| id              | UUID         | PK                            |
| user_id         | UUID         | FK → users.id                 |
| organization_id | UUID         | FK → organizations.id       |
| scan_job_id     | UUID         | FK → scan_jobs.id (nullable)  |
| target          | VARCHAR(500) | NOT NULL                      |
| scan_profile    | VARCHAR(50)  | NOT NULL                      |
| ip_address      | INET         | NOT NULL                      |
| user_agent      | TEXT         |                               |
| accepted_at     | TIMESTAMPTZ  | NOT NULL                      |

*Immutable — no UPDATE/DELETE*

---

### scan_profiles (reference/seed data)

| Column       | Type         | Constraints                   |
|--------------|--------------|-------------------------------|
| id           | UUID         | PK                            |
| name         | VARCHAR(50)  | UNIQUE (safe/deep/code)       |
| display_name | VARCHAR(100) | NOT NULL                      |
| description  | TEXT         |                               |
| is_active    | BOOLEAN      | DEFAULT true                  |
| tools        | JSONB        | Tool configuration            |
| created_at   | TIMESTAMPTZ  | NOT NULL                      |

---

### scan_jobs

| Column            | Type         | Constraints                          |
|-------------------|--------------|--------------------------------------|
| id                | UUID         | PK                                   |
| organization_id   | UUID         | FK → organizations.id                |
| project_id        | UUID         | FK → projects.id                     |
| domain_id         | UUID         | FK → domains.id                      |
| initiated_by      | UUID         | FK → users.id                        |
| scan_profile      | VARCHAR(50)  | NOT NULL                             |
| target_url        | VARCHAR(500) | NOT NULL                             |
| status            | VARCHAR(50)  | NOT NULL (see status enum)           |
| scope_config      | JSONB        | Included paths, exclusions           |
| error_log         | TEXT         | NULL                                 |
| findings_count    | INTEGER      | DEFAULT 0                            |
| started_at        | TIMESTAMPTZ  | NULL                                 |
| completed_at      | TIMESTAMPTZ  | NULL                                 |
| cancelled_at      | TIMESTAMPTZ  | NULL                                 |
| celery_task_id    | VARCHAR(255) | NULL                                 |
| worker_container_id | VARCHAR(255) | NULL                             |
| created_at        | TIMESTAMPTZ  | NOT NULL                             |
| updated_at        | TIMESTAMPTZ  | NOT NULL                             |

**Status enum**: `queued`, `validating`, `provisioning`, `running`, `parsing`, `analyzing`, `completed`, `partially_completed`, `failed`, `cancelled`

**Indexes**: `organization_id`, `status`, `domain_id`, `created_at`

---

### scan_job_tools

| Column        | Type         | Constraints                   |
|---------------|--------------|-------------------------------|
| id            | UUID         | PK                            |
| scan_job_id   | UUID         | FK → scan_jobs.id             |
| tool_name     | VARCHAR(50)  | NOT NULL                      |
| tool_version  | VARCHAR(50)  |                               |
| status        | VARCHAR(50)  | NOT NULL                      |
| started_at    | TIMESTAMPTZ  | NULL                          |
| completed_at  | TIMESTAMPTZ  | NULL                          |
| output_path   | VARCHAR(500) | Object storage key            |
| error_message | TEXT         | NULL                          |
| findings_count| INTEGER      | DEFAULT 0                     |

---

### findings

| Column               | Type          | Constraints                   |
|----------------------|---------------|-------------------------------|
| id                   | UUID          | PK                            |
| organization_id      | UUID          | FK → organizations.id         |
| project_id           | UUID          | FK → projects.id              |
| scan_id              | UUID          | FK → scan_jobs.id             |
| source_tool          | VARCHAR(50)   | NOT NULL                      |
| source_rule_id       | VARCHAR(255)  |                               |
| title                | VARCHAR(500)  | NOT NULL                      |
| description          | TEXT          |                               |
| technical_details    | TEXT          |                               |
| evidence             | JSONB         | Masked                        |
| affected_url         | VARCHAR(1000) |                               |
| affected_parameter   | VARCHAR(255)  |                               |
| request_method       | VARCHAR(10)   |                               |
| request_sample       | TEXT          | Masked                        |
| response_sample      | TEXT          | Masked                        |
| severity             | VARCHAR(20)   | info/low/medium/high/critical |
| confidence           | VARCHAR(20)   |                               |
| cvss_score           | DECIMAL(3,1)  | NULL                          |
| cwe_id               | VARCHAR(20)   |                               |
| owasp_category       | VARCHAR(100)  |                               |
| remediation          | TEXT          |                               |
| references           | JSONB         |                               |
| fingerprint          | VARCHAR(64)   | NOT NULL                      |
| status               | VARCHAR(50)   | open/resolved/false_positive/accepted_risk/inconclusive |
| risk_score           | DECIMAL(5,2)  |                               |
| risk_factors         | JSONB         | Explainable scoring breakdown |
| first_seen_at        | TIMESTAMPTZ   | NOT NULL                      |
| last_seen_at         | TIMESTAMPTZ   | NOT NULL                      |
| resolved_at          | TIMESTAMPTZ   | NULL                          |
| false_positive_reason| TEXT          | NULL                          |
| ai_summary           | TEXT          | NULL                          |
| ai_remediation       | TEXT          | NULL                          |
| ai_confidence_label  | VARCHAR(50)   | unverified/verified/likely_false_positive |
| reviewer_notes       | TEXT          | NULL                          |
| created_at           | TIMESTAMPTZ   | NOT NULL                      |
| updated_at           | TIMESTAMPTZ   | NOT NULL                      |

**Unique**: `(project_id, fingerprint)` for deduplication
**Indexes**: `organization_id`, `scan_id`, `fingerprint`, `severity`, `status`

---

### finding_history

| Column     | Type        | Constraints                   |
|------------|-------------|-------------------------------|
| id         | UUID        | PK                            |
| finding_id | UUID        | FK → findings.id              |
| scan_id    | UUID        | FK → scan_jobs.id             |
| event_type | VARCHAR(50) | detected/reappeared/resolved/status_change |
| details    | JSONB       |                               |
| created_at | TIMESTAMPTZ | NOT NULL                      |

---

### retest_jobs

| Column          | Type        | Constraints                   |
|-----------------|-------------|-------------------------------|
| id              | UUID        | PK                            |
| finding_id      | UUID        | FK → findings.id              |
| scan_job_id     | UUID        | FK → scan_jobs.id             |
| status          | VARCHAR(50) | NOT NULL                      |
| result          | VARCHAR(50) | resolved/still_present/partially_resolved/inconclusive |
| previous_evidence | JSONB     |                               |
| new_evidence    | JSONB       |                               |
| created_at      | TIMESTAMPTZ | NOT NULL                      |
| completed_at    | TIMESTAMPTZ | NULL                          |

---

### reports

| Column          | Type         | Constraints                   |
|-----------------|--------------|-------------------------------|
| id              | UUID         | PK                            |
| organization_id | UUID         | FK → organizations.id         |
| scan_job_id     | UUID         | FK → scan_jobs.id             |
| report_type     | VARCHAR(50)  | technical/executive           |
| format          | VARCHAR(10)  | html/pdf/json/csv               |
| storage_path    | VARCHAR(500) | Object storage key            |
| generated_at    | TIMESTAMPTZ  | NOT NULL                      |
| generated_by    | UUID         | FK → users.id                 |

---

### subscriptions

| Column          | Type         | Constraints                          |
|-----------------|--------------|--------------------------------------|
| id              | UUID         | PK                                   |
| organization_id | UUID         | FK → organizations.id, UNIQUE        |
| plan            | VARCHAR(50)  | free/starter/professional/agency     |
| status          | VARCHAR(50)  | active/cancelled/past_due/trialing   |
| current_period_start | TIMESTAMPTZ |                             |
| current_period_end   | TIMESTAMPTZ |                             |
| external_id     | VARCHAR(255) | Payment provider ID (nullable)       |
| created_at      | TIMESTAMPTZ  | NOT NULL                             |
| updated_at      | TIMESTAMPTZ  | NOT NULL                             |

---

### usage_records

| Column          | Type        | Constraints                   |
|-----------------|-------------|-------------------------------|
| id              | UUID        | PK                            |
| organization_id | UUID        | FK → organizations.id         |
| metric          | VARCHAR(50) | scans/domains/ai_tokens/reports |
| quantity        | INTEGER     | NOT NULL                      |
| period_start    | TIMESTAMPTZ | NOT NULL                      |
| period_end      | TIMESTAMPTZ | NOT NULL                      |
| created_at      | TIMESTAMPTZ | NOT NULL                      |

---

### notifications

| Column          | Type         | Constraints                   |
|-----------------|--------------|-------------------------------|
| id              | UUID         | PK                            |
| user_id         | UUID         | FK → users.id                 |
| organization_id | UUID         | FK → organizations.id         |
| event_type      | VARCHAR(50)  | NOT NULL                      |
| title           | VARCHAR(255) | NOT NULL                      |
| message         | TEXT         |                               |
| is_read         | BOOLEAN      | DEFAULT false                 |
| metadata        | JSONB        |                               |
| created_at      | TIMESTAMPTZ  | NOT NULL                      |

---

### audit_logs

| Column          | Type         | Constraints                   |
|-----------------|--------------|-------------------------------|
| id              | UUID         | PK                            |
| organization_id | UUID         | FK → organizations.id (nullable) |
| user_id         | UUID         | FK → users.id (nullable)      |
| action          | VARCHAR(100) | NOT NULL                      |
| resource_type   | VARCHAR(50)  |                               |
| resource_id     | UUID         |                               |
| ip_address      | INET         |                               |
| user_agent      | TEXT         |                               |
| details         | JSONB        |                               |
| created_at      | TIMESTAMPTZ  | NOT NULL                      |

*Append-only — application layer prevents UPDATE/DELETE*

**Indexes**: `organization_id`, `user_id`, `action`, `created_at`

---

## Migration Strategy

- Alembic for all schema changes
- Initial migration: Phase 2 (users, organizations)
- Incremental migrations per development phase
- Never modify applied migrations in production

## Multi-Tenancy

All tenant-scoped queries **must** filter by `organization_id`. Row-level security (RLS) may be added in Phase 10 as defense-in-depth.
