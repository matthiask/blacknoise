import os

import anyio
from starlette.datastructures import Headers
from starlette.responses import FileResponse, PlainTextResponse

# Ten years is what nginx sets a max age if you use 'expires max;'
# so we'll follow its lead
FOREVER = f"max-age={10 * 365 * 24 * 60 * 60}, public, immutable"
A_LITTE_WHILE = "max-age=60, public"
SUFFIX_ENCODINGS = {".br": "br", ".gz": "gzip"}


def never(_path):
    return False  # no cov


class BlackNoise:
    def __init__(self, application, *, immutable_file_test=never):
        self._files = {}
        self._prefixes = ()
        self._application = application

        self._immutable_file_test = immutable_file_test

    def add(self, path, prefix):
        self._prefixes = (*self._prefixes, prefix)

        for base, _dirs, files in os.walk(path):
            path_prefix = os.path.join(prefix, base[len(str(path)) :].strip("/"))
            self._files |= {
                os.path.join(path_prefix, file): os.path.join(base, file)
                for file in files
                if all(
                    # File is not a compressed file
                    not file.endswith(suffix)
                    # The uncompressed variant does not exist
                    or file.removesuffix(suffix) not in files
                    for suffix in SUFFIX_ENCODINGS
                )
            }

    async def __call__(self, scope, receive, send):
        path = os.path.normpath(scope["path"].removeprefix(scope["root_path"]))

        if scope["type"] != "http" or not path.startswith(self._prefixes):
            response = self._application

        elif scope["method"] not in ("GET", "HEAD"):
            response = PlainTextResponse("Method Not Allowed", status_code=405)

        elif file := self._files.get(path):
            response = await _file_response(
                scope, file, self._immutable_file_test(path)
            )

        else:
            response = PlainTextResponse("Not Found", status_code=404)

        await response(scope, receive, send)


def _parse_bytes_range(header):
    units, _, range_spec = header.partition("=")
    if units != "bytes":
        return None
    start_str, sep, end_str = range_spec.strip().partition("-")
    if not sep:
        return None
    try:
        if not start_str:
            return -int(end_str), None
        return int(start_str), int(end_str) if end_str else None
    except ValueError:
        return None


class SlicedFileResponse(FileResponse):
    chunk_size = 2 * 1024 * 1024

    def __init__(self, *args, **kwargs):
        self.start = kwargs.pop("start")
        self.end = kwargs.pop("end")
        size = kwargs["stat_result"].st_size
        kwargs["headers"] = kwargs.get("headers", {}) | {
            "content-range": f"bytes {self.start}-{self.end}/{size}",
            "content-length": str(self.end - self.start + 1),
        }
        kwargs["status_code"] = 206  # partial content
        super().__init__(*args, **kwargs)

    async def __call__(self, _scope, _receive, send):
        await send(
            {
                "type": "http.response.start",
                "status": self.status_code,
                "headers": self.raw_headers,
            }
        )

        size = self.end - self.start + 1
        async with await anyio.open_file(self.path, mode="rb") as file:
            await file.seek(self.start)
            more_body = True
            while more_body:
                chunk = await file.read(self.chunk_size)
                more_body = len(chunk) == self.chunk_size

                if size > 0:
                    chunk = chunk[:size]
                    size -= len(chunk)

                if size <= 0:
                    more_body = False

                await send(
                    {
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": more_body,
                    }
                )

        if self.background is not None:
            await self.background()


async def _file_response(scope, file, immutable):
    headers = {
        "accept-ranges": "bytes",
        "access-control-allow-origin": "*",
        "cache-control": FOREVER if immutable else A_LITTE_WHILE,
    }
    h = Headers(scope=scope)
    accept_encoding = h.get("accept-encoding", "")

    # XXX It would be nice if starlette's FileResponse supported range header
    # handling out of the box then we wouldn't have to do this.
    # See https://github.com/encode/starlette/issues/950
    if bytes_range := _parse_bytes_range(h.get("range", "")):
        start, end = bytes_range
        stat_result = await anyio.to_thread.run_sync(os.stat, file)
        size = stat_result.st_size
        if start < 0:
            start = max(start + size, 0)
        if end is None:
            end = size - 1
        else:
            end = min(end, size - 1)
        if start >= end:
            return PlainTextResponse("Range Not Satisfiable", status_code=416)

        return SlicedFileResponse(
            file, headers=headers, stat_result=stat_result, start=start, end=end
        )

    for suffix, encoding in SUFFIX_ENCODINGS.items():
        if encoding not in accept_encoding:
            continue

        if file.endswith(suffix):
            return FileResponse(file, headers=headers | {"content-encoding": encoding})

        compressed_file = f"{file}{suffix}"
        if os.path.exists(compressed_file):
            return FileResponse(
                compressed_file,
                headers=headers | {"content-encoding": encoding},
            )

    return FileResponse(file, headers=headers)
