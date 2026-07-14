from genome_io.collections import relabel_pairs, self_pairs


def test_relabel_pairs_cross_product():
    pairs = relabel_pairs(["A", "B"])
    assert ("A_B", "A.B") in pairs
    assert len(pairs) == 4


def test_self_pairs_only_diagonal():
    pairs = self_pairs(["X", "Y"])
    assert pairs == [("X_X", "X.X"), ("Y_Y", "Y.Y")]
