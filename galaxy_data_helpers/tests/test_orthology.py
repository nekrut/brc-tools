from galaxy_data_helpers.orthology import (
    UnionFind,
    collapse_positions,
    edge_weight,
    reciprocal_overlap,
)


def test_edge_weight_defaults():
    assert edge_weight("liftoff", "I") == 0.95
    assert edge_weight("none", "I") == 0.0
    assert edge_weight("unknown", "NA") == 0.10


def test_union_find_merges_components():
    uf = UnionFind()
    uf.union("a", "b")
    uf.union("c", "d")
    uf.union("b", "c")
    assert uf.find("a") == uf.find("d")


def test_reciprocal_overlap():
    assert reciprocal_overlap((0, 10), (5, 15)) == 0.5
    assert reciprocal_overlap((0, 10), (10, 20)) == 0.0


def test_collapse_positions_groups_by_overlap():
    node_pos = {
        "strain#gene1": ("chr1", 0, 100),
        "strain#gene2": ("chr1", 50, 150),
        "strain#gene3": ("chr2", 0, 100),
    }
    clusters = collapse_positions(["gene1", "gene2", "gene3"], "strain", node_pos)
    assert any({"gene1", "gene2"} == set(cluster) for cluster in clusters)
    assert any(cluster == ["gene3"] for cluster in clusters)


def test_collapse_positions_handles_missing_coords():
    clusters = collapse_positions(["geneX", "geneY"], "strain", {})
    assert clusters == [["geneX"], ["geneY"]]
