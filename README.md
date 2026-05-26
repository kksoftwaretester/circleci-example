# CircleCI Reference Pipeline: Build, Test, and Deploy a Containerized Python API

**Author:** Katie Kemp  
**Repository:** https://github.com/kksoftwaretester/circleci-example  
**Passing build:** https://app.circleci.com/pipelines/circleci/KWgoZjy3HY7XW2BZZ5726y/QTg8vCV7jAB7mNo1we8NsB/24/workflows/f5bbe515-e971-467e-bb5b-4a14daf958fd

## What This Pipeline Does

This repository demonstrates a production-quality CI/CD pipeline built on CircleCI. It takes a Python Flask REST API from source code to a running container on AWS with every merge to `main`.

The pipeline:

1. **Builds** a Docker image from source and validates it against a declared container spec
2. **Tests** the application against a real PostgreSQL database, collecting structured test results
3. **Pushes** the validated image to AWS Elastic Container Registry (ECR)
4. **Deploys** a rolling update to AWS Elastic Container Service (ECS) on Fargate

Steps 3 and 4 only run on the `main` branch. Pull requests and feature branches build and test, but never touch production infrastructure.

## Application

The application is a small Flask REST API backed by PostgreSQL. It exposes two endpoints:

- `GET /healthz` — returns `{"status": "ok"}`. Used by the container spec validator and as a deployment health signal.
- `GET /items` / `POST /items` — a simple CRUD resource backed by a SQLAlchemy model, demonstrating real database interaction.

**Why Flask + SQLAlchemy?** Flask is lightweight and easy to containerize. SQLAlchemy provides a clean ORM layer over PostgreSQL that maps naturally to ECS/RDS in production. Both have first-class support in CircleCI's convenience images and orbs.

**Why PostgreSQL?** It is the most common relational database in cloud deployments and has the best-documented sidecar support in CircleCI. Using a real database (rather than SQLite or an in-memory mock) means test failures reflect real production behaviour.

Since I'm familiar with these frameworks and they are supported by CircleCI, it was an easy choice to build my app using them.

## Pipeline Architecture

```
unit-test ───────────────────┐
                             ├──► integration-test ──► build-push-ecr ──► deploy-ecs
build-app-image ─────────────┘        (main only)        (main only)
```

`unit-test` and `build-app-image` run in parallel from the moment a push lands. `integration-test` waits for both to pass before starting — meaning a unit test failure stops the pipeline before it ever spins up a database sidecar or builds a container.

### Job 1: `build-app-image`

Runs on every push, every branch.

The Dockerfile uses a **multi-stage build** with two targets:

- `base` — the lean production image: Python 3.12 slim, application code, a locked non-root user (`appuser`, UID 1000), and nothing else.
- `tester` — extends `base` by adding the [goss](https://github.com/goss-org/goss) binary and the `goss.yaml` spec file. This image is used only in CI and is never pushed to ECR.

The job builds both targets, starts the `tester` container, and runs `goss validate` inside it via `docker exec`. Goss checks:

- TCP port 5000 is listening
- `GET /healthz` returns HTTP 200 with body containing `"ok"`
- User `appuser` exists with UID/GID 1000
- The Python process is running

Once validation passes, the clean `base` image is saved to a **CircleCI workspace** — a shared file area that downstream jobs can attach to. This means the image is built exactly once and reused, rather than rebuilt in every job.

**Why goss?** Container testing tools like goss let you declare what a correctly-running container looks like as a spec file, checked into version control alongside the code. This is more maintainable and readable than ad-hoc shell assertions. The spec becomes documentation. This means errors are easier to debug. Retries are also built-in, which is handy.

**Why multi-stage?** Goss and its dependencies only belong in the test image. The production image stays minimal for maximum efficiency (in storage, time, and as a result, cost).

### Job 2a: `unit-test`

Runs on every push, every branch — in parallel with `build-app-image`, with no prerequisites.

This job runs the `tests/unit/` suite against a Flask app configured with an in-memory SQLite database. All database interactions are replaced with `unittest.mock` stubs, so the job has no external dependencies. It completes in seconds.

**Why unit tests with mocks?** Unit tests validate the behaviour of individual functions in isolation without the latency or state of a real database. While they're overkill for a tiny app like this, they are a critical part of good CI/CD because they give the developer quick feedback. If something has changed in the business logic and the tests have not been updated to accomdate it, they will fail, drawing the developer's attention to any mistaken changes or giving them a chance to update existing tests and add any test coverage for new features.

**Why run in parallel with `build-app-image`?** The two jobs are independent: unit tests need only source code, and `build-app-image` needs only Docker. Running them in parallel maximises throughput. A unit test failure fails the pipeline before any database sidecar is started or any container is built.

### Job 2b: `integration-test`

Runs on every push, every branch. Requires both `build-app-image` and `unit-test` to pass.

This job uses `cimg/python:3.12` as its executor and spins up a **`cimg/postgres:15` sidecar container** alongside it. A sidecar is a secondary container that shares the job's network. The application code can reach it at `localhost:5432` exactly as it would in production.

Before running tests, `scripts/wait-for-db.sh` polls `pg_isready` in a loop (with a 30-second timeout) until PostgreSQL is accepting connections. This prevents flaky failures caused by the database not being ready when the tests start.

The `tests/integration/` suite runs against the live PostgreSQL instance. Tests create real rows, query real indexes, and exercise real constraint enforcement. This means a test failure signals a real problem rather than a difference between the mock and the actual database engine.

Test results are exported as **JUnit XML** and uploaded with `store_test_results`. CircleCI is able to parse this and displays pass/fail counts, per-test timing, and failure messages directly in the UI. A coverage report is also generated and stored as a build artifact. The build fails if coverage falls below 80%.

**Why a real database in integration tests?** Mocking the database is the most common source of "tests pass but production breaks" failures. SQLAlchemy queries that work against a mock may fail against a real engine because mocks don't enforce types or constraints, and mode the actual transaction behaviour of the database. Testing against the real thing removes this category of bug entirely.

**Why `store_test_results`?** CircleCI uses the JUnit output to surface test insights in the UI, power the "Flaky Tests" detection feature, and enable intelligent test splitting for parallelism (a future optimisation described below).

**The test pyramid in practice:** Unit tests cover behaviour; integration tests cover correctness against real infrastructure. The two jobs together enforce a structured test pyramid. The fast tier (unit) gates the slow tier (integration), so developers get failure feedback in seconds rather than waiting for a database sidecar to start.

### Job 3: `build-push-ecr`

Runs only on `main`. Requires `test` to pass.

This job attaches the workspace, loads the pre-built Docker image, and pushes it to ECR tagged with both the Git commit SHA and `latest`.

Authentication to AWS uses **OIDC (OpenID Connect)** via the `aws-cli` orb. There are no AWS access keys stored anywhere in CircleCI. Instead:

1. CircleCI generates a short-lived, signed OIDC token scoped to this specific organisation, project, and build.
2. AWS IAM is configured to trust CircleCI as an identity provider. The IAM role's trust policy restricts assumption to tokens from this specific CircleCI organisation.
3. The `aws-cli` orb exchanges the token for temporary AWS credentials valid only for the duration of the job.

If credentials are leaked or a build is compromised, the credentials expire within minutes and cannot be reused. Rotating them requires no action — there is nothing to rotate.

**Why OIDC over static keys?** Static AWS access keys stored in CI are a significant security risk because they don't expire, they can be found in logs, and rotating them requires coordinating across every system that uses them. OIDC eliminates all of this. It is the current industry standard for CI-to-cloud authentication.

### Job 4: `deploy-ecs`

Runs only on `main`. Requires `build-push-ecr` to pass.

Issues an `aws ecs update-service --force-new-deployment` command, which triggers ECS to pull the new image and perform a **rolling deployment** which replaces old tasks with new ones while maintaining availability. The job then waits for the service to stabilise before completing, so a failed deployment fails the pipeline rather than silently leaving a broken service running.

**Why ECS Fargate?** Fargate is serverless compute for containers. You define the task (CPU, memory, image) and AWS runs it. Combined with ECR, it is the simplest path to production-grade container hosting on AWS that also supports OIDC natively.

## CircleCI Features and Value

| Feature | Where used | Value delivered |
|---|---|---|
| **Workspaces** | Image passed from `build-app-image` to `build-push-ecr` | Build once, reuse downstream so there are no redundant builds |
| **Job parallelism** | `unit-test` + `build-app-image` run concurrently | Faster wall-clock time; unit failures surface before infrastructure starts |
| **Service containers (sidecar)** | PostgreSQL in `integration-test` | Real database in CI without infrastructure setup |
| **`store_test_results`** | JUnit XML in `unit-test`, `integration-test` | Test insights, timing, and flaky test detection in the UI |
| **`store_artifacts`** | Test results + coverage report | Downloadable evidence of every build's quality |
| **Docker layer caching** | `build-app-image`, `build-push-ecr` | Unchanged layers are not rebuilt so image is built faster |
| **Dependency caching** | pip cache in `unit-test`, `integration-test` | Python packages restored from cache instead of re-downloaded |
| **Branch filtering** | `build-push-ecr`, `deploy-ecs` | Production jobs never run on feature branches |
| **OIDC authentication** | ECR push, ECS deploy | No static credentials anywhere in the pipeline |
| **CircleCI contexts** | `circleci-oidc-aws` | Secrets scoped to approved builds; not inherited by forks |
| **Fail fast (`-x`)** | pytest | First failure stops the run immediately (faster feedback loop) |
| **Coverage enforcement** | `--cov-fail-under=80` in `integration-test` | Coverage below 80% fails the build before it reaches production |
| **Multi-stage Docker build** | `Dockerfile` | Test tooling stays out of the production image |∂ƒƒ

## Potential Future Optimisations and Trade-offs

### Test parallelism
As the test suite grows, test time grows linearly. CircleCI supports splitting tests across multiple parallel containers using `circleci tests split` with timing data from previous runs. Combined with `pytest-xdist` for in-process parallelism, a suite that takes 5 minutes can be reduced to under 1 minute. This optimization is essential to most CircleCI customers, given the number of tests they have. For this simple example app, it would be overkill.

### Path-based pipeline filtering
The pipeline currently runs all jobs on every push regardless of what changed. CircleCI's `path-filtering` orb combined with **dynamic config** can skip the build entirely when only documentation or configuration files are modified. This requires restructuring the pipeline into a setup phase (which evaluates changed paths) and a continuation phase (which runs the appropriate jobs). 

### Load balancer and HTTPS
The ECS service currently runs without a load balancer. In production, an **Application Load Balancer (ALB)** should sit in front of the service to provide HTTPS termination, health-check-based routing, and zero-downtime deployments. Without it, the service is not reachable on a stable DNS name and traffic is not encrypted in transit.

### Approval gate before production
For change-control compliance, a manual approval step can be inserted between `build-push-ecr` and `deploy-ecs`. A designated reviewer must click "Approve" in the CircleCI UI before the deployment proceeds. This adds no overhead to the pipeline infrastructure — it is a single `type: approval` job in the workflow definition. 

It's not always necessary as approvals may already take place in your VCS. However, it may be useful to add a step like this to gate deployments on restricted deployment days. For example, at Amazon our pipelines were blocked around holidays like Christmas and Black Friday, as well as Prime Day Events. Deployments could only be released with special approval.

### Scheduled nightly tests
CircleCI scheduled pipelines can trigger the full test suite on a schedule (e.g. nightly against a staging database) independent of commits. This catches issues introduced by dependency updates, infrastructure drift, or external API changes that wouldn't otherwise trigger a build.

### End-to-end tests
The pipeline currently implements two tiers of the test pyramid — unit tests and integration tests — but not the third. End-to-end tests would exercise the full running stack as a black box: the application container, the database, and the HTTP API together. Rather than calling application code directly, they make real HTTP requests and assert on the responses, the same way a user or downstream service would.

In this pipeline, an end-to-end job would sit between `build-push-ecr` and `deploy-ecs`, deploying the new image to a staging environment and running the suite against it before allowing the production deploy to proceed. Tools like `pytest` with the `requests` library are sufficient for a simple API; more complex user-journey testing could use Playwright or Selenium.

The trade-off is cost and complexity: end-to-end tests are slow, require a live environment, and are the most likely tier to produce flaky failures. They are high-value for catching regressions that slip past unit and integration tests, but should be kept small and focused to avoid becoming a bottleneck.

For that reason, not all CI/CD processes necessitate them, and for this exmaple, they are definitely overkill.
