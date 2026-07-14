from genome_io.intervals import best_query_gene, index_by_chrom


def test_index_by_chrom_builds_sorted_lists():
    genes = [
        ("chr1", 10, 20, "g1"),
        ("chr1", 5, 15, "g2"),
        ("chr2", 0, 5, "g3"),
    ]
    idx = index_by_chrom(genes)
    starts, entries = idx["chr1"]
    assert starts == [5, 10]
    assert entries[0][2] == "g2"


def test_best_query_gene_finds_highest_overlap():
    idx = index_by_chrom([("chr", 0, 10, "g1"), ("chr", 20, 40, "g2")])
    best = best_query_gene(0, 10, idx["chr"])
    assert best == ("g1", 1.0)
    assert best_query_gene(50, 60, idx.get("chr")) is None
