FROM python:3.12-slim AS base

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY app/main.py .

RUN useradd --no-create-home --shell /bin/false appuser
USER appuser

EXPOSE 5000

ENV FLASK_APP=app/main.py

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]

# Tester stage: extends base with goss for container spec validation.
# Never pushed to ECR — used only in CI to validate the production image.
FROM base AS tester
USER root
RUN apt-get update -qq && apt-get install -y --no-install-recommends curl ca-certificates && \
    GOSS_VER=$(curl -fsSL https://api.github.com/repos/goss-org/goss/releases/latest \
      | grep '"tag_name"' | sed 's/.*"v\([^"]*\)".*/\1/') && \
    curl -fsSL "https://github.com/goss-org/goss/releases/download/v${GOSS_VER}/goss-linux-amd64" \
      -o /usr/local/bin/goss && \
    chmod +x /usr/local/bin/goss && \
    apt-get purge -y curl ca-certificates && \
    apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/*
COPY goss.yaml /goss.yaml
USER appuser
