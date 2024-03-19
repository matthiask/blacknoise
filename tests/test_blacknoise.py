from pathlib import Path

import httpx
import pytest
from starlette.responses import PlainTextResponse

from blacknoise._impl import BlackNoise


async def app(scope, receive, send):
    response = PlainTextResponse(f"Hello from {scope['path']}")
    await response(scope, receive, send)


@pytest.fixture
def bn():
    this = Path(__file__).parent
    blacknoise = BlackNoise(app)
    blacknoise.add(this / "static", "/static/")
    return blacknoise


def test_files_contents(bn):
    this = Path(__file__).parent

    assert "/static/hello.txt" in bn._files
    assert "/static/hello.txt.gz" not in bn._files
    assert "/static/hello2.txt.gz" in bn._files
    assert "/static/hello3.txt" in bn._files
    assert "/static/foo" not in bn._files

    assert bn._files["/static/hello.txt"] == str(this / "static" / "hello.txt")


@pytest.mark.asyncio
async def test_static_file_serving(bn):
    transport = httpx.ASGITransport(app=bn)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        r = await client.get("/static/hello.txt")
        assert r.status_code == 200
        assert r.text == "world\n"

        r = await client.get("/static/hello2.txt.gz")
        assert r.status_code == 200
        # assert r.text == "world2\n"  FIXME

        r = await client.get("/static/hello3.txt")
        assert r.status_code == 200
        assert r.text == "world3\n"

        r = await client.post("/static/hello.txt")
        assert r.status_code == 405

        r = await client.get("/static/foo")
        assert r.status_code == 404

        r = await client.get("/blub")
        assert r.status_code == 200
        assert r.text == "Hello from /blub"
