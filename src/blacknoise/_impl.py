import os

from starlette.responses import FileResponse


class Blacknoise:
    def __init__(self, application):
        self._files = {}
        self._application = application

    def add(self, path, root):
        print(self, path, root)
        for base, _dirs, files in os.walk(path):
            self._files |= {
                os.path.join(root, file): os.path.join(base, file) for file in files
            }

        print(self._files)

    async def __call__(self, scope, receive, send):
        if file := self._files.get(scope["path"]):
            response = FileResponse(file)
            await response(scope, receive, send)
        else:
            await self._application(scope, receive, send)
