"""Email sending: dev-stub fallback when no API key, real Resend call when configured.

RESEND_API_KEY is blank in the test environment (see conftest.py), so an unmocked
call would fail loudly rather than silently costing money or flaking on a network
hiccup. These tests patch resend.Emails.send directly to prove both branches work
without ever reaching the network.
"""

from unittest.mock import MagicMock

from app.services import email_service


def test_send_invite_email_falls_back_to_console_without_api_key(monkeypatch, capsys):
    monkeypatch.setattr(email_service.settings, "resend_api_key", "")
    send = MagicMock()
    monkeypatch.setattr(email_service.resend.Emails, "send", send)

    email_service.send_invite_email("new@example.com", "http://app/accept-invite/tok", "Acme Inc")

    send.assert_not_called()
    assert "new@example.com" in capsys.readouterr().out


def test_send_invite_email_calls_resend_when_api_key_configured(monkeypatch):
    monkeypatch.setattr(email_service.settings, "resend_api_key", "re_test_key")
    monkeypatch.setattr(email_service.settings, "email_from", "noreply@example.com")
    send = MagicMock()
    monkeypatch.setattr(email_service.resend.Emails, "send", send)

    email_service.send_invite_email("new@example.com", "http://app/accept-invite/tok", "Acme Inc")

    send.assert_called_once()
    payload = send.call_args[0][0]
    assert payload["to"] == ["new@example.com"]
    assert payload["from"] == "noreply@example.com"
    assert "Acme Inc" in payload["html"]


def test_send_password_reset_email_falls_back_to_console_without_api_key(monkeypatch, capsys):
    monkeypatch.setattr(email_service.settings, "resend_api_key", "")
    send = MagicMock()
    monkeypatch.setattr(email_service.resend.Emails, "send", send)

    email_service.send_password_reset_email("user@example.com", "http://app/reset-password/tok")

    send.assert_not_called()
    assert "user@example.com" in capsys.readouterr().out


def test_send_password_reset_email_calls_resend_when_api_key_configured(monkeypatch):
    monkeypatch.setattr(email_service.settings, "resend_api_key", "re_test_key")
    send = MagicMock()
    monkeypatch.setattr(email_service.resend.Emails, "send", send)

    email_service.send_password_reset_email("user@example.com", "http://app/reset-password/tok")

    send.assert_called_once()
    payload = send.call_args[0][0]
    assert payload["to"] == ["user@example.com"]
