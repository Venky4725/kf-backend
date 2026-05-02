"""
Email notifier.

If SMTP settings are configured (SMTP_HOST + SMTP_USER + SMTP_PASSWORD), real
emails are sent (Outlook / Office 365 / Gmail / SendGrid / etc.).

Otherwise, in dev, activation/reset URLs are simply logged to the server console.
"""
import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from typing import Optional

from app.core.config import settings

logger = logging.getLogger("notifier")
logger.setLevel(logging.INFO)


# ---------- URL helpers ----------
def _activation_url(token: str) -> str:
    return f"{settings.FRONTEND_URL}/set-password?token={token}"


def _reset_url(token: str) -> str:
    return f"{settings.FRONTEND_URL}/reset-password?token={token}"


# ---------- Low-level SMTP sender ----------
def _smtp_configured() -> bool:
    return bool(settings.SMTP_HOST and settings.SMTP_USER and settings.SMTP_PASSWORD)


def _send_smtp(*, to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """Send an email via SMTP. Returns True on success, False on failure."""
    if not _smtp_configured():
        return False

    from_addr = settings.EMAIL_FROM or settings.SMTP_USER
    from_name = settings.EMAIL_FROM_NAME or "Knowledge Factory"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((from_name, from_addr))
    msg["To"] = to_email
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    try:
        if settings.SMTP_USE_SSL:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context, timeout=20) as server:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
                server.ehlo()
                if settings.SMTP_USE_TLS:
                    context = ssl.create_default_context()
                    server.starttls(context=context)
                    server.ehlo()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
        logger.info(f"[EMAIL SENT] to={to_email} subject={subject!r}")
        return True
    except Exception as e:
        logger.error(f"[EMAIL FAILED] to={to_email} subject={subject!r} err={e}")
        return False


# ---------- HTML templates ----------
def _wrap_html(title: str, intro: str, button_label: str, button_url: str, footer: str = "") -> str:
    return f"""\
<!DOCTYPE html>
<html>
  <body style="font-family: Arial, Helvetica, sans-serif; background:#f4f6f9; margin:0; padding:24px;">
    <table align="center" width="600" cellpadding="0" cellspacing="0"
           style="background:#ffffff; border-radius:12px; box-shadow:0 4px 14px rgba(0,0,0,0.08); overflow:hidden;">
      <tr>
        <td style="background:linear-gradient(135deg,#16BAAD,#063342); padding:24px 28px; color:#ffffff;">
          <div style="font-size:22px; font-weight:bold;">🌊 CoastalSeven Knowledge Factory</div>
          <div style="font-size:13px; opacity:.9; margin-top:4px;">{title}</div>
        </td>
      </tr>
      <tr>
        <td style="padding:28px;">
          <p style="font-size:15px; color:#1f2937; line-height:1.55; margin:0 0 18px 0;">{intro}</p>
          <p style="text-align:center; margin:24px 0;">
            <a href="{button_url}" target="_blank"
               style="background:#16BAAD; color:#ffffff; text-decoration:none;
                      padding:12px 28px; border-radius:8px; font-weight:bold;
                      display:inline-block;">
              {button_label}
            </a>
          </p>
          <p style="font-size:12px; color:#64748b; line-height:1.5; margin:16px 0 0 0;">
            Or copy &amp; paste this link into your browser:<br/>
            <span style="word-break:break-all; color:#0f766e;">{button_url}</span>
          </p>
          {f'<p style="font-size:12px; color:#64748b; margin-top:18px;">{footer}</p>' if footer else ''}
        </td>
      </tr>
      <tr>
        <td style="background:#f1f5f9; padding:14px 28px; font-size:11px; color:#64748b; text-align:center;">
          You received this email from Knowledge Factory. If you didn't expect it, you can ignore it.
        </td>
      </tr>
    </table>
  </body>
</html>
"""


# ---------- Public API ----------
def send_activation_email(*, to_email: str, name: str, token: str) -> None:
    url = _activation_url(token)
    subject = "Activate your Knowledge Factory account"
    text_body = (
        f"Hi {name},\n\n"
        f"Welcome to Knowledge Factory! Please set your password to activate your account:\n\n"
        f"{url}\n\n"
        f"This link will expire soon. If you didn't expect this email, please ignore it.\n"
    )
    html_body = _wrap_html(
        title="Activate your account",
        intro=f"Hi <b>{name}</b>,<br/><br/>Welcome to Knowledge Factory! Click the button below to set your password and activate your account.",
        button_label="Set My Password",
        button_url=url,
        footer="This link will expire in a few hours for your security.",
    )

    sent = _send_smtp(to_email=to_email, subject=subject, html_body=html_body, text_body=text_body)
    if not sent:
        # dev-mode fallback
        logger.info("=" * 70)
        logger.info(f"[ACTIVATION EMAIL — DEV MODE] to={to_email} name={name}")
        logger.info(f"  Set password: {url}")
        logger.info("  (Configure SMTP_HOST/SMTP_USER/SMTP_PASSWORD in .env to send real emails)")
        logger.info("=" * 70)


def send_reset_email(*, to_email: str, name: str, token: str) -> None:
    url = _reset_url(token)
    subject = "Reset your Knowledge Factory password"
    text_body = (
        f"Hi {name},\n\n"
        f"We received a request to reset your password. Click the link below to set a new one:\n\n"
        f"{url}\n\n"
        f"If you didn't request a password reset, you can safely ignore this email.\n"
    )
    html_body = _wrap_html(
        title="Password reset request",
        intro=f"Hi <b>{name}</b>,<br/><br/>We received a request to reset your password. Click the button below to choose a new one.",
        button_label="Reset My Password",
        button_url=url,
        footer="If you didn't request this, you can safely ignore this email.",
    )

    sent = _send_smtp(to_email=to_email, subject=subject, html_body=html_body, text_body=text_body)
    if not sent:
        logger.info("=" * 70)
        logger.info(f"[PASSWORD RESET — DEV MODE] to={to_email} name={name}")
        logger.info(f"  Reset link: {url}")
        logger.info("  (Configure SMTP_HOST/SMTP_USER/SMTP_PASSWORD in .env to send real emails)")
        logger.info("=" * 70)
