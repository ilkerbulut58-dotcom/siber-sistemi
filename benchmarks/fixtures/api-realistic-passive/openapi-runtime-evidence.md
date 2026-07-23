# crAPI Realistic Fixture — OpenAPI Runtime Exposure Evidence (Faz 12.1)

## Question

Does the pinned crAPI stack behind `benchmark-crapi-proxy` expose OpenAPI/Swagger documentation at runtime?

## Fixture topology

- Proxy: `benchmarks/docker/realistic/nginx/crapi-proxy.conf` → forwards all paths to `benchmark-crapi-web:80`
- Services: identity (Java/Spring), community (Go), workshop (Python) — OpenAPI spec exists in upstream repo but is **not published** as a served document by default ([OWASP ZAP crAPI docs](https://github.com/zaproxy/zaproxy-website/blob/main/site/content/docs/testapps/crapi.md), [Beesley.tech crAPI guide](https://beesley.tech/owasp-crapi-docker-zap-api-security-guide/))

## Probe method

Run `scripts/probe-crapi-openapi-paths.py` against `https://benchmark-crapi-proxy` with the lab CA bundle (`benchmarks/docker/realistic/certs/ca.crt`).

Paths include standard OpenAPI locations plus crAPI service prefixes and Spring springdoc defaults (`/identity/api/v3/api-docs`, `/swagger-ui/index.html`).

## CI evidence

The probe runs in GitHub Actions during `benchmark-api-active-repeat` and writes `benchmarks/reports/crapi-openapi-probe.json`.

When `runtime_openapi_exposed` is `false` across all probed paths, the `exposed-api-docs` expectation on this fixture is a **ground-truth mismatch**, not a scanner false negative.

## Ground-truth correction (evidence-backed)

`benchmarks/fixtures/api-realistic-passive/ground-truth.yaml` marks `exposed-api-docs` as `automation_support: unsupported` because the pinned lab fixture does not serve OpenAPI at runtime.

`subset-main.yaml` excludes `exposed-api-docs` from the active measurable subset (4 keys: CSP, HSTS, server-disclosure, permissive-cors).

## Product impact

OpenAPI discovery remains implemented in `backend/app/scanners/api_surface_scanner.py` for targets that **do** expose specs. crAPI lab FN was a fixture expectation error, not missing product capability.
