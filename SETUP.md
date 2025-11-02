# WOVCC Setup Guide

This guide will help you set up the WOVCC website with the new features including database, Stripe integration, and authentication.

## Prerequisites

- Python 3.8+
- pip
- Stripe account (for test mode: https://dashboard.stripe.com/test/apikeys)

## Initial Setup

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and update with your values:

```bash
cp .env.example .env
```

Edit `.env` and set:
- `JWT_SECRET_KEY`: A strong random secret key (generate one: `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- `STRIPE_SECRET_KEY`: Your Stripe test secret key (starts with `sk_test_`)
- `STRIPE_PUBLISHABLE_KEY`: Your Stripe test publishable key (starts with `pk_test_`)
- `STRIPE_WEBHOOK_SECRET`: For webhook verification (get from Stripe dashboard)
- Update `STRIPE_SUCCESS_URL` and `STRIPE_CANCEL_URL` with your domain

### 3. Initialize Database

```bash
python backend/database.py
```

This will create the SQLite database file `wovcc.db` in the backend directory.

### 4. Create Admin User

```bash
python backend/create_admin.py
```

Follow the prompts to create your first admin user.

### 5. Run the API Server

```bash
python backend/api.py
```

The API will start on `http://localhost:5000`

## Stripe Test Mode Setup

1. Go to https://dashboard.stripe.com/test/apikeys
2. Copy your test API keys to `.env`
3. For testing payments, use these test card numbers:
   - Success: `4242 4242 4242 4242`
   - Decline: `4000 0000 0000 0002`
   - Any future expiry date and any 3-digit CVC

### Webhook Setup (for production)

For testing webhooks locally, use Stripe CLI:

```bash
stripe listen --forward-to localhost:5000/api/payments/webhook
```

This will give you a webhook secret to add to `.env`.

## New Features

### Authentication System
- JWT-based authentication
- Secure password hashing with bcrypt
- Token-based API access
- Protected admin endpoints

### Stripe Integration
- Stripe Checkout for payments
- Automatic membership activation on payment
- Customer ID storage for renewals

### Database
- SQLite database for user management
- User profiles with membership status
- Payment tracking

### UI Improvements
- Skeleton loaders for better UX
- Last updated timestamps
- Accessibility improvements (ARIA labels, keyboard navigation)
- Smooth animations and transitions

## API Endpoints

### Public Endpoints
- `GET /api/health` - Health check
- `GET /api/teams` - Get all teams
- `GET /api/fixtures` - Get fixtures
- `GET /api/results` - Get results
- `GET /api/data` - Get all data
- `GET /api/match-status` - Check for matches today
- `GET /api/live-config` - Get live config
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user

### Protected Endpoints (Requires Auth)
- `POST /api/auth/logout` - Logout
- `GET /api/user/profile` - Get user profile
- `POST /api/user/update` - Update profile
- `POST /api/payments/create-checkout` - Create Stripe checkout

### Admin Only Endpoints
- `POST /api/live-config` - Update live config
- `POST /api/clear-cache` - Clear cache

## Troubleshooting

### Database Issues
- If database file is locked, make sure only one process is accessing it
- To reset database, delete `backend/wovcc.db` and run `python backend/database.py` again

### Stripe Issues
- Make sure you're using test mode keys
- Check that webhook URL is accessible (for production)
- Verify environment variables are set correctly

### Authentication Issues
- Clear browser localStorage if having token issues
- Check that JWT_SECRET_KEY is set in `.env`
- Verify API base URL in `scripts/auth.js` matches your setup

## Migration from Old System

The old localStorage-based authentication has been replaced with a database system. Existing users will need to:
1. Register a new account, or
2. An admin can create accounts manually

## Production Deployment

1. Change `DEBUG=False` in `.env`
2. Set strong `JWT_SECRET_KEY`
3. Use production Stripe keys
4. Set proper CORS origins
5. Use PostgreSQL instead of SQLite (update `DATABASE_URL`)
6. Set up proper SSL/TLS
7. Configure webhook endpoints in Stripe dashboard

