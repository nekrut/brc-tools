from galaxy_data_helpers.pansn import load_graph_paths, parse_pansn


def test_parse_pansn_handles_three_parts():
    assert parse_pansn("sample#1#chr1") == ("sample", "chr1")
    assert parse_pansn("weird") == ("weird", "weird")


def test_load_graph_paths(tmp_path):
    content = "sampleA#1#contig\nsampleB#1#contig\n"
    path = tmp_path / "paths.tsv"
    path.write_text(content)
    groups = load_graph_paths(path)
    assert groups["contig"] == {"sampleA", "sampleB"}
