from pathlib import Path

from genome_io.maf import (
    emit_bed_record,
    find_ref_index,
    iter_maf_blocks,
    parse_blocks,
    reorder_block,
    species_of,
)

DATA_DIR = Path(__file__).parent / "data" / "maf"


def test_species_of_accession_with_version():
    assert species_of("GCA_900093555.2.LT635612.2") == "GCA_900093555.2"


def test_species_of_accession_gcf():
    assert species_of("GCF_001234567.1.chromosome") == "GCF_001234567.1"


def test_species_of_ucsc_species():
    assert species_of("musMusculus.chr1") == "musMusculus"


def test_species_of_single_token():
    assert species_of("PanTro4") == "PanTro4"


def _sample_blocks():
    with open(DATA_DIR / "sample.maf") as fh:
        header, blocks = parse_blocks(fh)
    return blocks


def test_parse_blocks_and_iter_blocks_agree():
    with open(DATA_DIR / "sample.maf") as fh:
        header, blocks = parse_blocks(fh)
    assert header[0].startswith("##maf")
    with open(DATA_DIR / "sample.maf") as fh:
        iterated = list(iter_maf_blocks(fh))
    assert blocks == iterated


def test_find_ref_and_reorder():
    block = _sample_blocks()[0]
    idx = find_ref_index(block, "GCA_000001.1")
    assert idx == 0
    reordered = reorder_block(block, idx)
    assert reordered[0].startswith("a ")
    assert reordered[1].split()[1].startswith("GCA_000001.1")


def test_emit_bed_record():
    block = _sample_blocks()[0]
    chrom, start, end, text = emit_bed_record(block, "GCA_000001.1")
    assert chrom == "chr1"
    assert start == 0 and end == 4
    assert "a score=0" in text
