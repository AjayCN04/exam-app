import os
import smtplib
from email.message import EmailMessage


def send_exam_link_email(to_name, to_email, exam_title, link, max_attempts=None):
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", 587))
    username = os.environ["SMTP_USERNAME"]
    password = os.environ["SMTP_PASSWORD"]
    from_name = os.environ.get("SMTP_FROM_NAME", "Exam Team")

    attempts_line = (
        f"You have {max_attempts} attempt(s)." if max_attempts else "Attempts are limited."
    )

    msg = EmailMessage()
    msg["Subject"] = f'Your access link for "{exam_title}"'
    msg["From"] = f"{from_name} <{username}>"
    msg["To"] = to_email
    msg.set_content(
        f"Hi {to_name},\n\n"
        f'You have been granted access to "{exam_title}".\n\n'
        f"Click the link below to begin:\n{link}\n\n"
        f"{attempts_line} Once submitted, your answers are final.\n\n"
        f"Thanks,\n{from_name}\n"
    )

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(msg)
