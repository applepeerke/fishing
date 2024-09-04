import os.path
import smtplib

# Import the email modules we'll need
from email.mime.text import MIMEText

from src.utils.functions import is_debug_mode


def send_mail(template_path, subject: str, from_mail_address: str, to_mail_addresses: list, substitutions: dict):
    """
    Credits: https://stackoverflow.com/questions/6270782/how-to-send-an-email-with-python
    """
    if not os.path.isfile(template_path):
        raise ValueError(f'Template "{template_path}" does not exist.')
    required_input('Subject', subject)
    required_input('From', from_mail_address)
    required_input('To', to_mail_addresses)

    with open(template_path, 'r') as fp:
        text = fp.read()
    for code, value in substitutions.items():
        text = text.replace(code, str(value))

    # Create a text/plain message
    msg = MIMEText(text)
    # me == the sender's email address
    # you == the recipient's email address
    msg['Subject'] = subject
    msg['From'] = from_mail_address
    msg['To'] = to_mail_addresses[0]

    # Send the message via our own SMTP server, but don't include the envelope header.
    smtp = os.getenv('SMTP') if os.getenv('SMTP_ACTIVATED') == 'True' else 'localhost'
    s = smtplib.SMTP(smtp)
    s.sendmail(from_mail_address, to_mail_addresses, msg.as_string())
    s.quit()


def required_input(name, value):
    if not value:
        raise ValueError(f'Input for "{name}" is required')