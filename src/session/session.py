from starlette.requests import Request

from src.domains.base.models import current_user_var
from src.domains.token.functions import get_token_data
from src.domains.token.models import AccessTokenData


async def set_session(request: Request):
    # Get user information from the dependency
    auth_header = request.headers.get('Authorization')
    if auth_header:
        # Extract the token part after "Bearer "
        token = auth_header.split(" ")[1]
        token_data: AccessTokenData = get_token_data(token)
        # Set the user in the context variable
        current_user_var.set(token_data)
    else:
        current_user_var.set(AccessTokenData())
