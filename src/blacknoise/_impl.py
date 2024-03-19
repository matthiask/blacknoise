import os

from starlette.responses import FileResponse, PlainTextResponse

# Ten years is what nginx sets a max age if you use 'expires max;'
# so we'll follow its lead
FOREVER = f"max-age={10 * 365 * 24 * 60 * 60}, public, immutable"
A_LITTE_WHILE = "max-age=60, public"

_compress_content_encodings = {".gz": "gzip"}


class BlackNoise:
    def __init__(self, application, *, immutable_file_test=lambda *_a: False):
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
                    for suffix in _compress_content_encodings
                )
            }

    async def __call__(self, scope, receive, send):
        path = os.path.normpath(scope["path"].removeprefix(scope["root_path"]))

        if not path.startswith(self._prefixes):
            response = self._application

        elif scope["type"] != "http" or scope["method"] not in ("GET", "HEAD"):
            response = PlainTextResponse("Method Not Allowed", status_code=405)

        elif file := self._files.get(path):
            headers = {
                "access-control-allow-origin": "*",
                "cache-control": (
                    FOREVER if self._immutable_file_test(path) else A_LITTE_WHILE
                ),
            }
            gz_file = f"{file}.gz"
            if os.path.exists(gz_file):
                response = FileResponse(
                    gz_file, headers=headers | {"content-encoding": "gzip"}
                )
            elif encoding := next(
                (
                    encoding
                    for suffix, encoding in _compress_content_encodings.items()
                    if file.endswith(suffix)
                ),
                None,
            ):
                response = FileResponse(
                    file, headers=headers | {"content-encoding": encoding}
                )
            else:
                response = FileResponse(file, headers=headers)

        else:
            response = PlainTextResponse("Not Found", status_code=404)

        await response(scope, receive, send)
