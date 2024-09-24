import os
from typing import cast

import uvicorn as uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.services.test.create_db.api import fake_user_login
from src.domains.entities.fish.api import fish
from src.domains.entities.fisherman.api import fisherman
from src.domains.entities.fishingwater.api import fishingwater
from src.domains.login.acl.api import acl
from src.domains.login.login.api import login_logout
from src.domains.login.login.api import login_register, login_login_with_credentials, login_acknowledge
from src.domains.login.password.api import password_verify, password_forgot, password_change, password_hash
from src.domains.login.role.api import role
from src.domains.login.scope.api import scope
from src.domains.login.user.api import user
from src.middleware import add_process_time_header, auto_token_refresh, add_log_entry
from src.services.catch.api import catch
from src.services.test.populate_fishing.api import fake_fishing_data

load_dotenv()
env = os.getenv('ENV')
origins = os.getenv('CORS_ORIGINS')
os.environ['DATABASE_URI'] = os.getenv(f'DATABASE_URI_{env}')


app = FastAPI(openapi_url="/openapi.json", docs_url="/docs", root_path=os.getenv('API_V1_PREFIX'))


# Add routes
app.include_router(fake_user_login, prefix='/test/login', tags=['Test'])
app.include_router(fake_fishing_data, prefix='/test/populate_db', tags=['Test'])
# - Services
app.include_router(catch, prefix='/fish/catch', tags=['Services'])
# - Login
app.include_router(login_register, prefix='/login/register', tags=['Login'])
app.include_router(login_acknowledge, prefix='/login/acknowledge', tags=['Login'])
app.include_router(login_login_with_credentials, prefix='/login', tags=['Login'])
# - Logout
app.include_router(login_logout, prefix='/logout', tags=['Logout'])
# - Password
app.include_router(password_change, prefix='/password/change', tags=['Login'])
app.include_router(password_forgot, prefix='/password/forgot', tags=['Login'])
# - CRUD
app.include_router(user, prefix='/user', tags=['User'])
app.include_router(role, prefix='/role', tags=['Role'])
app.include_router(acl, prefix='/acl', tags=['ACL'])
app.include_router(scope, prefix='/scope', tags=['Scope'])
app.include_router(fishingwater, prefix='/fishingwater', tags=['Fishing water'])
app.include_router(fisherman, prefix='/fisherman', tags=['Fisherman'])
app.include_router(fish, prefix='/fish', tags=['Fish'])
# - Email/Password hashing (internal)
app.include_router(password_hash, prefix='/encrypt', tags=['Hash (internal)'])
app.include_router(password_verify, prefix='/encrypt/verify', tags=['Hash (internal)'])

# Add middleware
app.add_middleware(cast('_MiddlewareClass', BaseHTTPMiddleware), dispatch=auto_token_refresh)
app.add_middleware(cast('_MiddlewareClass', BaseHTTPMiddleware), dispatch=add_process_time_header)
app.add_middleware(cast('_MiddlewareClass', BaseHTTPMiddleware), dispatch=add_log_entry)
app.add_middleware(cast('_MiddlewareClass', CORSMiddleware), allow_origins=origins, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

if __name__ == '__main__':
    uvicorn.run("main:app", port=8085, host="0.0.0.0", reload=False)
