import os
from httpx import AsyncClient, ASGITransport


def get_async_client(app):
    return AsyncClient(
        base_url=f"http://{os.getenv('API_V1_PREFIX')}",
        transport=ASGITransport(app=app)
    )
