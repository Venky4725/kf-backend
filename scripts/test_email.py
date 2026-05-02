#!/usr/bin/env python3
"""
Quick CLI to test SMTP / Outlook email delivery.

Usage:
    cd backend
    source .venv/bin/activate
    python scripts/test_email.py recipient@example.com
"""
import sys
import os

# allow running from anywhere
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.services.notifier import _send_smtp, _smtp_configured


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_email.py <recipient_email>")
        sys.exit(1)

    to = sys.argv[1]

    print("=" * 60)
    print("SMTP Configuration:")
    print(f"  HOST:     {settings.SMTP_HOST}")
    print(f"  PORT:     {settings.SMTP_PORT}")
    print(f"  USER:     {settings.SMTP_USER}")
    print(f"  USE_TLS:  {settings.SMTP_USE_TLS}")
    print(f"  USE_SSL:  {settings.SMTP_USE_SSL}")
    print(f"  FROM:     {settings.EMAIL_FROM or settings.SMTP_USER}")
    print(f"  Configured? {'YES ✓' if _smtp_configured() else 'NO ✗ (will fall back to logging)'}")
    print("=" * 60)
    print(f"\nSending test email to: {to}\n")

    ok = _send_smtp(
        to_email=to,
        subject="Knowledge Factory — SMTP test",
        text_body=(
            "Hello!\n\n"
            "This is a test message from your Knowledge Factory backend.\n"
            "If you can read this, SMTP is configured correctly. 🎉\n"
        ),
        html_body=(
            "<h2 style='color:#16BAAD'>SMTP Test ✅</h2>"
            "<p>Hello! This is a <b>test message</b> from your Knowledge Factory backend.</p>"
            "<p>If you can read this in your inbox, SMTP is wired up correctly. 🎉</p>"
        ),
    )

    if ok:
        print("✅ Email sent successfully — check your inbox (and spam folder).")
    else:
        print("❌ Failed to send. See log above for the SMTP error.")
        print("\nCommon causes:")
        print("  • SMTP_PASSWORD is wrong")
        print("  • Account has MFA — you need an APP PASSWORD, not your normal password")
        print("  • SMTP AUTH is disabled on your tenant (ask IT to enable 'Authenticated SMTP')")
        print("  • Firewall blocking port 587")


if __name__ == "__main__":
    main()
