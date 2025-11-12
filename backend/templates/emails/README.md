# Email Templates

This directory contains Jinja2 email templates used by the WOVCC membership system. The templates have been refactored to reduce code duplication and improve maintainability.

## Architecture

### Base Template
- **`base.html`**: The master template containing all common HTML structure and CSS styles
  - Defines the email container, header, content area, and footer
  - Contains all CSS styling in a single location
  - Uses Jinja2 blocks for customization

### Email Templates

All email templates extend `base.html` and override specific blocks:

1. **`welcome_receipt.html`**
   - Welcome email with payment receipt for new members
   - Used by: `EmailConfig.send_welcome_receipt_email()`
   - Shows membership details, payment breakdown, and next steps

2. **`extra_card_receipt.html`**
   - Receipt for additional card purchases
   - Used by: `EmailConfig.send_extra_card_receipt_email()`
   - Simpler receipt focused on the additional card

3. **`welcome.html`**
   - Simple welcome email without payment details
   - Used by: `EmailConfig.send_welcome_email()`
   - Focus on membership benefits

4. **`contact_notification.html`**
   - Admin notification for contact form submissions
   - Used by: `EmailConfig.send_contact_notification()`
   - Shows sender details and message

5. **`password_reset.html`**
   - Password reset email with secure link
   - Used by: `EmailConfig.send_password_reset_email()`
   - Includes security warnings

6. **`weekly_report.html`**
   - Weekly signup report for administrators
   - Used by: `generate_weekly_report_email()` in `signup_logger.py`
   - Displays summary statistics and member details

## Usage

### In Python Code

```python
from flask import render_template

# Render an email template
html_content = render_template(
    'emails/welcome_receipt.html',
    name='John Doe',
    currency_symbol='£',
    amount_paid='50.00',
    has_spouse_card=True,
    membership_expiry='31 December 2025'
)
```

### Creating New Email Templates

1. Create a new `.html` file in this directory
2. Extend the base template:
   ```jinja2
   {% extends "emails/base.html" %}
   ```

3. Override the `header` block for custom header content:
   ```jinja2
   {% block header %}
   <h1 style="color: white;">Your Custom Title</h1>
   <p style="color: white;">Subtitle text</p>
   {% endblock %}
   ```

4. Override the `content` block for the email body:
   ```jinja2
   {% block content %}
   <p>Your email content here...</p>
   {% endblock %}
   ```

5. (Optional) Override the `footer` block for custom footer:
   ```jinja2
   {% block footer %}
   <p>Custom footer content</p>
   {% endblock %}
   ```

## Styling Guidelines

### Available CSS Classes

The base template provides these pre-styled classes:

- **`.greeting`**: Styled greeting text (e.g., "Dear John,")
- **`.success-badge`**: Green success indicator badge
- **`.receipt-box`**: Container for payment receipts
- **`.receipt-title`**: Receipt section header
- **`.receipt-items`**: Container for receipt line items
- **`.receipt-item`**: Individual receipt line
- **`.receipt-total`**: Total amount section
- **`.section-title`**: Section header with underline
- **`.links-grid`**: 2-column grid for link cards
- **`.link-card`**: Styled card for action links
- **`.info-box`**: Blue informational box
- **`.warning`**: Yellow warning box
- **`.button`**: Styled call-to-action button
- **`.badge`**: Small label badge
- **`.badge-yes` / `.badge-no`**: Green/red badge variants

### Inline Styles

Due to email client compatibility, inline styles are used extensively. When adding custom styles:
- Include `color` properties for text elements
- Use `background-color` explicitly for colored sections
- Mobile responsive styles are in `@media` queries in the base template

### Color Palette

- Primary Green: `#1a5f5f` (buttons, headers)
- Dark Green: `#144a4a` (gradients)
- Gold Accent: `#d4a574` (borders, highlights)
- Success Green: `#28a745` (revenue, positive indicators)
- Text: `#1a1a1a` (main text)
- Muted Text: `#6c757d` (secondary text)
- Background: `#f8f9fa` (light gray)

## Benefits of Template-Based Approach

1. **Single Source of Truth**: All CSS is defined once in `base.html`
2. **Easy Updates**: Change styling in one place, affects all emails
3. **Consistency**: All emails share the same design language
4. **Maintainability**: Much easier to read and modify than string concatenation
5. **Testability**: Templates can be rendered and previewed independently
6. **Separation of Concerns**: Design (templates) separated from logic (Python)

## Plain Text Emails

All email methods also generate plain text versions for email clients that don't support HTML. These are created separately in the Python code using f-strings.

## Testing Templates

To test a template render:

```python
from flask import Flask, render_template
app = Flask(__name__)

with app.app_context():
    html = render_template('emails/welcome_receipt.html', 
                          name='Test User',
                          # ... other parameters
                          )
    print(html)
```

## Migration Notes

The refactoring migrated from:
- Large HTML strings embedded in Python code
- Duplicated CSS across multiple functions
- Difficult to maintain and update

To:
- Modular Jinja2 templates
- Centralized styling in base template
- Easy to maintain and extend

All email functionality remains unchanged; only the implementation is improved.
