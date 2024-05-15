import argparse
from concurrent.futures import ThreadPoolExecutor, wait
import gzip
import io
from itertools import cycle
import os
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
        print(
            f"{path!s} has been shrinked by {algorithm} by {orig_len - compress_len} bytes to {int(100 * len(compress_bytes) / len(orig_bytes))}%"
        )
        Path(str(path) + suffix).write_bytes(compress_bytes)
    else:
        print(f"{path!s} has been skipped because of missing gains")


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


def compress(root):
    workers = os.cpu_count()
    paths = [[] for _ in range(workers)]
    paths_ = cycle(paths)

    for dir_, _dirs, files in os.walk(root):
        dir = Path(dir_)
        for filename in files:
            path = dir / filename
            if path.suffix not in SKIP_COMPRESS_EXTENSIONS:
                next(paths_).append(path)

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(_compress_paths, p) for p in paths]
        wait(futures)

    return 0


def _compress_paths(paths):
    for path in paths:
        orig_bytes = path.read_bytes()
        try_brotli(path, orig_bytes)
        try_gzip(path, orig_bytes)


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Path containing static files to compress")
    return parser.parse_args(args)


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(compress(args.root))
