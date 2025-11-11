from flask import Blueprint, request, jsonify, current_app
import logging
import smtplib
from email.message import EmailMessage
import os
from mailchimp import subscribe_to_newsletter, is_mailchimp_configured

contact_bp = Blueprint("contact_api", __name__, url_prefix="/api")


def _get_contact_recipient():
    """
    Resolve contact recipient email.

    Order of precedence:
    1. CONTACT_RECIPIENT in environment
    2. MAIL_DEFAULT_SENDER (if configured)
    3. Fallback hard-coded club address
    """
    return (
        os.environ.get("CONTACT_RECIPIENT")
        or os.environ.get("MAIL_DEFAULT_SENDER")
        or "info@wovcc.co.uk"
    )


def _send_email_smtp(subject: str, body: str, reply_to: str = None):
    """
    Minimal SMTP-based sender using environment for configuration.
    Expects:
      - SMTP_HOST
      - SMTP_PORT (optional, default 587)
      - SMTP_USERNAME
      - SMTP_PASSWORD
      - SMTP_USE_TLS (optional, default true)
    """
    host = os.environ.get("SMTP_HOST")
    username = os.environ.get("SMTP_USERNAME")
    password = os.environ.get("SMTP_PASSWORD")

    if not host or not username or not password:
        current_app.logger.error(
            "Contact API: SMTP not configured (SMTP_HOST/SMTP_USERNAME/SMTP_PASSWORD required)"
        )
        raise RuntimeError("Email delivery not configured")

    port = int(os.environ.get("SMTP_PORT", "587"))
    use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

    recipient = _get_contact_recipient()
    sender = os.environ.get("MAIL_DEFAULT_SENDER", username)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = recipient
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)

    if use_tls:

        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(username, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port) as server:
            server.login(username, password)
            server.send_message(msg)


@contact_bp.route("/contact", methods=["POST"])
def submit_contact():
    """
    Handle contact form submissions.

    Expects JSON:
      - name (required)
      - email (required)
      - subject (required)
      - message (required)

    Sends an email to the configured club contact address.
    """
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip()
        subject = (data.get("subject") or "").strip()
        message = (data.get("message") or data.get("content") or "").strip()

        # Security: Sanitize inputs to prevent email header injection
        # Remove newline characters that could be used for header injection
        name = name.replace('\n', '').replace('\r', '')
        email = email.replace('\n', '').replace('\r', '')
        subject = subject.replace('\n', '').replace('\r', '')
        # Message content can have newlines, but sanitize control characters
        message = message.replace('\r\n', '\n').replace('\r', '\n')

        if not name or not email or not subject or not message:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "All fields (name, email, subject, message) are required.",
                    }
                ),
                400,
            )

        recipient = _get_contact_recipient()
        full_subject = f"[WOVCC Contact] {subject}"
        body = (
            f"New contact form submission from WOVCC website:\n\n"
            f"Name: {name}\n"
            f"Email: {email}\n\n"
            f"Subject: {subject}\n\n"
            f"Message:\n{message}\n"
        )

        try:
            _send_email_smtp(full_subject, body, reply_to=email)
        except Exception as send_err:  # noqa: BLE001
            current_app.logger.error(
                "Contact API: Failed to send email: %s", send_err, exc_info=True
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Unable to send message at this time. Please try again later.",
                    }
                ),
                500,
            )

        current_app.logger.info(
            "Contact API: Message from %s <%s> delivered to %s",
            name,
            email,
            recipient,
        )

        return jsonify({"success": True, "message": "Message sent successfully."})
    except Exception as exc:  # noqa: BLE001
        logging.exception("Contact API: Unexpected error handling contact form: %s", exc)
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unexpected error processing your request.",
                }
            ),
            500,
        )


@contact_bp.route("/newsletter/subscribe", methods=["POST"])
def subscribe_newsletter():
    """
    Handle newsletter subscription requests.

    Expects JSON:
      - email (required): Email address to subscribe

    Subscribes the email to the Mailchimp newsletter list.
    """
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip()

        # Security: Sanitize email input
        email = email.replace('\n', '').replace('\r', '')

        if not email:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Email address is required.",
                    }
                ),
                400,
            )

        # Basic email validation
        if '@' not in email or '.' not in email.split('@')[-1]:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Please provide a valid email address.",
                    }
                ),
                400,
            )

        # Check if Mailchimp is configured
        if not is_mailchimp_configured():
            current_app.logger.warning(
                "Newsletter API: Mailchimp not configured, subscription request for %s ignored",
                email
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Newsletter service is not currently available.",
                    }
                ),
                503,
            )

        # Attempt to subscribe
        result = subscribe_to_newsletter(email)

        if result.get('success'):
            current_app.logger.info(
                "Newsletter API: Successfully subscribed %s (already_subscribed: %s)",
                email,
                result.get('already_subscribed', False)
            )
            return jsonify({
                "success": True,
                "message": result.get('message', 'Successfully subscribed to newsletter'),
                "already_subscribed": result.get('already_subscribed', False)
            })
        else:
            current_app.logger.warning(
                "Newsletter API: Failed to subscribe %s - %s",
                email,
                result.get('message', 'Unknown error')
            )
            return (
                jsonify(
                    {
                        "success": False,
                        "error": result.get('message', 'Unable to subscribe at this time.'),
                    }
                ),
                500,
            )

    except Exception as exc:  # noqa: BLE001
        logging.exception("Newsletter API: Unexpected error handling subscription: %s", exc)
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Unexpected error processing your subscription.",
                }
            ),
            500,
        )