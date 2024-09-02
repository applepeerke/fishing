import datetime
import os

from dateutil.relativedelta import relativedelta

from src.utils.tests.constants import PAYLOAD


def is_debug_mode() -> bool:
    return os.getenv('DEBUG') == 'True' and os.getenv('ENV') == 'DEV'


def find_filename_path(file_name) -> str:
    """
    Return file paths matching the specified file type in the specified base directory (recursively).
    """
    if not file_name:
        return ''
    app_root = os.getenv("APP_ROOT")
    walk_path = os.path.abspath(os.curdir)
    # Try to find app root
    if app_root in walk_path and walk_path.count(app_root) == 1:
        p = walk_path.find(app_root) + len(app_root)
        walk_path = walk_path[:p]
    # Walk from app root
    for path, dirs, files in os.walk(walk_path):
        for filename in files:
            if filename == file_name:
                return os.path.join(path, filename)


def get_otp_expiration():
    return (datetime.datetime.now(datetime.timezone.utc) +
            datetime.timedelta(minutes=int(os.getenv('OTP_EXPIRATION_MINUTES', 10))))


def get_password_expiration():
    return (datetime.datetime.now(datetime.timezone.utc) +
            relativedelta(months=int(os.getenv('PASSWORD_EXPIRATION_MONTHS', 10))))


def get_pk(fixture, pk_name):
    return fixture.get(PAYLOAD, {}).get(pk_name)
