import tempfile
from pathlib import Path

import httpx
import pytest
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route, WebSocketRoute

from blacknoise import BlackNoise
from blacknoise._impl import _parse_bytes_range
from blacknoise.compress import compress, parse_args


async def http_hello(request):
    return PlainTextResponse(f"Hello from {request.url.path}")


async def ws_hello(websocket):
    await websocket.accept()
    await websocket.send_text("Hello World!")
    await websocket.close()


app = Starlette(
    routes=[
        Route("/http", http_hello),
        WebSocketRoute("/ws", ws_hello),
    ]
)


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

        r = await client.get("/http")
        assert r.status_code == 200
        assert r.text == "Hello from /http"


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


@pytest.mark.asyncio
async def test_ws(bn):
    async with httpx.AsyncClient(transport=ASGIWebSocketTransport(bn)) as client:
        http_response = await client.get("http://server/http")
        assert http_response.status_code == 200

        async with aconnect_ws("http://server/ws", client) as ws:
            message = await ws.receive_text()
            assert message == "Hello World!"


def test_compress():
    with tempfile.TemporaryDirectory() as root_:
        root = Path(root_)

        (root / "hello.txt").write_text("hello " * 100)
        (root / "hello2.txt").write_text("hello")
        (root / "hello3.jpeg").write_text("")
        compress(root)

        assert {file.name for file in root.glob("*")} == {
            "hello.txt",
            "hello.txt.gz",
            "hello.txt.br",
            "hello2.txt",
            "hello3.jpeg",
        }


def test_parse_args():
    with pytest.raises(SystemExit):
        parse_args([])

    args = parse_args(["hello"])
    assert args.root == "hello"


@pytest.mark.asyncio
async def test_range(bn):
    assert _parse_bytes_range("words=1-2") is None
    assert _parse_bytes_range("bytes=1-2") == (1, 2)
    assert _parse_bytes_range("bytes=2-1") == (2, 1)
    assert _parse_bytes_range("bytes=1-2, 3-4") is None
    assert _parse_bytes_range("bogus") is None
    assert _parse_bytes_range("bytes=bogus") is None
    assert _parse_bytes_range("bytes=-5") == (-5, None)

    transport = httpx.ASGITransport(app=bn)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        r = await client.get("/static/hello.txt", headers={"range": "words=1-2"})
        assert r.status_code == 200
        assert r.text == "world\n"

        r = await client.get("/static/hello.txt", headers={"range": "bytes=2-1"})
        assert r.status_code == 416

        r = await client.get("/static/hello.txt", headers={"range": "bytes=1-2"})
        assert r.status_code == 206
        assert r.text == "or"
        assert r.headers["content-range"] == "bytes 1-2/6"

        r = await client.get("/static/hello.txt", headers={"range": "bytes=-2"})
        assert r.status_code == 206
        assert r.text == "d\n"
        assert r.headers["content-range"] == "bytes 4-5/6"
