from io import StringIO
import os

from genome_io.pansn import load_graph_paths, parse_pansn, rename_headers

DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "pansn")


def test_parse_pansn_handles_three_parts():
    assert parse_pansn("sample#1#chr1") == ("sample", "chr1")
    assert parse_pansn("weird") == ("weird", "weird")


def test_load_graph_paths(tmp_path):
    groups = load_graph_paths(os.path.join(DATA_DIR, "paths.tsv"))
    assert groups["contig1"] == {"sampleA", "sampleB"}


def test_rename_headers():
    input_fa = ">contig1\nACGT\n"
    out = StringIO()
    n = rename_headers(StringIO(input_fa), out, "sample", 2, "#")
    assert n == 1
    assert out.getvalue().startswith(">sample#2#contig1")
