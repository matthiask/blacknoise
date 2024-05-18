import argparse
import gzip
import io
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    import brotli
except ModuleNotFoundError:  # no cov
    brotli = None

# Extensions that it's not worth trying to compress
SKIP_COMPRESS_EXTENSIONS = (
    # Images
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    # Compressed files
    ".zip",
    ".gz",
    ".tgz",
    ".bz2",
    ".tbz",
    ".xz",
    ".br",
    # Flash
    ".swf",
    ".flv",
    # Fonts
    ".woff",
    ".woff2",
    # Video
    ".3gp",
    ".3gpp",
    ".asf",
    ".avi",
    ".m4v",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".webm",
    ".wmv",
)


def _write_if_smaller(path, orig_bytes, compress_bytes, algorithm, suffix):
    orig_len = len(orig_bytes)
    compress_len = len(compress_bytes)
    if compress_len < orig_len * 0.9:
        compress_improvement = (compress_len - orig_len) / orig_len
        print(
            f"{path!s}: {algorithm} compressed {orig_len} to {compress_len} bytes ({int(100 * compress_improvement)}%)"
        )
        Path(str(path) + suffix).write_bytes(compress_bytes)
    else:
        print(f"{path!s}: {algorithm} didn't produce useful compression results")


def try_gzip(path, orig_bytes):
    with io.BytesIO() as f:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=f, compresslevel=9, mtime=0
        ) as compress_file:
            compress_file.write(orig_bytes)
        _write_if_smaller(
            path,
            orig_bytes,
            f.getvalue(),
            "Gzip",
            ".gz",
        )


def try_brotli(path, orig_bytes):
    if not brotli:  # no cov
        return
    _write_if_smaller(
        path,
        orig_bytes,
        brotli.compress(orig_bytes),
        "Brotli",
        ".br",
    )


def _compress_path(path):
    orig_bytes = path.read_bytes()
    try_brotli(path, orig_bytes)
    try_gzip(path, orig_bytes)


def _paths(root):
    for dir_, _dirs, files in os.walk(root):
        dir = Path(dir_)
        for filename in files:
            path = dir / filename
            if path.suffix not in SKIP_COMPRESS_EXTENSIONS:
                yield path


def compress(root):
    with ThreadPoolExecutor() as executor:
        executor.map(_compress_path, _paths(root))
    return 0


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Path containing static files to compress")
    return parser.parse_args(args)


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(compress(args.root))
