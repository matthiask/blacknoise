import argparse
import gzip
import io
import os
from pathlib import Path

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


def try_gzip(path):
    orig_bytes = path.read_bytes()
    with io.BytesIO() as f:
        with gzip.GzipFile(
            filename="", mode="wb", fileobj=f, compresslevel=9, mtime=0
        ) as gz_file:
            gz_file.write(orig_bytes)
        gz_bytes = f.getvalue()
        orig_len = len(orig_bytes)
        gz_len = len(gz_bytes)
        if gz_len < orig_len * 0.9:
            print(
                f"{path!s} has been shrinked by {orig_len - gz_len} bytes to {int(100 * len(gz_bytes) / len(orig_bytes))}%"
            )
            Path(str(path) + ".gz").write_bytes(gz_bytes)
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

            try_gzip(path)

    return 0


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("root", help="Path containing static files to compress")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    raise SystemExit(compress(args.root))
