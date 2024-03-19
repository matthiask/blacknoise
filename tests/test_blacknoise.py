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
    blacknoise = BlackNoise(app, immutable_file_test=lambda path: "hello3" in path)
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
        assert r.headers["content-encoding"] == "gzip"
        assert r.headers["cache-control"] == "max-age=60, public"
        assert r.headers["access-control-allow-origin"] == "*"

        r = await client.get("/static/hello2.txt.gz")
        assert r.status_code == 200
        assert r.text == "world2\n"
        assert r.headers["content-encoding"] == "gzip"
        assert r.headers["cache-control"] == "max-age=60, public"
        assert r.headers["access-control-allow-origin"] == "*"

        r = await client.get("/static/hello3.txt")
        assert r.status_code == 200
        assert r.text == "world3\n"
        assert "content-encoding" not in r.headers
        assert r.headers["cache-control"] == "max-age=315360000, public, immutable"
        assert r.headers["access-control-allow-origin"] == "*"

        r = await client.post("/static/hello.txt")
        assert r.status_code == 405

        r = await client.get("/static/foo")
        assert r.status_code == 404

        r = await client.get("/blub")
        assert r.status_code == 200
        assert r.text == "Hello from /blub"


@pytest.mark.asyncio
async def test_accept_encoding(bn):
    transport = httpx.ASGITransport(app=bn)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        r = await client.get("/static/hello.txt", headers={"accept-encoding": "gzip"})
        assert r.status_code == 200
        assert r.text == "world\n"
        assert r.headers["content-encoding"] == "gzip"

        r = await client.get(
            "/static/hello.txt", headers={"accept-encoding": "identity"}
        )
        assert r.status_code == 200
        assert r.text == "world\n"
        assert "content-encoding" not in r.headers
