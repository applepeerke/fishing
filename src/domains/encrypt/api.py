from fastapi import APIRouter

from src.domains.encrypt.models import Password, PasswordEncrypted
from src.general.models import StatusResponse, get_authorization_response
from src.utils.security.crypto import get_hashed_password, verify_password

password = APIRouter()
validate = APIRouter()


@password.post('/', response_model=PasswordEncrypted)
def encrypt_password(payload: Password):
    encrypted_text = get_hashed_password(payload.plain_text.get_secret_value())
    return PasswordEncrypted(encrypted_text=encrypted_text)


@validate.post('/', response_model=StatusResponse)
def validate_password(payload: Password):
    success = verify_password(
        payload.plain_text.get_secret_value(),
        payload.encrypted_text
    )
    return get_authorization_response(success, 'password')
