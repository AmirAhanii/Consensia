import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


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