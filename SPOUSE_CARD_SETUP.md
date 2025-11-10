# Spouse Card Add-on Implementation

## Overview
This implementation adds a £5 spouse/partner card add-on that can be purchased:
1. **During signup** - Users can optionally add it when joining (£15 + £5 = £20 total)
2. **After signup** - Existing members can purchase it from their members area

## What Was Changed

### Backend Changes

#### 1. Database (`database.py`)
- Added `has_spouse_card` boolean field to `User` model
- Added `include_spouse_card` boolean field to `PendingRegistration` model
- Both fields default to `False`

#### 2. Stripe Configuration (`stripe_config.py`)
- Added environment variables for spouse card product:
  - `STRIPE_SPOUSE_CARD_PRICE_ID` - Price ID for £5 spouse card
  - `STRIPE_SPOUSE_CARD_PRODUCT_ID` - Product ID for spouse card
  - `SPOUSE_CARD_AMOUNT = 500` - £5.00 in pence
- Modified `create_checkout_session()` to accept `include_spouse_card` parameter
- Created new `create_spouse_card_checkout_session()` for standalone purchases
- Both functions add spouse card as additional line item when requested

#### 3. Auth Routes (`routes_api_auth.py`)
- Updated `/auth/pre-register` endpoint to accept `includeSpouseCard` parameter
- Added new `/user/purchase-spouse-card` endpoint for existing members
  - Requires authentication
  - Checks if user already has spouse card
  - Checks if user is active member
  - Creates checkout session for spouse card only

#### 4. Webhook Handler (`routes_api_webhooks.py`)
- Handles `spouse_card_only` purchases for existing members
- Sets `has_spouse_card = True` when spouse card payment completes
- New user creation now includes `has_spouse_card` from pending registration

### Frontend Changes

#### 5. Join Page (`templates/join.html`)
- Added checkbox for spouse card add-on with description
- Added dynamic total price display (£15 or £20)

#### 6. Members Page (`templates/members.html`)
- Added "Add Spouse/Partner Card" section (shown if user doesn't have it)
- Added "Spouse Card Active" status section (shown if user has it)
- Includes purchase button with £5 pricing display

#### 7. JavaScript (`scripts/pages.js`)
- Join page: Updates total price when checkbox changes
- Join page: Passes `includeSpouseCard` to signup function
- Members page: Shows/hides spouse card sections based on user status
- Members page: Handles spouse card purchase button click
- Members page: Shows success/cancel messages after checkout

#### 8. Auth Client (`scripts/auth.js`)
- Updated `signup()` function to accept `includeSpouseCard` parameter
- Passes parameter to `/auth/pre-register` endpoint

## Setup Instructions

### 1. Create Stripe Products

You need to create a Stripe product and price for the spouse card:

#### Option A: Using Stripe Dashboard
1. Go to https://dashboard.stripe.com/products
2. Click "Add Product"
3. Name: "Spouse/Partner Membership Card"
4. Description: "Additional membership card for spouse or partner of existing member"
5. Pricing: £5.00 GBP (one-time payment)
6. Save and copy the Price ID (starts with `price_`)

#### Option B: Using the Stripe CLI
```bash
stripe products create \
  --name "Spouse/Partner Membership Card" \
  --description "Additional membership card for spouse or partner"

stripe prices create \
  --product <PRODUCT_ID_FROM_ABOVE> \
  --unit-amount 500 \
  --currency gbp
```

### 2. Update Environment Variables

Add these to your `.env` file:

```env
# Spouse Card Product Configuration
STRIPE_SPOUSE_CARD_PRICE_ID=price_xxxxxxxxxxxxx
STRIPE_SPOUSE_CARD_PRODUCT_ID=prod_xxxxxxxxxxxxx
```

You only need `STRIPE_SPOUSE_CARD_PRICE_ID` if you created a price. The product ID is optional but can be used if you want to create prices dynamically.

### 3. Update Database Schema

Run these SQL commands to add the new columns:

```sql
-- Add has_spouse_card to users table
ALTER TABLE users ADD COLUMN has_spouse_card BOOLEAN DEFAULT FALSE;

-- Add include_spouse_card to pending_registrations table
ALTER TABLE pending_registrations ADD COLUMN include_spouse_card BOOLEAN DEFAULT FALSE;
```

Or if you're using SQLAlchemy migrations, the changes will be applied automatically on next migration.

### 4. Test the Implementation

#### Test Signup Flow with Add-on:
1. Go to `/join`
2. Fill in registration form
3. Check "Add spouse/partner card (+£5)"
4. Verify total shows £20
5. Complete checkout
6. After activation, verify `has_spouse_card` is `True` in database

#### Test Standalone Purchase:
1. Login as existing member without spouse card
2. Go to `/members`
3. Verify "Add Spouse/Partner Card" section is visible
4. Click "Purchase Now"
5. Complete checkout
6. Verify redirect back to members page with success message
7. Verify `has_spouse_card` is now `True`
8. Verify section changed to "Spouse Card Active"

#### Test Edge Cases:
1. Try to purchase spouse card when already owned (should show error)
2. Try to purchase as non-member (should show error)
3. Cancel checkout (should return to appropriate page with cancel message)

## User Flow Diagrams

### New Member with Spouse Card
```
User visits /join
  → Fills form + checks spouse card box
  → Sees £20 total
  → Clicks "Continue to Payment"
  → Redirected to Stripe (£15 membership + £5 spouse card)
  → Completes payment
  → Redirected to /join/activate
  → Account created with has_spouse_card=True
  → Logged in and redirected to /members
```

### Existing Member Adds Spouse Card
```
User logs into /members
  → Sees "Add Spouse/Partner Card" section
  → Clicks "Purchase Now"
  → Redirected to Stripe (£5 spouse card only)
  → Completes payment
  → Redirected to /members?spouse_card=success
  → Success message shown
  → Section changes to "Spouse Card Active"
```

## Stripe Webhook Events

The webhook handler (`/api/payments/webhook`) processes these events:

### `checkout.session.completed`
- Checks `payment_status === 'paid'`
- If `metadata.spouse_card_only === 'true'`:
  - Updates existing user's `has_spouse_card = True`
- If `metadata.pending_id` exists:
  - Creates new user account
  - Sets `has_spouse_card` based on pending registration
  - Deletes pending registration

## Security Considerations

1. **Authentication Required**: Spouse card purchase endpoint requires valid JWT token
2. **Active Member Check**: Validates user is active member before allowing purchase
3. **Duplicate Prevention**: Checks if user already has spouse card
4. **Webhook Verification**: Stripe signatures verified on webhooks (if `STRIPE_WEBHOOK_SECRET` set)
5. **Metadata Validation**: User ID in webhook metadata verified against database

## Pricing Summary

- **New Membership**: £15
- **New Membership + Spouse Card**: £20
- **Spouse Card Add-on (for existing members)**: £5
- **Membership Renewal**: £10 (done in-person at club tills)

## Collection Process

Physical cards are collected at the club within 7 days, as stated in the UI.

## Future Enhancements

Potential improvements:
1. Add email notification when spouse card is ready for collection
2. Allow specifying spouse name during purchase
3. Track spouse card expiry separately
4. Add ability to renew spouse card independently
5. Admin interface to mark cards as "collected"
