from pathlib import Path

from blacknoise._impl import BlackNoise


def test_app():
    this = Path(__file__).parent
    blacknoise = BlackNoise(lambda *_a: None)
    blacknoise.add(this, "/hello/")

    assert "/hello/__init__.py" in blacknoise._files
    assert "/hello/foo" not in blacknoise._files

    assert blacknoise._files["/hello/__init__.py"] == str(this / "__init__.py")
