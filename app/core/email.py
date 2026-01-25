import smtplib
from email.message import EmailMessage
from app.core.config import settings

def send_reset_email(to_email: str, token: str) -> None:
    # เปิดใช้งานเฉพาะ production เท่านั้น
    if settings.ENV != "prod":
        return

    # ตรวจว่าค่าจำเป็นครบ
    required = [
        settings.SMTP_HOST, settings.SMTP_PORT,
        settings.SMTP_USERNAME, settings.SMTP_PASSWORD,
        settings.SMTP_FROM, settings.FRONTEND_RESET_URL
    ]
    if any(v in (None, "", 0) for v in required):
        raise RuntimeError("SMTP settings are not configured for production")

    reset_link = f"{settings.FRONTEND_RESET_URL}?token={token}"

    msg = EmailMessage()
    msg["Subject"] = "Reset your password"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to_email
    msg.set_content(
        "You requested a password reset.\n\n"
        f"Reset link: {reset_link}\n\n"
        "If you did not request this, please ignore this email."
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()

        # เปิดตอนเทส ถ้าอยากเห็น log
        # smtp.set_debuglevel(1)

        smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.send_message(msg)
