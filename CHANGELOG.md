# Change log

## Unreleased

- Added Python 3.13 to the CI.
- Updated our pre-commit hooks.

## 1.1 (2024-09-23)

- Stopped interleaving `print()` statements from different compression threads.
- Started running the testsuite using GitHub actions.
- Don't crash when compressing if brotli isn't installed.
- Replaced our own HTTP Range support with the implementation added to
  Starlette 0.39.

## 1.0 (2024-05-18)

- I'm declaring this package to be production-ready.
