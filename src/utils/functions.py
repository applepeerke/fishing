import datetime
import os
import random

from dateutil.relativedelta import relativedelta
from src.utils.tests.constants import PAYLOAD

rng = random.SystemRandom()

NAME_CHARS = 'aaaaaabbcddeeeeeeffgghhiiiiijjkkllmmnnnooooooppqrrsssttuuuuuuvvwwxyyz'
NAME_CHARS_LIST = [item for item in NAME_CHARS]


def is_debug_mode() -> bool:
    return os.getenv('DEBUG') == 'True' and os.getenv('ENV') == 'DEV'


def find_dirname_path(dirname) -> str:
    """
    Find and return path to the specified dir name (recursively).
    """
    return walk_for_dirname(get_app_dir(), dirname)


def find_filename_path(file_name, test=True) -> str:
    """
    Return file paths matching the specified file type in the specified base directory (recursively).
    """
    # Validation
    app_dir = get_app_dir()

    # Try to find in test root "../fishing/tests" or else in app root "../fishing"
    test_dir = os.path.join(app_dir, os.getenv("APP_ROOT_TESTS"))
    if not test or not os.path.isdir(test_dir):
        test = False
    path = test_dir if test else app_dir

    # Walk from path
    return walk_for_filename(path, file_name)


def get_app_dir() -> str:
    """
    Return file paths matching the specified file type in the specified base directory (recursively).
    """
    # Validation
    app_name = os.getenv("APP_NAME")
    current_path = os.path.abspath(os.curdir)
    if app_name not in current_path:
        return ''

    p = current_path.find(app_name) + len(app_name)
    return current_path[:p]


def walk_for_filename(path, find_file_name) -> str:
    if not path or not find_file_name:
        return ''
    for p, dirs, files in os.walk(path):
        for filename in files:
            if filename == find_file_name:
                return os.path.join(p, filename)


def walk_for_dirname(path, find_dir_name) -> str:
    for p, dirs, files in os.walk(path):
        for dirname in dirs:
            if dirname == find_dir_name:
                return os.path.join(p, dirname)


def get_otp_expiration():
    return (datetime.datetime.now(datetime.timezone.utc) +
            datetime.timedelta(minutes=int(os.getenv('OTP_EXPIRATION_MINUTES', 10))))


def get_password_expiration():
    return (datetime.datetime.now(datetime.timezone.utc) +
            relativedelta(months=int(os.getenv('PASSWORD_EXPIRATION_MONTHS', 10))))


def get_pk(fixture, pk_name):
    return fixture.get(PAYLOAD, {}).get(pk_name)


def get_random_name(max_length=20) -> str:
    name = []
    for i in range(rng.randint(5, max(5, max_length))):
        name.append(get_random_item(NAME_CHARS_LIST))
    return ''.join(name).title()


def get_random_item(items: list):
    if not items:
        return None
    index = rng.randint(0, len(items) - 1)
    return items[index]


def get_random_index_set(items: list, random_subset_count: int) -> set:
    set_count = len(items)
    if set_count == 0:
        return set()
    if set_count == 1:
        return {0}

    index_set = set()
    count = 0
    while len(index_set) < random_subset_count and count < 1000:
        count += 1
        index_set.add(rng.randint(0, set_count - 1))  # get an index
    return index_set
