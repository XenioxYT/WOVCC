from flask import Blueprint, request, jsonify, current_app
import logging
from mailchimp import subscribe_to_newsletter, is_mailchimp_configured
from email_config import EmailConfig

contact_bp = Blueprint("contact_api", __name__, url_prefix="/api")


@contact_bp.route("/contact", methods=["POST"])
def submit_contact():
    """
    Handle contact form submissions.

    Expects JSON:
      - name (required)
      - email (required)
      - subject (required)
      - message (required)
      - phone (optional)

    Sends an email to the configured club contact address.
    """
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip()
        phone = (data.get("phone") or "").strip()
        subject = (data.get("subject") or "").strip()
        message = (data.get("message") or data.get("content") or "").strip()

        # Security: Sanitize inputs to prevent email header injection
        # Remove newline characters that could be used for header injection
        name = name.replace('\n', '').replace('\r', '')
        email = email.replace('\n', '').replace('\r', '')
        phone = phone.replace('\n', '').replace('\r', '')
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

        # Check if email is configured
        if not EmailConfig.is_configured():
            current_app.logger.error("Contact API: Email service not configured")
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Email service is not currently available. Please try again later.",
                    }
                ),
                503,
            )

        # Send email using centralized email configuration
        try:
            success = EmailConfig.send_contact_notification(
                from_name=name,
                from_email=email,
                from_phone=phone if phone else None,
                subject=subject,
                message=message
            )
            
            if not success:
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
                "Contact API: Message from %s <%s> delivered successfully",
                name,
                email,
            )
            
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