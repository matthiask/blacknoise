import argparse
import gzip
import io
import os
from pathlib import Path

try:
    import brotli
except ModuleNotFoundError:
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


def try_gzip(path, orig_bytes):
    with io.BytesIO() as f:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=f, compresslevel=9, mtime=0
        ) as compress_file:
            compress_file.write(orig_bytes)
        compress_bytes = f.getvalue()
        orig_len = len(orig_bytes)
        compress_len = len(compress_bytes)
        if compress_len < orig_len * 0.9:
            print(
                f"{path!s} has been shrinked by Gzip by {orig_len - compress_len} bytes to {int(100 * len(compress_bytes) / len(orig_bytes))}%"
            )
            Path(str(path) + ".gz").write_bytes(compress_bytes)
        else:
            print(f"{path!s} has been skipped because of missing gains")


def try_brotli(path, orig_bytes):
    compress_bytes = brotli.compress(orig_bytes)
    orig_len = len(orig_bytes)
    compress_len = len(compress_bytes)
    if compress_len < orig_len * 0.9:
        print(
            f"{path!s} has been shrinked by Brotli by {orig_len - compress_len} bytes to {int(100 * len(compress_bytes) / len(orig_bytes))}%"
        )
        Path(str(path) + ".br").write_bytes(compress_bytes)
    else:
        print(f"{path!s} has been skipped because of missing gains")


def compress(root):
    for root, _dirs, files in os.walk(args.root):
        dir = Path(root)
        for filename in files:
            path = dir / filename
            if path.suffix in SKIP_COMPRESS_EXTENSIONS:
                # print(f"Skipping {str(path)} because of extension")
                continue

            orig_bytes = path.read_bytes()
            try_gzip(path, orig_bytes)

            if brotli:
                try_brotli(path, orig_bytes)

    return 0


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Path containing static files to compress")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(compress(args.root))
