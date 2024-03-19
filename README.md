# blacknoise

[![PyPI - Version](https://img.shields.io/pypi/v/blacknoise.svg)](https://pypi.org/project/blacknoise)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/blacknoise.svg)](https://pypi.org/project/blacknoise)

blacknoise is an [ASGI](https://asgi.readthedocs.io/en/latest/) app for static
file serving inspired by [whitenoise](https://github.com/evansd/whitenoise/)
and following the principles of [low maintenance
software](https://406.ch/writing/low-maintenance-software/).

**This is pre-alpha software and everything is subject to change. I'm not even
sure if blacknoise should exist at all or if the energy wouldn't be better
spent improving whitenoise or other tools. Feedback and contributions are very
welcome though!**


## Using blacknoise with Django to serve static files

Install blacknoise into your Python environment:

```console
pip install blacknoise
```

Wrap your ASGI application with the `BlackNoise` app:

```python
from blacknoise import BlackNoise
from django.core.asgi import get_asgi_application
from pathlib import Path

BASE_DIR = Path(__file__).parent

application = BlackNoise(get_asgi_application())
application.add(BASE_DIR / "static", "/static")
```

`BlackNoise` will automatically handle all paths below the prefixes added, and
either return the files or return 404 errors if files do not exist. The files
are added on server startup, which also means that `BlackNoise` only knows
about files which existed at that particular point in time.

## Improving performance

`BlackNoise` has worse performance than when using an optimized webserver such
as nginx and others. Sometimes it doesn't matter much if the app is behind a
caching reverse proxy or behind a content delivery network anyway. To further
support this use case `BlackNoise` can be configured to serve media files with
far-future expiry headers and has support for serving compressed assets.

Compressing is possible by running:

```console
python -m blacknoise.compress static/
```

`BlackNoise` will try compress non-binary files using gzip or brotli (if the
[Brotli](ttps://pypi.org/project/Brotli/) library is available), and will serve
the gzip encoded version if the compression actually results in (significantly)
smaller files.

Far-future expiry headers can be enabled by passing the `immutable_file_test`
callable to the `BlackNoise` constructor:

```python
def immutable_file_test(path):
    return True  # Enable far-future expiry headers for all files

application = BlackNoise(
    get_asgi_application(),
    immutable_file_test=immutable_file_test,
)
```

Maybe you want to add some other logic, for example check if the path contains
a hash based upon the contents of the static file. Such hashes can be added by
Django's `ManifestStaticFilesStorage` or by appropriately configuring bundlers
such as `webpack` and others.

## License

`blacknoise` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
