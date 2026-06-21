"""
IMAP background poller — rezerva ako n8n cloud zataji.

Pokretanje (standalone, van uvicorn-a):
    python -m app.email_poller

Ili integriši u lifespan (main.py) sa asyncio.create_task.
Primarni kanal je n8n; ovo je fallback za lokalni demo bez interneta.
"""
from __future__ import annotations

import asyncio
import email
import imaplib
import logging
import smtplib
import time
from email.mime.text import MIMEText

from .agent import run_agent
from .config import settings

log = logging.getLogger(__name__)

SUBJECT_KEYWORDS = [
    "upit", "ponuda", "cijena", "dostava", "garancija",
    "kako", "imate li", "trebam", "kupiti", "narudžba",
]

POLL_INTERVAL = 60  # sekundi


def _matches_keywords(subject: str) -> bool:
    s = subject.lower()
    return any(kw in s for kw in SUBJECT_KEYWORDS)


def _fetch_unseen(mail: imaplib.IMAP4_SSL) -> list[tuple[str, str, str, str]]:
    """Vraća listu (uid, from, subject, body) nepročitanih emailova."""
    mail.select("INBOX")
    _, data = mail.uid("search", None, "UNSEEN")
    uids = data[0].split() if data[0] else []

    results = []
    for uid in uids:
        _, msg_data = mail.uid("fetch", uid, "(RFC822)")
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)

        sender = msg.get("From", "")
        subject = msg.get("Subject", "")

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode("utf-8", errors="replace")
                    break
        else:
            body = msg.get_payload(decode=True).decode("utf-8", errors="replace")

        results.append((uid.decode(), sender, subject, body[:2000]))

    return results


def _send_reply(to_addr: str, original_subject: str, reply_text: str) -> None:
    msg = MIMEText(reply_text, "plain", "utf-8")
    msg["Subject"] = f"Re: {original_subject}"
    msg["From"] = settings.smtp_user or ""
    msg["To"] = to_addr

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.sendmail(settings.smtp_user, to_addr, msg.as_string())


def _mark_seen(mail: imaplib.IMAP4_SSL, uid: str) -> None:
    mail.uid("store", uid, "+FLAGS", "\\Seen")


def poll_once() -> int:
    """Jedna iteracija pollinga. Vraća broj obrađenih emailova."""
    if not all([settings.imap_host, settings.imap_user, settings.imap_password]):
        log.warning("IMAP nije konfigurisan — preskačem poll.")
        return 0

    processed = 0
    try:
        mail = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
        mail.login(settings.imap_user, settings.imap_password)

        messages = _fetch_unseen(mail)
        for uid, sender, subject, body in messages:
            if not _matches_keywords(subject):
                log.debug("Preskačem email (subject ne odgovara): %s", subject)
                _mark_seen(mail, uid)
                continue

            log.info("Obrađujem email od %s: %s", sender, subject)
            message = f"Email od: {sender}\nPredmet: {subject}\n\n{body}"
            result = run_agent(
                [{"role": "user", "content": message}],
                channel="email",
            )

            if settings.smtp_host and settings.smtp_user:
                _send_reply(sender, subject, result["reply"])
                log.info("Reply poslan na %s (escalated=%s)", sender, result["escalated"])
            else:
                log.info("SMTP nije konfigurisan — reply nije poslan. Sadržaj:\n%s", result["reply"])

            _mark_seen(mail, uid)
            processed += 1

        mail.logout()
    except Exception as exc:
        log.exception("IMAP poll greška: %s", exc)

    return processed


async def run_poller() -> None:
    """Async petlja za pokretanje unutar uvicorn lifespan-a."""
    log.info("Email poller startao (interval=%ds).", POLL_INTERVAL)
    while True:
        n = poll_once()
        if n:
            log.info("Obrađeno %d emailova.", n)
        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    log.info("Pokretanje standalone email pollera...")
    while True:
        poll_once()
        time.sleep(POLL_INTERVAL)
