import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def smtp_fully_configured(
    smtp_host: str,
    smtp_user: str,
    smtp_password: str,
    mail_from: str,
) -> bool:
    return bool(smtp_host and smtp_user and smtp_password and mail_from)


def send_verification_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    mail_from: str,
    to_email: str,
    verification_code: str,
) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your Consensia account"
    msg["From"] = mail_from
    msg["To"] = to_email

    html = f"""
    <h2>Welcome to Consensia</h2>
    <p>Your verification code is:</p>
    <h1 style="letter-spacing: 4px;">{verification_code}</h1>
    <p>Enter this code on the verification page to activate your account.</p>
    <p>This code expires in 24 hours.</p>
    """

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, [to_email], msg.as_string())


def send_password_reset_email(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    mail_from: str,
    to_email: str,
    reset_code: str,
) -> None:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Reset your Consensia password"
    msg["From"] = mail_from
    msg["To"] = to_email

    html = f"""
    <h2>Password reset</h2>
    <p>Your password reset code is:</p>
    <h1 style="letter-spacing: 4px;">{reset_code}</h1>
    <p>Enter this code on the reset password page along with your new password.</p>
    <p>This code expires in 24 hours. If you did not request a reset, you can ignore this email.</p>
    """

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, [to_email], msg.as_string())


def send_verification_email_if_configured(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    mail_from: str,
    to_email: str,
    verification_code: str,
) -> bool:
    """
    Send the verification email when SMTP is configured.

    Returns True if an email was sent, False if SMTP env is incomplete (local dev).
    In the False case, the code is logged at WARNING so you can still verify via /verify-email.

    Raises on SMTP misconfiguration that only fails at send time (connection/auth errors).
    """
    if not smtp_fully_configured(smtp_host, smtp_user, smtp_password, mail_from):
        logger.warning(
            "SMTP not configured (set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, MAIL_FROM in backend/.env). "
            "Verification code for %s: %s",
            to_email,
            verification_code,
        )
        return False
    send_verification_email(
        smtp_host,
        smtp_port,
        smtp_user,
        smtp_password,
        mail_from,
        to_email,
        verification_code,
    )
    return True


def send_password_reset_email_if_configured(
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    mail_from: str,
    to_email: str,
    reset_code: str,
) -> bool:
    """
    Send password reset code when SMTP is configured.
    Returns True if sent; if SMTP incomplete, logs code at WARNING and returns False.
    """
    if not smtp_fully_configured(smtp_host, smtp_user, smtp_password, mail_from):
        logger.warning(
            "SMTP not configured. Password reset code for %s: %s",
            to_email,
            reset_code,
        )
        return False
    send_password_reset_email(
        smtp_host,
        smtp_port,
        smtp_user,
        smtp_password,
        mail_from,
        to_email,
        reset_code,
    )
    return True