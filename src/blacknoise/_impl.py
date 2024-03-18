import os

from starlette.exceptions import HTTPException
from starlette.responses import FileResponse

# Ten years is what nginx sets a max age if you use 'expires max;'
# so we'll follow its lead
FOREVER = f"max-age={10 * 365 * 24 * 60 * 60}, public, immutable"
A_LITTE_WHILE = "max-age=60, public"


class Blacknoise:
    def __init__(self, application, *, immutable_file_test=lambda *_a: False):
        self._files = {}
        self._prefixes = ()
        self._application = application

        self._immutable_file_test = immutable_file_test

    def add(self, path, prefix):
        self._prefixes += (prefix,)
        for base, _dirs, files in os.walk(path):
            self._files |= {
                os.path.join(prefix, file): os.path.join(base, file) for file in files
            }

    async def __call__(self, scope, receive, send):
        path = os.path.normpath(scope["path"].removeprefix(scope["root_path"]))
        if not path.startswith(self._prefixes):
            await self._application(scope, receive, send)
            return

        if scope["type"] != "http" or scope["method"] not in ("GET", "HEAD"):
            raise HTTPException(status_code=405)

        if file := self._files.get(path):
            headers = {
                "access-control-allow-origin": "*",
                "cache-control": (
                    FOREVER if self._immutable_file_test(path) else A_LITTE_WHILE
                ),
            }
            response = FileResponse(file, headers=headers)
            await response(scope, receive, send)
            return

        raise HTTPException(status_code=404)
