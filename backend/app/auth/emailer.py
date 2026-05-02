import logging
import os
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

# Without this, a bad SMTP_HOST (e.g. localhost copied to Render) blocks until the OS TCP
# timeout (~minutes), and the browser aborts first (e.g. 90s).
def _smtp_socket_timeout_sec() -> float:
    raw = (os.getenv("SMTP_TIMEOUT_SECONDS") or "20").strip()
    try:
        n = float(raw)
    except ValueError:
        return 20.0
    return max(5.0, min(120.0, n))


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

    timeout = _smtp_socket_timeout_sec()
    with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout) as server:
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

    timeout = _smtp_socket_timeout_sec()
    with smtplib.SMTP(smtp_host, smtp_port, timeout=timeout) as server:
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
    Send the verification email when SMTP is fully configured.

    Returns True if an email was sent.

    Returns False if SMTP env is incomplete, or if sending fails (wrong host, auth, timeout).
    In those cases the verification code is logged at WARNING so you can still use /verify-email.
    """
    if not smtp_fully_configured(smtp_host, smtp_user, smtp_password, mail_from):
        sys.stderr.write(
            f"CONSENSIA_MAIL_SKIP verification to={to_email!r} reason=smtp_incomplete\n"
        )
        sys.stderr.flush()
        logger.warning(
            "SMTP not configured (set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, MAIL_FROM). "
            "Verification code for %s: %s",
            to_email,
            verification_code,
        )
        return False
    sys.stderr.write(
        f"CONSENSIA_MAIL_ATTEMPT verification to={to_email!r} host={smtp_host!r} port={smtp_port}\n"
    )
    sys.stderr.flush()
    try:
        send_verification_email(
            smtp_host,
            smtp_port,
            smtp_user,
            smtp_password,
            mail_from,
            to_email,
            verification_code,
        )
        sys.stderr.write(f"CONSENSIA_MAIL_OK verification sent to={to_email!r}\n")
        sys.stderr.flush()
        logger.info("Verification email sent to %s", to_email)
        return True
    except Exception:
        logger.exception("SMTP verification send failed for %s", to_email)
        sys.stderr.write(
            f"CONSENSIA_MAIL_FAIL verification to={to_email!r} (see exception above in logs)\n"
        )
        sys.stderr.flush()
        logger.warning("Verification code for %s (after SMTP failure): %s", to_email, verification_code)
        return False


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
    Send password reset code when SMTP is fully configured.
    Returns True if sent. If SMTP is incomplete or sending fails, logs the code at WARNING and returns False.
    """
    if not smtp_fully_configured(smtp_host, smtp_user, smtp_password, mail_from):
        logger.warning(
            "SMTP not configured. Password reset code for %s: %s",
            to_email,
            reset_code,
        )
        return False
    try:
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
    except Exception:
        logger.exception("SMTP password reset send failed for %s", to_email)
        logger.warning("Password reset code for %s (after SMTP failure): %s", to_email, reset_code)
        return False