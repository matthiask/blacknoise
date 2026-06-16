# blacknoise

[![PyPI - Version](https://img.shields.io/pypi/v/blacknoise.svg)](https://pypi.org/project/blacknoise)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/blacknoise.svg)](https://pypi.org/project/blacknoise)

blacknoise is an [ASGI](https://asgi.readthedocs.io/en/latest/) app for static
file serving inspired by [whitenoise](https://github.com/evansd/whitenoise/)
and following the principles of [low maintenance
software](https://406.ch/writing/low-maintenance-software/).


## Using blacknoise to serve static files

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

The example uses Django, but you can wrap any ASGI application.

`BlackNoise` will automatically handle all paths below the prefixes added, and
either return the files or return 404 errors if files do not exist. The files
are added on server startup, which also means that `BlackNoise` only knows
about files which existed at that particular point in time.

`BlackNoise` doesn't watch the added folders for changes; if you add new files
you have to restart the server, otherwise those files aren't served. It doesn't
cache file contents though, so changes to files are directly picked up.

## Improving performance

`BlackNoise` has worse performance than when using an optimized webserver such
as nginx and others. Sometimes it doesn't matter much if the app is behind a
caching reverse proxy or behind a content delivery network anyway. To further
support this use case `BlackNoise` can be configured to serve media files with
far-future expiry headers and has support for serving compressed assets.

### Serving pre-compressed assets

Compressing is possible by running:

```console
python -m blacknoise.compress static/
```

`BlackNoise` will try compress non-binary files using gzip or brotli (if the
[Brotli](ttps://pypi.org/project/Brotli/) library is available), and will serve
the compressed version if the compression actually results in (significantly)
smaller files and if the client also supports it. Files are compressed in
parallel for faster completion times.

### Setting far-future expiry headers

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

## Comparison with similar projects

**[whitenoise](https://github.com/evansd/whitenoise/)** is the original inspiration
for blacknoise. whitenoise only supports WSGI; an [ASGI pull
request](https://github.com/evansd/whitenoise/pull/359) was never merged, which
prompted the creation of blacknoise.

**[ServeStatic](https://github.com/Archmonger/ServeStatic)** is effectively
whitenoise with that ASGI pull request merged and continued development on top.
It supports development setups and is a more complete drop-in replacement for
whitenoise. blacknoise takes a different approach: it delegates to
[Starlette](https://github.com/encode/starlette) for the actual file serving and
intentionally does as little as possible, keeping the codebase small and easy to
maintain.

If you need development-mode static file serving or a feature-rich whitenoise
replacement, ServeStatic may be a better fit. If you value simplicity and are happy
letting your ASGI framework or a reverse proxy handle the rest, blacknoise is for
you.

If you are already using [granian](https://github.com/emmett-framework/granian) as
your server, consider using its built-in static file serving instead. It handles
files directly without any additional Python layer.

## License

`blacknoise` is distributed under the terms of the
[MIT](https://spdx.org/licenses/MIT.html) license.
