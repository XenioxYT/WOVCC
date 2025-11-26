# WOVCC Website

A professional website and membership portal for Wickersley Old Village Cricket Club, built with a Python Flask backend, PostgreSQL database, and a dynamic frontend.

## Project Overview

This project provides a full-featured, production-ready website for the cricket club. It includes a complete membership system with payments, an administrative backend for site management, and dynamic content modules for events and match data.

## DB Migrations

```
docker-compose exec web alembic upgrade head
```

## Features

* Full member authentication (Join, Login, Password Reset) using a PostgreSQL database and JWT.

* Stripe integration for processing membership payments and optional add-ons.

* Comprehensive admin panel for managing users, events, and editable site content (CMS).

* Dynamic event system with support for creating, editing, and deleting events, including support for recurring events and image uploads.

* AI-powered (OpenAI) helper for generating event descriptions within the admin panel.

* A Play-Cricket web scraper (`scraper.py`) fetches team, fixture, and result data, which is cached in `scraped_data.json` and served via the API for high performance.

* A "Smart" match hub on the homepage automatically shows live scores on match days, controlled via the admin panel.

* Contact form with automated email notifications.

* Newsletter subscription integration with Mailchimp.

## Technology Stack

* **Backend:** Python 3.12, Flask, SQLAlchemy, Gunicorn

* **Database:** PostgreSQL

* **Frontend:** HTML5, CSS3, Vanilla JavaScript (ES6+)

* **APIs & Integrations:** Stripe (Payments), Mailchimp (Newsletter), Brevo (SMTP), OpenAI (AI Help)

* **Deployment:** Docker, Docker Compose, Nginx (as reverse proxy)

## Project Structure

```

WOVCC/
├── backend/
│   ├── app.py             \# Main Flask application factory
│   ├── database.py        \# SQLAlchemy models and DB connection
│   ├── scraper.py         \# Play-Cricket web scraper
│   ├── auth.py            \# JWT and password hashing utilities
│   ├── stripe\_config.py   \# Stripe payment integration
│   ├── mailchimp.py       \# Mailchimp integration
│   ├── email\_config.py    \# SMTP email configuration
│   ├── routes\_*.py        \# API endpoint blueprints (auth, admin, events)
│   ├── templates/         \# HTML templates (index, join, admin, etc.)
│   └── ...
├── scripts/
│   ├── api-client.js      \# Frontend API communication
│   ├── auth.js            \# User login/signup logic
│   ├── match-controller.js\# Homepage match display logic
│   └── admin-*.js         \# Admin panel JavaScript modules
├── styles/
│   ├── main.css           \# Core site styles
│   └── pages.css          \# Page-specific styles
├── assets/
│   ├── logo.webp
│   └── banner.webp
├── Dockerfile             \# Container definition for the web application
├── docker-compose.yml     \# Docker Compose setup for web + db services
├── requirements.txt       \# Python dependencies
└── README.md              \# This file

```

## Getting Started (Local Development)

The recommended method for local development is using Docker Compose, which mirrors the production environment.

### Recommended: Docker Compose

1. **Create Environment File:**
   Copy `backend/.env.example` to `backend/.env` and fill in all the required API keys and secrets.

```

cp backend/.env.example backend/.env

# Now edit backend/.env with your keys

```

2. **Build and Run:**
From the project root, run:

```

docker-compose up --build

```

3. **Access:**
The application will be running at `http://localhost:5000`. The PostgreSQL database is also managed by Compose.

4. **Create Admin User:**
To create your first admin user, run the interactive script in a separate terminal:

```

docker-compose exec web python backend/create\_admin.py

```

### Alternative: Manual Flask Setup

1. **Setup Database:**
Ensure you have a PostgreSQL server running and create a database.

2. **Create Environment File:**
Copy `backend/.env.example` to `backend/.env`. Update `DATABASE_URL` to point to your local PostgreSQL database (e.g., `postgresql://user:pass@localhost:5432/wovcc_db`). Fill in all other keys.

3. **Install Dependencies:**

```

pip install -r requirements.txt

```

4. **Run Application:**

```

cd backend
python app.py

```

5. **Create Admin User:**

```

python backend/create\_admin.py

```

## Configuration

All configuration is managed via environment variables loaded from `backend/.env`. See `backend/.env.example` for the full list of required keys, including:

* `DATABASE_URL`: Connection string for PostgreSQL.

* `JWT_SECRET_KEY`: A long, random string for signing auth tokens.

* `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`: Stripe API keys.

* `STRIPE_PRICE_ID`, `STRIPE_SPOUSE_CARD_PRICE_ID`: Stripe Price IDs for your products.

* `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`: For sending emails.

* `MAILCHIMP_API_KEY`, `MAILCHIMP_LIST_ID`: For newsletter subscriptions.

* `OPENAI_API_KEY`: For the admin help assistant.

## Core API Endpoints

* `GET /api/health`: Health check.

* `GET /api/data`: Get all cached cricket data (teams, fixtures, results).

* `GET /api/live-config`: Get the current live match display configuration.

* `POST /api/live-config`: Set the live match display configuration (Admin).

* `POST /api/auth/pre-register`: Begin new member registration and create a Stripe session.

* `POST /api/auth/login`: Log in a user and return JWT tokens.

* `POST /api/auth/refresh`: Refresh an expired access token using the `httpOnly` refresh cookie.

* `POST /api/auth/activate`: Activates a user account after successful payment using a secure token.

* `GET /api/user/profile`: Get the current authenticated user's details.

* `DELETE /api/user/delete-account`: Allows a user to delete their own account (GDPR).

* `GET /api/events`: Get all published events.

* `POST /api/events`: Create a new event (Admin).

* `GET /api/admin/stats`: Get dashboard statistics (Admin).

* `GET /api/admin/users`: Get all users with pagination and filters (Admin).

* `PUT /api/admin/users/<id>`: Update a user's details (Admin).

* `GET /api/admin/content`: Get all editable content snippets (Admin).

* `PUT /api/admin/content/<key>`: Update a content snippet (Admin).

## Deployment

This project is configured for deployment using Docker Compose.

1. Ensure your server has `docker` and `docker-compose` installed.

2. Copy the entire project directory to your server.

3. Create the `backend/.env` file on the server with your production keys.

4. Run the application in detached mode:

```

docker-compose up -d --build

```

5. Set up Nginx as a reverse proxy to forward requests from your domain (e.g., `https://wovcc.co.uk`) to `http://localhost:5000`. Use the `backend/nginx.conf` file as a template.

6. Ensure you configure SSL using Let's Encrypt or another provider.

## Support

To view logs for the running services:

```

# View web application logs

docker-compose logs -f web

# View database logs

docker-compose logs -f db

```

To run a one-off script (like creating an admin):

```

docker-compose exec web python backend/create\_admin.py

```
