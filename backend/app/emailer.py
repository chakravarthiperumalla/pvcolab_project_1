import logging
import re
import smtplib
from email.message import EmailMessage

from .config import settings

log = logging.getLogger(__name__)


def email_enabled() -> bool:
    return bool(settings.smtp_host)


def send_roadmap_email(to: str, topic: str, duration: int, roadmap_id: int, pdf_bytes: bytes) -> None:
    """Send the finished handbook as a PDF attachment. Raises if SMTP is not configured."""
    if not email_enabled():
        raise RuntimeError("Email is not configured on the server")
    msg = EmailMessage()
    msg["Subject"] = f"Your {topic} learning handbook is ready"
    msg["From"] = settings.smtp_from or settings.smtp_user
    msg["To"] = to
    link = f"{settings.frontend_url.rstrip('/')}/roadmaps/{roadmap_id}"
    msg.set_content(
        f'Hi,\n\nYour {duration}-day learning roadmap for "{topic}" is ready.\n'
        f"Read it online (and track your progress): {link}\n"
        f"A PDF copy is attached.\n\nHappy learning!"
    )
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", topic).strip("_") or "roadmap"
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=f"{filename}.pdf")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)
    log.info("Sent roadmap %s to %s", roadmap_id, to)
