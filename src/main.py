import os

import uvicorn as uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI

from src.domains.encrypt.api import password, validate
from src.domains.fishingwater.api import fishingwater
from src.domains.systemvalue.api import systemvalue
from src.domains.user.api import user, user_registration

load_dotenv()
env = os.getenv('ENV')
os.environ['DATABASE_URI'] = os.getenv(f'DATABASE_URI_{env}')

prefix = os.getenv('API_V1_PREFIX')
app = FastAPI(openapi_url=f"{prefix}/openapi.json", docs_url=f"{prefix}/docs")

app.include_router(fishingwater, prefix=f'{prefix}/fishingwater', tags=['fishingwater'])
app.include_router(user, prefix=f'{prefix}/user', tags=['user'])
app.include_router(user_registration, prefix=f'{prefix}/user_registration', tags=['user_registration'])
app.include_router(systemvalue, prefix=f'{prefix}/systemvalue', tags=['systemvalue'])
app.include_router(password, prefix=f'{prefix}/password', tags=['password'])
app.include_router(validate, prefix=f'{prefix}/validate', tags=['validate'])


if __name__ == '__main__':
    uvicorn.run("main:app", port=8085, host="0.0.0.0", reload=False)
