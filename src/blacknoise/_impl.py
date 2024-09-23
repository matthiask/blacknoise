import os

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


async def _file_response(scope, file, immutable):
    headers = {
        "accept-ranges": "bytes",
        "access-control-allow-origin": "*",
        "cache-control": FOREVER if immutable else A_LITTE_WHILE,
    }
    h = Headers(scope=scope)
    accept_encoding = h.get("accept-encoding", "")

    # Defer to Starlette when we get a HTTP Range request.
    if h.get("range"):
        return FileResponse(file, headers=headers)

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
