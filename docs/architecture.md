# SIBER — System Architecture

## Overview

SIBER is a self-service SaaS platform for authorized security analysis of web applications and APIs. The system follows a **modular monolith** architecture with clear domain boundaries, deployed as separate containers for isolation and scalability.

## Design Principles

- **Defense in depth**: Domain verification, SSRF protection, and least-privilege access at every layer.
- **Isolation**: Scan workers run in dedicated, resource-limited containers — never inside the API process.
- **Fail-safe defaults**: Production scans use Safe Scan mode only; aggressive tests require explicit staging authorization.
- **Provider independence**: AI and payment integrations sit behind abstraction layers.
- **Auditability**: All authorization acceptances and security-relevant actions are logged.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              Client Layer                                │
│  Next.js (App Router) · TypeScript · Tailwind · shadcn/ui · TanStack Q  │
└─────────────────────────────────┬───────────────────────────────────────┘
                                  │ HTTPS
┌─────────────────────────────────▼───────────────────────────────────────┐
│                         Reverse Proxy (Nginx/Traefik)                   │
│                    TLS termination · CSP · Rate limiting                 │
└───────────────┬─────────────────────────────────────┬───────────────────┘
                │                                     │
┌───────────────▼───────────────┐     ┌───────────────▼───────────────────┐
│      FastAPI API Server       │     │         Static / SSR Frontend      │
│  Auth · RBAC · REST API       │     │         (Next.js standalone)       │
└───────────────┬───────────────┘     └───────────────────────────────────┘
                │
    ┌───────────┼───────────┬──────────────┬──────────────┐
    │           │           │              │              │
┌───▼───┐  ┌───▼───┐  ┌───▼────┐   ┌─────▼─────┐  ┌──────▼──────┐
│Postgres│  │ Redis │  │ Celery │   │  Object   │  │   Worker    │
│        │  │       │  │ Broker │   │  Storage  │  │  Pool (N)   │
└────────┘  └───────┘  └───┬────┘   └───────────┘  └──────┬──────┘
                           │                               │
                    ┌──────▼──────┐                 ┌───────▼───────┐
                    │Celery Worker│                 │ ZAP · Nuclei  │
                    │  (API-side) │                 │ Semgrep · Trivy│
                    └─────────────┘                 └───────────────┘
```

## Container Topology (Development & Production)

| Container        | Role                                      | Resource Limits        |
|------------------|-------------------------------------------|------------------------|
| `frontend`       | Next.js UI                                | CPU/RAM per env        |
| `api`            | FastAPI REST API                          | CPU/RAM per env        |
| `worker`         | Celery task orchestration                 | CPU/RAM per env        |
| `scan-worker`    | Isolated per-scan execution (dynamic)     | Strict CPU/RAM/time    |
| `postgres`       | Primary relational store                  | Persistent volume      |
| `redis`          | Celery broker + cache + rate limits       | Persistent optional    |
| `nginx`          | Reverse proxy, TLS, security headers      | —                      |

Scan workers are **ephemeral**: provisioned per job, cleaned up after completion with temp files removed.

## Backend Modules (Modular Monolith)

```
backend/app/
├── core/           # Config, logging, security, database, redis
├── api/v1/         # Route handlers (thin)
├── schemas/        # Pydantic request/response models
├── models/         # SQLAlchemy ORM models
├── services/       # Business logic
│   ├── auth/
│   ├── users/
│   ├── organizations/
│   ├── projects/
│   ├── domains/
│   ├── domain_verification/
│   ├── scan_profiles/
│   ├── scan_jobs/
│   ├── scan_workers/
│   ├── findings/
│   ├── finding_normalization/
│   ├── risk_scoring/
│   ├── ai_analysis/
│   ├── reports/
│   ├── notifications/
│   ├── billing/
│   └── audit/
├── tasks/          # Celery task definitions
├── parsers/        # Tool output parsers (ZAP, Nuclei, etc.)
└── workers/        # Scan worker entrypoints
```

Each module exposes:
- **Models** — database entities
- **Schemas** — API contracts
- **Services** — domain logic (testable, no HTTP coupling)
- **Routes** — HTTP layer only

## Request Flow: Scan Lifecycle

```
User → API: POST /scans (verified domain, accepted authorization)
  → API validates: domain ownership, plan limits, rate limit, concurrent scan cap
  → API creates ScanJob (status: queued)
  → Celery: enqueue scan_orchestrator task
  → Worker: status → validating → provisioning
  → Worker: spawn isolated scan-worker container
  → Scan-worker: run tools per profile (Safe/Deep/Code)
  → Scan-worker: upload raw outputs to object storage
  → Worker: status → parsing → normalize findings → deduplicate
  → Worker: status → analyzing → optional AI enrichment
  → Worker: status → completed
  → Notification: scan completed
  → User: view findings, download report
```

## Domain Verification Flow

```
User adds domain → system generates unique token (TTL, single-use binding)
  → User chooses method: DNS TXT | /.well-known file | HTML meta tag
  → Background job re-validates periodically
  → If verification fails → block new scans, notify user
  → Subdomains require explicit inclusion in scan scope
```

## Data Stores

| Store          | Purpose                                              |
|----------------|------------------------------------------------------|
| PostgreSQL     | Users, orgs, projects, domains, scans, findings, audit |
| Redis          | Celery broker, session cache, rate limit counters    |
| Object Storage | Raw scan outputs, generated reports (HTML/PDF)       |

## Security Boundaries

- **API ↔ Scan Worker**: Workers receive scoped tokens; no direct DB access from scan containers.
- **Scan Worker ↔ Target**: Egress allowlist; SSRF blocklist for private/metadata IPs.
- **AI Layer**: Masked findings only; output schema-validated; never authoritative for vulnerability status.
- **Admin Panel**: Separate elevated permissions; no plaintext secrets in UI.

## Scan Profiles

| Profile    | Environment        | Tools (phased rollout)                          |
|------------|--------------------|-------------------------------------------------|
| Safe Scan  | Production         | Headers, TLS, passive ZAP, safe Nuclei, Trivy   |
| Deep Scan  | Staging/test only  | Active ZAP, extended Nuclei, auth-aware checks  |
| Code Scan  | Repo integration   | Semgrep, Trivy FS, dependency/secret analysis   |

## AI Integration Architecture

```
Finding (normalized) → DataMasker → AIProvider (abstract)
  → Structured JSON response (Zod/Pydantic validated)
  → Tags: unverified | verified | likely_false_positive
  → Stored alongside finding; scan succeeds even if AI fails
```

Supported providers via adapter pattern; initial: OpenAI API.

## Billing Architecture

```
SubscriptionService (abstract)
  ├── MockBillingProvider (Phase 1–8)
  └── StripeProvider (Phase 9+, future)

Plan limits enforced at:
  - Domain count
  - Scan frequency
  - Concurrent scans
  - Report retention
  - Feature flags (Deep Scan, API access, etc.)
```

## Observability

- Structured JSON logging with correlation IDs (`request_id`, `scan_id`)
- Health endpoints: `/health`, `/health/ready`, `/health/live`
- Metrics (Phase 10): scan duration, queue depth, worker utilization, AI cost
- Audit log: immutable append-only records for compliance

## Deployment Phases

| Phase | Focus                                              |
|-------|----------------------------------------------------|
| 1     | Infrastructure, health checks, Docker Compose      |
| 2     | Auth, users, organizations, roles, audit           |
| 3     | Projects, domain verification                      |
| 4     | Scan queue, workers, resource limits               |
| 5     | Security tools integration                         |
| 6     | Findings, normalization, dedup, risk scoring       |
| 7     | AI analysis layer                                  |
| 8     | Reports, retest, comparison                        |
| 9     | Billing, quotas                                    |
| 10    | Production hardening, CI/CD, monitoring            |

## Technology Stack Summary

- **Frontend**: Next.js 15, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query, Zod, React Hook Form
- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2, Celery, Redis
- **Database**: PostgreSQL 16
- **Scan Tools**: OWASP ZAP, Nuclei, Semgrep CE, Trivy (Phase 5+)
- **Infrastructure**: Docker, Docker Compose, Nginx
