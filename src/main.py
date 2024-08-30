import os

import uvicorn as uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from src.domains.authentication.api import token
from src.domains.fishingwater.api import fishingwater
from src.domains.login.api import login_register, password, password_validate, login_login, \
    login_password_forgot, login_password_set, login_activate
from src.domains.systemvalue.api import systemvalue
from src.domains.user.api import user

load_dotenv()
env = os.getenv('ENV')
os.environ['DATABASE_URI'] = os.getenv(f'DATABASE_URI_{env}')

app = FastAPI(openapi_url="/openapi.json", docs_url="/docs", root_path=os.getenv('API_V1_PREFIX'))

# CRUD
app.include_router(fishingwater, prefix='/fishingwater', tags=['Fishing water'])
app.include_router(user, prefix='/user', tags=['User'])
app.include_router(systemvalue, prefix='/systemvalue', tags=['System value'])
# Login
app.include_router(login_register, prefix='/login/register', tags=['Login - Send password'])
app.include_router(login_activate, prefix='/login/activate', tags=['Login - Activate user'])
app.include_router(login_login, prefix='/login/login', tags=['Login'])
# Password
app.include_router(login_password_set, prefix='/password/set', tags=['Password - Set'])
app.include_router(login_password_forgot, prefix='/password/forgot', tags=['Password - Forgot'])
# Password (internal)
app.include_router(password, prefix='/encrypt', tags=['Encrypt'])
app.include_router(password_validate, prefix='/encrypt/verify', tags=['Encrypt - verify'])

# Access token
app.include_router(token, prefix='/token', tags=['Token'])


if __name__ == '__main__':
    uvicorn.run("main:app", port=8085, host="0.0.0.0", reload=False)
