import os

import uvicorn as uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Depends

from src.domains.role.api import role
from src.domains.token.functions import has_access
from src.domains.fishingwater.api import fishingwater
from src.domains.login.api import login_register, login_login, login_acknowledge
from src.domains.password.api import password_verify, password_forgot, password_change, password_hash
from src.domains.user.api import user
from src.utils.functions import is_debug_mode

load_dotenv()
env = os.getenv('ENV')
os.environ['DATABASE_URI'] = os.getenv(f'DATABASE_URI_{env}')

AUTH = None if is_debug_mode() else [Depends(has_access)]

app = FastAPI(openapi_url="/openapi.json", docs_url="/docs", root_path=os.getenv('API_V1_PREFIX'))

# Login
app.include_router(login_register, prefix='/login/register', tags=['Login'])
app.include_router(login_acknowledge, prefix='/login/acknowledge', tags=['Login'])
app.include_router(login_login, prefix='/login', tags=['Login'])
# Password
app.include_router(password_change, prefix='/password/change', tags=['Login'])
app.include_router(password_forgot, prefix='/password/forgot', tags=['Login'])
# CRUD
app.include_router(user, prefix='/user', tags=['User'], dependencies=AUTH)  # Creating/deleting user is not by user
app.include_router(role, prefix='/role', tags=['Role'], dependencies=AUTH)  # Creating/deleting user is not by user
app.include_router(fishingwater, prefix='/fishingwater', tags=['Fishing water'], dependencies=AUTH)
# Email/Password hashing (internal)
app.include_router(password_hash, prefix='/encrypt', tags=['Hash (internal)'])
app.include_router(password_verify, prefix='/encrypt/verify', tags=['Hash (internal)'])


if __name__ == '__main__':
    uvicorn.run("main:app", port=8085, host="0.0.0.0", reload=False)
