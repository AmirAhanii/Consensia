FROM python:3.11-slim

WORKDIR /app/backend

# Avoid Python writing .pyc files and show logs immediately.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install dependencies
COPY backend/pyproject.toml backend/env.template backend/alembic.ini ./
COPY backend/app ./app
COPY backend/data ./data
COPY backend/alembic ./alembic

# Ensure a README exists because pyproject.toml points to it.
RUN test -f README.md || printf "# consensia-backend\n" > README.md

# Editable install so code edits reflect immediately (with --reload).
RUN pip install --no-cache-dir -e .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]

