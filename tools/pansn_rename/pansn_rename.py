#!/usr/bin/env python3
"""Prefix FASTA headers with PanSN spec: SAMPLE<DELIM>HAP<DELIM>CONTIG.

Reads (optionally gzipped) FASTA on --input, writes renamed FASTA on
--output (gzipped iff --gzip-output).

PanSN-spec: https://github.com/pangenome/PanSN-spec
"""

from __future__ import annotations

__version__ = "1.0.0"

import argparse
import gzip
import io
import logging
import sys
from pathlib import Path


def open_maybe_gz(path: Path, mode: str) -> io.IOBase:
    """Detect gzip by magic bytes (1f 8b), not by extension.

    Galaxy stores datasets as `.dat` regardless of original type, so
    extension-based detection breaks. Magic-byte sniff is robust.
    """
    if "r" in mode:
        with open(path, "rb") as probe:
            is_gz = probe.read(2) == b"\x1f\x8b"
        if is_gz:
            return gzip.open(path, mode)
    return open(path, mode)


def rename(in_fh, out_fh, sample: str, hap: int, delim: str) -> int:
    n_headers = 0
    prefix = f"{sample}{delim}{hap}{delim}"
    for line in in_fh:
        if line.startswith(">"):
            n_headers += 1
            contig = line[1:].split(None, 1)[0]
            rest = line[1 + len(contig):]
            out_fh.write(f">{prefix}{contig}{rest}")
        else:
            out_fh.write(line)
    return n_headers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sample", required=True,
                        help="Sample name (no whitespace, no delim).")
    parser.add_argument("--haplotype", type=int, default=1)
    parser.add_argument("--delimiter", default="#")
    parser.add_argument("--gzip-output", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(sys.stderr)],
    )

    if args.delimiter in args.sample:
        logging.error("Sample name %r contains delimiter %r", args.sample, args.delimiter)
        return 2
    if any(c.isspace() for c in args.sample):
        logging.error("Sample name %r contains whitespace", args.sample)
        return 2

    in_mode = "rt"
    out_mode = "wt"
    out_path = args.output

    with open_maybe_gz(args.input, in_mode) as in_fh:
        if args.gzip_output:
            with gzip.open(out_path, out_mode) as out_fh:
                n = rename(in_fh, out_fh, args.sample, args.haplotype, args.delimiter)
        else:
            with open(out_path, out_mode) as out_fh:
                n = rename(in_fh, out_fh, args.sample, args.haplotype, args.delimiter)

    logging.info("Renamed %d headers (sample=%s hap=%d delim=%r)",
                 n, args.sample, args.haplotype, args.delimiter)
    if n == 0:
        logging.error("No FASTA headers found in input")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
