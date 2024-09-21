import os

from fastapi_jwt_auth import AuthJWT



@AuthJWT.load_config
def get_config():
    return os.getenv('JWT_SECRET_KEY')
