import asyncio

import httpx

from app.main import app


def test_health():
    async def run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url='http://testserver') as client:
            response = await client.get('/api/health')
        assert response.status_code == 200
        assert response.json()['ok'] is True

    asyncio.run(run())
