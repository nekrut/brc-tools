"""MAF-format helpers for Galaxy tool wrappers."""

from __future__ import annotations

from typing import Iterable, Iterator, List, Sequence, Tuple

MAFBlock = List[str]


def species_of(seq_name: str) -> str:
    """Extract the species/accession prefix from an MAF s-line sequence name."""

    parts = seq_name.split(".")
    if len(parts) >= 2 and parts[0].startswith(("GCA_", "GCF_")):
        return parts[0] + "." + parts[1]
    return parts[0]


def parse_blocks(lines: Iterable[str]) -> tuple[list[str], list[MAFBlock]]:
    """Return (header_lines, blocks) from a sequence of MAF lines."""

    header: list[str] = []
    blocks: list[MAFBlock] = []
    current: list[str] = []
    in_body = False
    for line in lines:
        if not in_body:
            header.append(line)
            if line.startswith("##maf"):
                in_body = True
            continue
        if line.startswith("a "):
            if current:
                blocks.append(current)
            current = [line]
        elif not line.strip():
            if current:
                blocks.append(current)
                current = []
        else:
            if current:
                current.append(line)
    if current:
        blocks.append(current)
    return header, blocks


def iter_maf_blocks(lines: Iterable[str]) -> Iterator[MAFBlock]:
    """Yield blocks lazily from a sequence of MAF lines (skips headers)."""

    current: list[str] = []
    in_body = False
    for line in lines:
        if not in_body:
            if line.startswith("##maf"):
                in_body = True
            continue
        if line.startswith("a "):
            if current:
                yield current
            current = [line]
        elif not line.strip():
            if current:
                yield current
                current = []
        else:
            if current:
                current.append(line)
    if current:
        yield current


def find_ref_index(block: Sequence[str], ref_species: str) -> int | None:
    """Return the index (among s-lines) of the first reference s-line."""

    s_idx = 0
    for line in block:
        if line.startswith("s "):
            if species_of(line.split()[1]) == ref_species:
                return s_idx
            s_idx += 1
    return None


def reorder_block(block: Sequence[str], ref_index: int) -> MAFBlock:
    """Move the reference s-line to the first s-line position in ``block``."""

    s_lines = [ln for ln in block if ln.startswith("s ")]
    other = [ln for ln in block if not ln.startswith("s ")]
    ref_line = s_lines.pop(ref_index)
    return other + [ref_line] + s_lines


def ref_coords(block: Sequence[str], ref_species: str) -> tuple[str, int, int] | None:
    """Return (chrom, start, end) for the reference s-line (if present)."""

    for line in block:
        if line.startswith("s "):
            parts = line.split()
            if species_of(parts[1]) == ref_species:
                chrom = parts[1]
                start = int(parts[2])
                span = int(parts[3])
                return chrom, start, start + span
    return None


def emit_bed_record(block: Sequence[str], ref_species: str) -> tuple[str, int, int, str] | None:
    """Convert a block into a BED3+1 tuple for the reference species."""

    coords = ref_coords(block, ref_species)
    if coords is None:
        return None
    chrom, start, end = coords
    # Trim species prefix for chrom comparison (optional)
    if chrom.startswith(ref_species + "."):
        chrom = chrom[len(ref_species) + 1 :]
    lines = [ln.rstrip("\n") for ln in block]
    block_text = ";".join(lines)
    return chrom, start, end, block_text
