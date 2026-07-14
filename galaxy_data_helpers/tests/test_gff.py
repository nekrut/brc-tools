import os

from galaxy_data_helpers.gff import (
    normalize_gene_id,
    parse_gff_attributes_to_dict,
    parse_gff_cds,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "gff")


def _attr_line(path: str, line_index: int) -> str:
    """Return the attribute string (column 9) for the n'th non-comment GFF line."""
    with open(path) as fh:
        records = [ln for ln in fh if not ln.startswith("#") and ln.strip()]
    return records[line_index].rstrip("\n").split("\t")[8]


def test_parse_gff_attributes_to_dict_liftoff_gene():
    """Port of the phase_c2_triage planemo test coverage."""
    attr = _attr_line(os.path.join(DATA_DIR, "liftoff.gff3"), 0)
    attrs = parse_gff_attributes_to_dict(attr)

    assert attrs == {
        "ID": "gene1",
        "sequence_ID": "0.99",
        "coverage": "0.98",
        "extra_copy_number": "0",
        "valid_ORFs": "1",
        "partial_mapping": "False",
    }


def test_parse_gff_attributes_to_dict_liftoff_clean_gene():
    """Port of the phase_c4_merge planemo test coverage."""
    attr = _attr_line(os.path.join(DATA_DIR, "liftoff_clean.gff3"), 0)
    attrs = parse_gff_attributes_to_dict(attr)

    assert attrs == {
        "ID": "geneA",
        "coverage": "1.0",
        "sequence_ID": "0.99",
    }


def test_parse_gff_attributes_to_dict_trailing_semicolon():
    attrs = parse_gff_attributes_to_dict("ID=gene1;name=foo;")
    assert attrs == {"ID": "gene1", "name": "foo"}


def test_parse_gff_attributes_to_dict_empty():
    assert parse_gff_attributes_to_dict("") == {}


def test_parse_gff_attributes_to_dict_preserves_equals_in_value():
    """Values containing '=' should keep everything after the first '='."""
    attrs = parse_gff_attributes_to_dict("ID=gene1;note=some=value")
    assert attrs == {"ID": "gene1", "note": "some=value"}


def test_parse_gff_attributes_to_dict_whitespace_trimmed():
    attrs = parse_gff_attributes_to_dict("  ID = gene1 ; name = foo  ")
    assert attrs == {"ID": "gene1", "name": "foo"}


def test_normalize_gene_id_variants():
    assert normalize_gene_id("gene1_t2") == "gene1"
    assert normalize_gene_id("gene1.3") == "gene1"
    assert normalize_gene_id("gene1_2") == "gene1"
    assert normalize_gene_id("gene1_200") == "gene1_200"  # suffix too long


def test_parse_gff_cds_builds_segments(tmp_path):
    path = os.path.join(DATA_DIR, "liftoff_clean.gff3")
    segments = parse_gff_cds(path)
    assert "geneA" in segments
    assert len(segments["geneA"]) == 2
    chrom, start, end, strand, phase, parent = segments["geneA"][0]
    assert chrom == "chr1"
    assert start == 1000 and end == 1500
    assert strand == "+"
    assert phase == 0
    assert parent == "geneA.t1"

    filtered = parse_gff_cds(path, target_genes={"geneX"})
    assert filtered == {}
