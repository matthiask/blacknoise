from pathlib import Path

import httpx
import pytest
from starlette.responses import PlainTextResponse

from blacknoise._impl import BlackNoise


async def app(scope, receive, send):
    response = PlainTextResponse(f"Hello from {scope['path']}")
    await response(scope, receive, send)


@pytest.mark.asyncio
async def test_app():
    this = Path(__file__).parent
    blacknoise = BlackNoise(app)
    blacknoise.add(this, "/hello/")

    assert "/hello/__init__.py" in blacknoise._files
    assert "/hello/foo" not in blacknoise._files

    assert blacknoise._files["/hello/__init__.py"] == str(this / "__init__.py")

    transport = httpx.ASGITransport(app=blacknoise)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        r = await client.get("/hello/__init__.py")
        assert r.status_code == 200
        assert "SPDX" in r.text

        r = await client.post("/hello/__init__.py")
        assert r.status_code == 405

        r = await client.get("/hello/foo")
        assert r.status_code == 404

        r = await client.get("/blub")
        assert r.status_code == 200
        assert r.text == "Hello from /blub"
