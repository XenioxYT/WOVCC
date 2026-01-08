# Dockerfile

# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container to /app
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install system dependencies needed for building some Python packages (like psycopg2),
# for the PostgreSQL client (for pg_dump, etc.), and fonts for image generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    postgresql-client \
    fontconfig \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install the Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container at /app
COPY . .

# Tell Gunicorn to run the app. The module is `backend.app` and the Flask object is `app`.
# We use --chdir to make the backend directory the working directory for Gunicorn.
CMD ["gunicorn", "--chdir", "backend", "--bind", "0.0.0.0:5000", "app:app"]