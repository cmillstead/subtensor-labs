"""Email sending via Resend."""

import resend

from engine.core.config import settings
from engine.core.logging import get_logger

log = get_logger(__name__)

_RESET_EMAIL_HTML = """\
<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif;\
 max-width: 480px; margin: 0 auto; padding: 24px;">
  <h2 style="color: #e2e2e9;">Reset your password</h2>
  <p style="color: #a0a0b0;">
    You requested a password reset for your Subtensor Labs account.
  </p>
  <p style="margin: 24px 0;">
    <a href="{reset_url}"
       style="background: #7c3aed; color: white; padding: 12px 24px;\
 border-radius: 6px; text-decoration: none; display: inline-block;">
      Reset Password
    </a>
  </p>
  <p style="color: #a0a0b0; font-size: 14px;">
    This link expires in 1 hour.
  </p>
  <p style="color: #a0a0b0; font-size: 14px;">
    If you didn&#39;t request this, you can safely ignore this email.
  </p>
</div>"""


def send_password_reset_email(to: str, reset_url: str) -> None:
    """Send a password reset email with the given reset URL.

    Configures Resend API key from settings and sends a simple HTML email.
    Logs success/failure without exposing the token or URL.
    """
    resend.api_key = settings.resend_api_key

    resend.Emails.send(
        {
            "from": settings.resend_from_email,
            "to": [to],
            "subject": "Reset your Subtensor Labs password",
            "html": _RESET_EMAIL_HTML.format(reset_url=reset_url),
        }
    )

    log.info("password_reset_email_sent", to_email=to)
