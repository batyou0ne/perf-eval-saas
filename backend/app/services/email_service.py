import resend

from app.core.config import get_settings

settings = get_settings()


def _dev_stub(message: str) -> None:
    print(f"[dev-stub email] {message}")


def _send(to: str, subject: str, html: str) -> None:
    resend.api_key = settings.resend_api_key
    resend.Emails.send(
        {
            "from": settings.email_from,
            "to": [to],
            "subject": subject,
            "html": html,
        }
    )


def send_invite_email(to: str, invite_link: str, company_name: str) -> None:
    if not settings.resend_api_key:
        _dev_stub(f"Invite for {to}: {invite_link}")
        return

    _send(
        to,
        subject=f"You're invited to join {company_name}",
        html=(
            f"<p>You've been invited to join <strong>{company_name}</strong>.</p>"
            f'<p><a href="{invite_link}">Accept your invite</a></p>'
        ),
    )


def send_password_reset_email(to: str, reset_link: str) -> None:
    if not settings.resend_api_key:
        _dev_stub(f"Password reset for {to}: {reset_link}")
        return

    _send(
        to,
        subject="Reset your password",
        html=(
            "<p>We received a request to reset your password.</p>"
            f'<p><a href="{reset_link}">Reset your password</a></p>'
            "<p>If you didn't request this, you can safely ignore this email.</p>"
        ),
    )
