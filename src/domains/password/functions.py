from src.domains.password.models import ChangePassword
from src.utils.security.crypto import verify_hash, is_valid_password


def validate_new_password(credentials: ChangePassword, old_password_hashed=None) -> str | None:
    """ Change password extra validation """
    detail = None
    new_password_plain_text = credentials.new_password.get_secret_value()
    new_password_repeated_plain_text = credentials.new_password_repeated.get_secret_value()
    # a. New password is required.
    if not new_password_plain_text:
        detail = f'New password is required.'
    # b. New password repetition must be the same.
    if not detail and not (new_password_plain_text == new_password_repeated_plain_text):
        detail = f'New password must be the same as the repeated one.'
    # c. New password must differ from old one.
    if not detail and old_password_hashed and verify_hash(new_password_plain_text, old_password_hashed):
        detail = f'New password must differ from the old one.'
    # d. New password must be valid.
    if not detail and not is_valid_password(new_password_plain_text):
        detail = f'The password is not valid.'
    return detail
