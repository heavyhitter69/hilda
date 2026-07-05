"""
plugins/email_integration.py — Email management for Hilda.

Supports IMAP (read) and SMTP (send) for any email provider.
Credentials stored in .env.
"""
from __future__ import annotations

import email
import email.utils
import imaplib
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText



from config.settings import settings
from core.logger import get_logger

log = get_logger(__name__)


def _get_email_config() -> dict[str, str]:
    """Read email configuration from environment."""
    return {
        "imap_host": os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com"),
        "imap_port": int(os.getenv("EMAIL_IMAP_PORT", "993")),
        "smtp_host": os.getenv("EMAIL_SMTP_HOST", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("EMAIL_SMTP_PORT", "587")),
        "address": os.getenv("EMAIL_ADDRESS", ""),
        "password": os.getenv("EMAIL_PASSWORD", ""),  # App password for Gmail
    }


def _is_configured() -> bool:
    cfg = _get_email_config()
    return bool(cfg["address"] and cfg["password"])


def check_email(count: int = 5) -> str:
    """
    Check the inbox and return the latest unread emails.
    Returns a formatted string summary.
    """
    if not _is_configured():
        return "Email is not configured. Add EMAIL_ADDRESS and EMAIL_PASSWORD to your .env file."

    cfg = _get_email_config()
    try:
        mail = imaplib.IMAP4_SSL(cfg["imap_host"], int(cfg["imap_port"]))
        mail.login(cfg["address"], cfg["password"])
        mail.select("INBOX")

        # Search for unread messages
        status, data = mail.search(None, "UNSEEN")
        if status != "OK" or not data[0]:
            mail.logout()
            return "No unread emails."

        ids = data[0].split()
        latest = ids[-count:] if len(ids) > count else ids
        latest.reverse()  # Most recent first

        emails_info = []
        for eid in latest:
            status, msg_data = mail.fetch(eid, "(RFC822)")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            sender = email.utils.parseaddr(msg.get("From", ""))[1] or msg.get("From", "Unknown")
            subject = msg.get("Subject", "No subject")
            date = msg.get("Date", "")

            # Get preview
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        try:
                            body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                        except Exception:
                            pass
                        break
            else:
                try:
                    body = msg.get_payload(decode=True).decode("utf-8", errors="replace")
                except Exception:
                    pass

            preview = body.strip()[:150] if body else ""
            emails_info.append({
                "from": sender,
                "subject": subject,
                "date": date,
                "preview": preview,
            })

        mail.logout()

        if not emails_info:
            return "No unread emails."

        lines = [f"You have {len(ids)} unread email(s). Here are the latest:"]
        for i, e in enumerate(emails_info, 1):
            lines.append(f"\n{i}. From: {e['from']}")
            lines.append(f"   Subject: {e['subject']}")
            if e['preview']:
                lines.append(f"   Preview: {e['preview'][:100]}...")

        return "\n".join(lines)

    except imaplib.IMAP4.error as e:
        log.error("IMAP error: %s", e)
        return f"Email check failed: {e}. Check your credentials."
    except Exception as e:
        log.error("Email check failed: %s", e)
        return f"Could not check email: {e}"


def send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    if not _is_configured():
        return "Email is not configured. Add EMAIL_ADDRESS and EMAIL_PASSWORD to .env."

    cfg = _get_email_config()
    try:
        msg = MIMEMultipart()
        msg["From"] = cfg["address"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(cfg["smtp_host"], int(cfg["smtp_port"])) as server:
            server.starttls()
            server.login(cfg["address"], cfg["password"])
            server.send_message(msg)

        log.info("Email sent to %s: %s", to, subject)
        return f"Email sent to {to} with subject '{subject}'."

    except Exception as e:
        log.error("Send email failed: %s", e)
        return f"Could not send email: {e}"


def search_email(query: str, count: int = 5) -> str:
    """Search emails by subject or body content."""
    if not _is_configured():
        return "Email is not configured."

    cfg = _get_email_config()
    try:
        mail = imaplib.IMAP4_SSL(cfg["imap_host"], int(cfg["imap_port"]))
        mail.login(cfg["address"], cfg["password"])
        mail.select("INBOX")

        # Search by subject
        status, data = mail.search(None, f'(SUBJECT "{query}")')
        if status != "OK" or not data[0]:
            mail.logout()
            return f"No emails found matching '{query}'."

        ids = data[0].split()
        latest = ids[-count:] if len(ids) > count else ids
        latest.reverse()

        results = []
        for eid in latest:
            status, msg_data = mail.fetch(eid, "(RFC822)")
            if status != "OK":
                continue
            msg = email.message_from_bytes(msg_data[0][1])
            sender = email.utils.parseaddr(msg.get("From", ""))[1] or "Unknown"
            subject = msg.get("Subject", "No subject")
            results.append(f"• {subject} (from {sender})")

        mail.logout()
        return f"Found {len(results)} email(s) matching '{query}':\n" + "\n".join(results)

    except Exception as e:
        log.error("Email search failed: %s", e)
        return f"Email search failed: {e}"


def summarize_inbox() -> str:
    """Get an LLM-generated summary of unread emails."""
    raw = check_email(count=10)
    if "not configured" in raw.lower() or "no unread" in raw.lower():
        return raw

    try:
        import ollama
        response = ollama.chat(
            model=settings.OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": "Summarize the user's inbox concisely. Highlight urgent or important items."},
                {"role": "user", "content": f"Here are my unread emails:\n\n{raw}\n\nGive me a brief summary."},
            ],
            options={"temperature": 0.2, "num_predict": 200},
        )
        return response["message"]["content"].strip()
    except Exception:
        return raw
