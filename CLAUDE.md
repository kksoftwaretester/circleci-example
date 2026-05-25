# CircleCI Field Engineer Reference Pipeline

## Project Purpose

This repo is a CircleCI Field Engineer candidate assignment. The goal is to build a reference pipeline that demonstrates CircleCI best practices and covers the following competencies:

- Custom Docker image built within the pipeline and used in a downstream job
- Automated testing with results collected by CircleCI (JUnit XML)
- Database integration via a sidecar container (PostgreSQL)
- Conditional pipeline execution (path filtering, branch restrictions)
- Shell scripting + a non-scripting language (Python)
- Artifact publish to cloud infrastructure — **only on merge to `main`**
- No credentials accessible outside approved builds; OIDC preferred

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Application | Python Flask + SQLAlchemy | First-class CircleCI orb support, clean testability |
| Database | PostgreSQL | Best CircleCI sidecar docs; SQLAlchemy integration |
| Testing | pytest + JUnit XML (`pytest-junit`) | CircleCI `store_test_results` compatible |
| Container testing | dgoss | Lightweight; validates the built image before pushing |
| Deployment target | AWS ECS (Fargate) via ECR | Supports OIDC; no long-lived credentials needed |
| OIDC | CircleCI to AWS via `aws-oidc` orb | Credentials scoped to approved builds only |

## Repository Layout (target state)

```
circle-ci-example/
├── .circleci/
│   └── config.yml          # pipeline config
├── app/
│   ├── __init__.py
│   ├── main.py             # Flask app entry point
│   ├── models.py           # SQLAlchemy models
│   └── routes.py           # API routes
├── tests/
│   ├── conftest.py         # pytest fixtures (real DB, not mocks)
│   ├── test_routes.py
│   └── test_models.py
├── scripts/
│   └── wait-for-db.sh      # shell script: polls until postgres is ready
├── Dockerfile              # production image
├── Dockerfile.test         # test image (extends production)
├── goss.yaml               # dgoss container spec
├── requirements.txt
└── CLAUDE.md
```

## Pipeline Architecture

### Jobs

```
build-app-image ──► test ──► build-push-ecr (main only)
                              └── deploy-ecs  (main only)
```

**`build-app-image`**
- Builds `Dockerfile` and saves the image as a CircleCI workspace artifact
- Runs `dgoss run` against the image to validate container spec

**`test`**
- Uses the image built in `build-app-image` as its executor
- Spins up a `postgres:15` sidecar container
- `scripts/wait-for-db.sh` blocks until postgres is accepting connections
- Runs `pytest --junitxml=test-results/junit.xml`
- Uploads results with `store_test_results` + `store_artifacts`

**`build-push-ecr`** (conditional: only on `main` branch)
- Uses CircleCI OIDC + `aws-oidc` orb to authenticate to AWS — no static credentials
- Tags and pushes the image to ECR

**`deploy-ecs`** (conditional: only on `main` branch, requires `build-push-ecr` success)
- Triggers a rolling ECS service update with the new image tag

### Conditional Execution

- `build-push-ecr` and `deploy-ecs` use a `when: equal [ main, << pipeline.git.branch >> ]` filter so they only run on merge to `main`.
- Path-based filtering (CircleCI `path-filtering` orb) can gate jobs when only docs or non-app files change.

### Credentials & OIDC

- No static AWS keys stored in CircleCI project settings.
- CircleCI generates a short-lived OIDC token per build; AWS IAM trusts the CircleCI OIDC provider for the specific org/project.
- All other secrets (e.g. `POSTGRES_PASSWORD` if needed for staging) go in a CircleCI context scoped to the project; context is referenced explicitly in `config.yml` and is not inherited by forked PRs.

## Key CircleCI Features Used

| Feature | Where |
|---|---|
| Custom executor image built in-pipeline | `build-app-image` to `test` |
| Service containers (sidecar) | postgres in `test` job |
| `store_test_results` | `test` job (JUnit XML) |
| `store_artifacts` | test results + built image digest |
| Branch filtering / conditional steps | `build-push-ecr`, `deploy-ecs` |
| OIDC (`aws-oidc` orb) | ECR push, ECS deploy |
| CircleCI contexts | AWS OIDC role ARN |
| Workspaces | Pass built image between jobs |
| `path-filtering` orb | Skip CI on docs-only changes |

## Implementation Notes

- The Flask app exposes a `/healthz` endpoint and a `/items` CRUD endpoint backed by postgres.
- `scripts/wait-for-db.sh` uses a `pg_isready` loop — this is the shell scripting component.
- `pytest` fixtures in `conftest.py` hit a real postgres instance (no mocking); this matches prod behaviour.
- `goss.yaml` checks: port 5000 is listening, `/healthz` returns 200, user is non-root.

## Assignment Deliverables Checklist

- [ ] Public VCS repo connected to CircleCI
- [ ] Custom docker image used in the pipeline
- [ ] Testing with CircleCI-collectible results
- [ ] Postgres sidecar container
- [ ] Conditional work (branch filter + path filter)
- [ ] Shell scripting (`wait-for-db.sh`) + Python application
- [ ] Artifact publish to AWS (ECR + ECS), main branch only
- [ ] OIDC — no static credentials
- [ ] Green build link
- [ ] Written customer-facing writeup

## Potential Future Optimizations (for writeup)

- Docker layer caching with `docker-layer-caching: true` to speed up image builds
- Parallelism: split pytest across multiple containers with `circleci tests split`
- Dynamic config to generate jobs based on changed service directories (monorepo)
- Approval gate before production deploy for change-control compliance
- Scheduled pipeline for nightly integration tests
- Migrate from ECS to Lambda + API Gateway for cost optimization on low-traffic workloads