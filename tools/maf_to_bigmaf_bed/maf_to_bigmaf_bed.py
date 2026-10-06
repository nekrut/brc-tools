#!/usr/bin/env python3
"""
Convert a preprocessed MAF to BED3+1 directly (bypass mafToBigMaf's overlap check).
The 4th field is the full MAF block text with newlines replaced by ';'.

Usage: maf_to_bigmaf_bed.py <ref_acc> <input.maf> <output.bed>
"""
import sys

ref_acc, src, dst = sys.argv[1], sys.argv[2], sys.argv[3]


def species_of(seq_name):
    parts = seq_name.split('.')
    if len(parts) >= 2 and parts[0].startswith(('GCA_', 'GCF_')):
        return parts[0] + '.' + parts[1]
    return parts[0]


def emit_block(out, block):
    """Block is a list of MAF lines (including the 'a ' line). Find the ref s-line, then emit BED3+1."""
    ref_chrom = None
    ref_start = None
    ref_size = None
    for line in block:
        if line.startswith('s '):
            parts = line.split()
            sname = parts[1]
            if species_of(sname) == ref_acc:
                # Strip species prefix to match chrom-sizes file naming
                ref_chrom = sname[len(ref_acc) + 1:] if sname.startswith(ref_acc + '.') else sname
                ref_start = int(parts[2])
                ref_size = int(parts[3])
                break
    if ref_chrom is None:
        # ⛔ RETURNS FALSE, AND THE CALLER MUST COUNT THE RETURN. This used to `return`
        # while the caller incremented unconditionally, so a block with no reference row
        # -- every block, if ref_acc is misspelt -- was counted as emitted. The run then
        # printed "Emitted 2 BED3+1 records" having written none.
        return False
    # MAF block text: join lines with ';' (UCSC bigMaf convention)
    # Strip trailing newlines, trim leading whitespace per line
    text_lines = [l.rstrip('\n') for l in block]
    block_text = ';'.join(text_lines)
    out.write(f"{ref_chrom}\t{ref_start}\t{ref_start + ref_size}\t{block_text}\n")
    return True


with open(src) as fh, open(dst, 'w') as out:
    block = []
    in_body = False
    n_emit = 0
    n_skip = 0

    def _flush(b):
        global n_emit, n_skip
        if not b:
            return
        if emit_block(out, b):
            n_emit += 1
        else:
            n_skip += 1

    for line in fh:
        if not in_body:
            if line.startswith('##maf'):
                in_body = True
            continue
        if line.startswith('a '):
            _flush(block)
            block = [line]
        elif line.strip() == '':
            _flush(block)
            block = []
        else:
            if block:
                block.append(line)
    _flush(block)

# ⛔ A HEADERLESS MAF IS NOT AN EMPTY MAF. `in_body` only turns on at a `##maf` line, so a
# file without one is read to the end, nothing is written, and the job exits 0 with an
# empty bigMaf track. Distinguish it from "read fine, matched nothing".
if not in_body:
    raise SystemExit(
        f"error: {src!r} has no '##maf' header line, so not one block was read. "
        f"Every record would be silently absent from the bigMaf track.")

print(f"  Emitted {n_emit} BED3+1 records to {dst}"
      + (f"; SKIPPED {n_skip} block(s) with no '{ref_acc}' reference row" if n_skip else ""),
      flush=True)

# ⛔ ZERO RECORDS PUBLISHES AN EMPTY TRACK FROM A GREEN JOB. The overwhelmingly likely
# cause is a ref_acc that matches no s-line, which cannot be distinguished from a correct
# run over an empty alignment -- and this tool is only ever handed a produced MAF.
if n_emit == 0:
    raise SystemExit(
        f"error: no BED3+1 record was written from {src!r}. {n_skip} block(s) were read "
        f"and none carried a reference row for {ref_acc!r} -- check the accession against "
        f"the MAF's s-line names.")
