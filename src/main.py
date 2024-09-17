import os

import uvicorn as uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.domains.acl.api import acl
from src.domains.fishingwater.api import fishingwater
from src.domains.login.api import login_register, login_login, login_acknowledge
from src.domains.logout.api import login_logout
from src.domains.password.api import password_verify, password_forgot, password_change, password_hash
from src.domains.role.api import role
from src.domains.scope.api import scope
from src.domains.test.populate_db import populate_fake_db
from src.domains.user.api import user
from src.middleware import add_process_time_header, add_db_session
from src.session.session import has_access
from src.utils.functions import is_debug_mode

load_dotenv()
env = os.getenv('ENV')
origins = os.getenv('CORS_ORIGINS')
os.environ['DATABASE_URI'] = os.getenv(f'DATABASE_URI_{env}')

AUTH = None if is_debug_mode() else [Depends(has_access)]

app = FastAPI(openapi_url="/openapi.json", docs_url="/docs", root_path=os.getenv('API_V1_PREFIX'))

# Add routes
app.include_router(populate_fake_db, prefix='/test', tags=['Test'])
# - Login
app.include_router(login_register, prefix='/login/register', tags=['Login'])
app.include_router(login_acknowledge, prefix='/login/acknowledge', tags=['Login'])
app.include_router(login_login, prefix='/login', tags=['Login'])
# - Logout
app.include_router(login_logout, prefix='/logout', tags=['Logout'])
# - Password
app.include_router(password_change, prefix='/password/change', tags=['Login'])
app.include_router(password_forgot, prefix='/password/forgot', tags=['Login'])
# - CRUD
app.include_router(user, prefix='/user', tags=['User'], dependencies=AUTH)
app.include_router(role, prefix='/role', tags=['Role'], dependencies=AUTH)
app.include_router(acl, prefix='/acl', tags=['ACL'], dependencies=AUTH)
app.include_router(scope, prefix='/scope', tags=['Scope'], dependencies=AUTH)
app.include_router(fishingwater, prefix='/fishingwater', tags=['Fishing water'], dependencies=AUTH)
# - Email/Password hashing (internal)
app.include_router(password_hash, prefix='/encrypt', tags=['Hash (internal)'])
app.include_router(password_verify, prefix='/encrypt/verify', tags=['Hash (internal)'])

# Add middleware
app.add_middleware(BaseHTTPMiddleware, dispatch=add_db_session)
app.add_middleware(BaseHTTPMiddleware, dispatch=add_process_time_header)
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"],
                   allow_headers=["*"])

if __name__ == '__main__':
    uvicorn.run("main:app", port=8085, host="0.0.0.0", reload=False)
