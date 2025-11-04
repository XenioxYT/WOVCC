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

Create a `.env` file in the `backend` directory with the following:

```bash
# JWT Secret (generate a strong random key)
JWT_SECRET_KEY=your-secret-key-here

# Stripe Configuration
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_PRODUCT_ID=prod_TLphFe62v2j1Xw
# STRIPE_PRICE_ID=price_...  # Optional: Use a specific Price ID instead of creating inline prices
# STRIPE_WEBHOOK_SECRET=whsec_...  # Leave commented for development, set for production

# URLs
STRIPE_SUCCESS_URL=http://localhost:5000/pages/join.html?success=true
STRIPE_CANCEL_URL=http://localhost:5000/pages/join.html?canceled=true
```

**Important Configuration Notes:**
- `JWT_SECRET_KEY`: Generate a strong random key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- `STRIPE_SECRET_KEY`: Your Stripe test secret key (starts with `sk_test_`)
- `STRIPE_PUBLISHABLE_KEY`: Your Stripe test publishable key (starts with `pk_test_`)
- `STRIPE_PRODUCT_ID`: Your Stripe product ID (default: `prod_TLphFe62v2j1Xw`)
- `STRIPE_PRICE_ID`: (Optional) If you have a Price object in Stripe, set this. Otherwise, prices are created inline using `STRIPE_PRODUCT_ID`
- `STRIPE_WEBHOOK_SECRET`: Leave commented/blank for development. Set when using Stripe CLI or in production
- Update `STRIPE_SUCCESS_URL` and `STRIPE_CANCEL_URL` with your actual domain in production

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

### Getting Your Stripe Keys

1. Go to https://dashboard.stripe.com/test/apikeys
2. Copy your **Publishable key** (starts with `pk_test_`) and **Secret key** (starts with `sk_test_`)
3. Add them to your `.env` file

### Product and Price Configuration

The integration uses product ID `prod_TLphFe62v2j1Xw` by default. You have two options:

**Option 1: Use inline prices (default)**
- Set `STRIPE_PRODUCT_ID=prod_TLphFe62v2j1Xw` in `.env`
- Prices are created dynamically for each checkout session
- Easiest for development

**Option 2: Use a Price object**
- Create a Price in Stripe Dashboard: https://dashboard.stripe.com/test/products/prod_TLphFe62v2j1Xw
- Set the price to £15.00 (1500 pence)
- Copy the Price ID (starts with `price_`)
- Add `STRIPE_PRICE_ID=price_...` to your `.env`
- The code will prefer the Price ID when available

### Testing Payments

Use these test card numbers:
- **Success**: `4242 4242 4242 4242`
- **Decline**: `4000 0000 0000 0002`
- **Requires authentication**: `4000 0025 0000 3155`
- Use any future expiry date and any 3-digit CVC

### Webhook Setup

**For Development (without webhook verification):**
- Leave `STRIPE_WEBHOOK_SECRET` blank or commented in `.env`
- Webhooks will accept any payload (insecure, development only!)
- Test the flow using the test script: `python backend/test_flow.py`

**For Production (with webhook verification):**

1. Install Stripe CLI: https://stripe.com/docs/stripe-cli
2. Run webhook forwarding:
   ```bash
   stripe listen --forward-to localhost:5000/api/payments/webhook
   ```
3. Copy the webhook secret (starts with `whsec_`) and add to `.env`:
   ```
   STRIPE_WEBHOOK_SECRET=whsec_...
   ```
4. Test payments will now be properly verified

**For Production Deployment:**
- Set up webhook endpoint in Stripe Dashboard: https://dashboard.stripe.com/webhooks
- Add your production webhook URL: `https://yourdomain.com/api/payments/webhook`
- Select event: `checkout.session.completed`
- Copy the signing secret and add to production `.env`

## New Features

### Authentication System
- JWT-based authentication
- Secure password hashing with bcrypt
- Token-based API access
- Protected admin endpoints

### Stripe Integration
- Stripe Checkout for secure payments
- Uses product ID `prod_TLphFe62v2j1Xw` for £15 annual membership
- Automatic membership activation via webhooks
- Customer ID storage for renewal tracking
- Supports both Price objects and inline pricing
- Webhook signature verification for production security

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

