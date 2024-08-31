import os
import datetime

from fastapi import HTTPException
from pydantic import BaseModel
from starlette import status

from src.domains.user.functions import is_valid_password, send_otp
from src.domains.user.models import User, UserRead, UserStatus
from src.utils.db import crud
from src.utils.functions import get_otp_expiration, get_password_expiration
from src.utils.security.crypto import verify_password, get_random_password, get_hashed_password

