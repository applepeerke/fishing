"""
# Example usage
plain_text = "my_secure_password"
hashed_password = hash_password(plain_text)

print(f"Plain Password: {plain_password}")
print(f"Hashed Password: {hashed_password}")

# Check the password
is_correct = validate_password(plain_text, hashed_password)
print(f"Password Match: {is_correct}")
"""
import os
import secrets
import string

import bcrypt


def get_salted_hash(password: str) -> str:
    if not password:
        return password
    # Generate a salt and hash the password with the salt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_password.decode('utf-8')


def verify_hash(plain_text: str, hashed_password: str) -> bool:
    # Compare the plain password with the hashed password
    try:
        return bcrypt.checkpw(plain_text.encode('utf-8'), hashed_password.encode('utf-8'))
    except (ValueError, AttributeError):
        return False


def get_random_password() -> str:
    # Random OTP
    chars = string.ascii_letters + string.digits + '@#$%^&*'
    for _ in range(1000):
        password = ''.join(secrets.choice(chars) for _ in range(int(os.getenv('PASSWORD_MINIMUM_LENGTH'))))
        if is_valid_password(password):
            return password
    raise ValueError('No random OTP could be generated.')


def is_valid_password(password) -> bool:
    """ Precondition: pydantic has checked already on type, min_length and max_length """
    # must contain upper, lower, number, special
    d = {}
    for c in str(password):
        if c.islower():
            d['LC'] = True
        elif c.isupper():
            d['UC'] = True
        elif c.isnumeric():
            d['number'] = True
        elif c != ' ':
            d['special'] = True
    return len(d) == 4
