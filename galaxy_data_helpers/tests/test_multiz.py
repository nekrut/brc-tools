from galaxy_data_helpers.multiz import load_matrix, order_queries, similarities_to_hinge


def test_load_matrix_and_similarities(tmp_path):
    csv_text = "ref,queryA,queryB\n1.0,0.8,0.6\n0.8,1.0,0.7\n0.6,0.7,1.0\n"
    csv_path = tmp_path / "compare.csv"
    csv_path.write_text(csv_text)

    labels, rows = load_matrix(csv_path)
    assert labels == ["ref", "queryA", "queryB"]

    sims = similarities_to_hinge(labels, rows, "ref")
    assert sims["queryA"] == 0.8
    assert sims["queryB"] == 0.6


def test_order_queries_handles_missing():
    sims = {"A": 0.9, "B": 0.8}
    ordered = order_queries(["A", "C", "B"], sims)
    assert ordered == ["A", "B", "C"]
