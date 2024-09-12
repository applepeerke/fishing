import datetime
import os

from dateutil.relativedelta import relativedelta

from src.utils.tests.constants import PAYLOAD


def is_debug_mode() -> bool:
    return os.getenv('DEBUG') == 'True' and os.getenv('ENV') == 'DEV'


def find_filename_path(file_name, test=True) -> str:
    """
    Return file paths matching the specified file type in the specified base directory (recursively).
    """
    # Validation
    app_name = os.getenv("APP_NAME")
    test_base_name = os.getenv("APP_ROOT_TESTS")
    current_path = os.path.abspath(os.curdir)
    if not file_name or app_name not in current_path:
        return ''

    p = current_path.find(app_name) + len(app_name)
    app_dir = current_path[:p]

    # Try to find in test root "../fishing/tests" or else in app root "../fishing"
    test_dir = os.path.join(app_dir, os.getenv("APP_ROOT_TESTS"))
    if not test or not os.path.isdir(test_dir):
        test = False
    path = test_dir if test else app_dir
    if not os.path.dirname(path):
        return ''

    # Walk from path
    return walk(path, file_name)


def walk(path, find_file_name) -> str:
    for p, dirs, files in os.walk(path):
        for filename in files:
            if filename == find_file_name:
                return os.path.join(p, filename)


def get_otp_expiration():
    return (datetime.datetime.now(datetime.timezone.utc) +
            datetime.timedelta(minutes=int(os.getenv('OTP_EXPIRATION_MINUTES', 10))))


def get_password_expiration():
    return (datetime.datetime.now(datetime.timezone.utc) +
            relativedelta(months=int(os.getenv('PASSWORD_EXPIRATION_MONTHS', 10))))


def get_pk(fixture, pk_name):
    return fixture.get(PAYLOAD, {}).get(pk_name)
