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
