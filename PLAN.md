# Assignment Completion Plan

## Overview

Build a CircleCI reference pipeline around a small Python Flask API backed by PostgreSQL.
The pipeline builds a custom Docker image, tests it against a real database, and deploys to AWS on merge to `main` using OIDC.

---

## Phase 1 — Application

**Goal:** A minimal but real Flask app that exercises the database.

### Files to create

- `app/__init__.py` — Flask factory
- `app/models.py` — SQLAlchemy `Item` model (id, name, created_at)
- `app/routes.py` — `GET /healthz`, `GET /items`, `POST /items`
- `requirements.txt` — Flask, SQLAlchemy, psycopg2-binary, pytest, pytest-flask, pytest-cov

### Done when
- `flask run` starts locally and `/healthz` returns 200
- At least one model with a real DB column

---

## Phase 2 — Tests

**Goal:** pytest suite that runs against a real postgres instance, outputs JUnit XML.

### Files to create

- `tests/conftest.py` — pytest fixtures: spin up Flask test client, connect to postgres via env var `DATABASE_URL`
- `tests/test_routes.py` — test `/healthz`, `POST /items`, `GET /items`
- `tests/test_models.py` — test model creation and query

### Done when
- `pytest --junitxml=test-results/junit.xml` passes locally with a running postgres

---

## Phase 3 — Docker

**Goal:** A production image and a dgoss spec to validate it.

### Files to create

- `Dockerfile` — multi-stage: build deps, then slim runtime image, non-root user
- `goss.yaml` — checks: port 5000 listening, `/healthz` returns HTTP 200, process runs as non-root

### Done when
- `docker build -t app .` succeeds
- `dgoss run app` passes all checks

---

## Phase 4 — Shell Script

**Goal:** Shell scripting component required by the assignment.

### Files to create

- `scripts/wait-for-db.sh` — loops `pg_isready` until postgres accepts connections (max 30s timeout, exits non-zero on timeout)

### Done when
- Script exits 0 when postgres is up, exits 1 after timeout

---

## Phase 5 — CircleCI Config

**Goal:** The `.circleci/config.yml` that wires everything together.

### Job breakdown

```
build-app-image
  └── docker build + dgoss test
  └── save image to workspace

test
  └── executor: image from workspace
  └── service: postgres:15 sidecar
  └── run wait-for-db.sh
  └── pytest --junitxml
  └── store_test_results + store_artifacts

build-push-ecr          [branch: main only]
  └── aws-oidc orb: assume role via OIDC
  └── docker tag + push to ECR

deploy-ecs              [branch: main only, requires build-push-ecr]
  └── aws ecs update-service --force-new-deployment
```

### CircleCI features to include

| Feature | Job |
|---|---|
| Workspaces | pass image tar from `build-app-image` to `test` |
| Service containers (sidecar) | postgres in `test` |
| `store_test_results` | JUnit XML in `test` |
| `store_artifacts` | test results in `test` |
| Branch filter (`when`) | `build-push-ecr`, `deploy-ecs` |
| OIDC (`aws-oidc` orb) | `build-push-ecr`, `deploy-ecs` |
| Context | AWS OIDC role ARN stored in CircleCI context |
| `path-filtering` orb | skip `build-app-image` on docs-only changes |

### Done when
- Config validates: `circleci config validate`
- All four jobs appear in the CircleCI UI

---

## Phase 6 — AWS Setup

**Goal:** ECR repo and ECS service to receive the deployment.

### Steps (one-time, done in AWS console or CLI)

1. Create ECR repository: `circle-ci-example`
2. Create ECS cluster + Fargate task definition + service (can use minimal nginx to bootstrap)
3. Create IAM OIDC identity provider for CircleCI in AWS IAM
4. Create IAM role `circleci-oidc-role` with trust policy scoped to your org/project
5. Attach policy: `AmazonEC2ContainerRegistryPowerUser` + `AmazonECSFullAccess`
6. Store role ARN in a CircleCI context (`AWS_ROLE_ARN`)

### Done when
- A manual `aws sts assume-role-with-web-identity` works with a CircleCI OIDC token

---

## Phase 7 — Connect Repo to CircleCI & Get a Green Build

1. Push repo to GitHub (public)
2. Connect project in CircleCI UI
3. Set up context with `AWS_ROLE_ARN`, `AWS_REGION`, `ECR_REPO_URI`, `ECS_CLUSTER`, `ECS_SERVICE`
4. Push a commit to a feature branch — `build-app-image` and `test` should run, deploy jobs should not
5. Merge to `main` — all four jobs should run green

### Done when
- Green build on `main` with all four jobs passing
- Deploy jobs did NOT run on the feature branch push

---

## Phase 8 — Writeup

Structure the writeup as a customer-facing reference doc:

1. **What it does** — brief summary of the app and pipeline
2. **Architecture** — pipeline diagram + job descriptions
3. **How components map together** — image hand-off via workspace, OIDC trust chain, sidecar pattern
4. **CircleCI value & optimizations used** — call out: OIDC, sidecar, `store_test_results`, conditional execution, workspaces
5. **Future optimizations / trade-offs** — layer caching, test parallelism, dynamic config, approval gate, Lambda migration

---

## Checklist

- [ ] Phase 1: Flask app
- [ ] Phase 2: pytest suite
- [ ] Phase 3: Dockerfile + dgoss spec
- [ ] Phase 4: wait-for-db.sh
- [ ] Phase 5: .circleci/config.yml
- [ ] Phase 6: AWS ECR + ECS + OIDC role
- [ ] Phase 7: green build on CircleCI
- [ ] Phase 8: customer writeup + submission
