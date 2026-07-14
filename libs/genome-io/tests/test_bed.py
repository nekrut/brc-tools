import os

from genome_io.bed import load_bed_genes_by_source

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "bed")


def test_load_bed_genes_by_source_strain_collection():
    """Port of the phase_e_rbest_overlap planemo test coverage."""
    pattern = os.path.join(DATA_DIR, "strains", "*.bed")
    genes = load_bed_genes_by_source(pattern)

    assert set(genes.keys()) == {"strainA", "strainB"}
    assert genes["strainA"] == [("chrA", 100, 200, "geneA1")]
    assert genes["strainB"] == [("chrB", 100, 200, "geneB1")]


def test_load_bed_genes_by_source_sample_collection():
    """Port of the phase_e_graph_edges planemo test coverage."""
    pattern = os.path.join(DATA_DIR, "samples", "*.bed")
    genes = load_bed_genes_by_source(pattern)

    assert set(genes.keys()) == {"SampleA", "SampleB"}
    assert genes["SampleA"] == [
        ("chr1", 100, 400, "geneA1"),
        ("chr1", 800, 1200, "geneA2"),
    ]
    assert genes["SampleB"] == [("chr1", 120, 420, "geneB1")]


def test_load_bed_genes_by_source_skips_comments_and_short_rows(tmp_path):
    bed = tmp_path / "test.bed"
    bed.write_text(
        "# comment\n"
        "\n"
        "chr1\t10\t20\tgene1\n"
        "chr1\t30\t40\n"  # too short, should be ignored
    )

    genes = load_bed_genes_by_source(str(tmp_path / "*.bed"))
    assert genes == {"test": [("chr1", 10, 20, "gene1")]}
