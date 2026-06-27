import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import encoders
from pathlib import Path


def send_detection_email(settings, class_name, confidence, timestamp, location, attachment_path):
    sender = settings.get("email_address") or ""
    password = settings.get("email_password") or ""
    recipient = settings.get("email_to") or sender
    smtp_server = settings.get("smtp_server") or "smtp.gmail.com"
    smtp_port = int(settings.get("smtp_port") or 587)

    if not sender or not password or not recipient:
        return False

    message = MIMEMultipart()
    message["From"] = sender
    message["To"] = recipient
    message["Subject"] = "UAV Detection Alert"
    body = (
        f"Object Name: {class_name}\n"
        f"Confidence: {confidence:.2f}\n"
        f"Date/Time: {timestamp}\n"
        f"Location: {location}\n"
    )
    message.attach(MIMEText(body, "plain"))

    path = Path(attachment_path)
    if path.exists():
        part = MIMEBase("application", "octet-stream")
        part.set_payload(path.read_bytes())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={path.name}")
        message.attach(part)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender, password)
        server.send_message(message)
    return True
