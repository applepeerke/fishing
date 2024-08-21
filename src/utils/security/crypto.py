

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
import random

import bcrypt


def get_hashed_password(password: str) -> str:
    # Generate a salt and hash the password with the salt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_password.decode('utf-8')


def verify_password(plain_text: str, hashed_password: str) -> bool:
    # Compare the plain password with the hashed password
    try:
        return bcrypt.checkpw(plain_text.encode('utf-8'), hashed_password.encode('utf-8'))
    except (ValueError, AttributeError):
        return False


def get_otp_as_number() -> int:
    return random.SystemRandom().randint(10000, 99999)
