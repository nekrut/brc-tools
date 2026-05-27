#!/usr/bin/env python3
"""Concatenate FASTAs (plain or gzipped) into one multifasta.

Order is taken from positional args; preserves headers and sequence
bodies verbatim. Output is plain text or gzip per --gzip flag.
"""

from __future__ import annotations

__version__ = "1.0.0"

import argparse
import gzip
import logging
import shutil
import sys
from pathlib import Path


def open_in(path: Path):
    with open(path, "rb") as probe:
        magic = probe.read(2)
    if magic == b"\x1f\x8b":
        return gzip.open(path, "rb")
    return open(path, "rb")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--gzip", action="store_true",
                        help="Gzip-compress the output.")
    parser.add_argument("inputs", nargs="+", type=Path,
                        help="Input FASTA files (.fa or .fa.gz).")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    if args.gzip:
        out_fh = gzip.open(args.output, "wb")
    else:
        out_fh = open(args.output, "wb")

    try:
        for fa in args.inputs:
            with open_in(fa) as in_fh:
                shutil.copyfileobj(in_fh, out_fh, length=1 << 20)
            logging.info("appended %s", fa)
    finally:
        out_fh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
