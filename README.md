# blacknoise

[![PyPI - Version](https://img.shields.io/pypi/v/blacknoise.svg)](https://pypi.org/project/blacknoise)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/blacknoise.svg)](https://pypi.org/project/blacknoise)

-----

**Table of Contents**

- [Installation](#installation)
- [License](#license)

## Installation

```console
pip install blacknoise
```

### Using blacknoise with Django to serve static files

```python
from blacknoise import BlackNoise
from django.core.asgi import get_asgi_application
from pathlib import Path

BASE_DIR = Path(__file__).parent

application = BlackNoise(get_asgi_application())
application.add(BASE_DIR / "static", "/static")
```

## License

`blacknoise` is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
