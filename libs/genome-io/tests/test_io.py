import gzip

from genome_io.io import open_maybe_gz, read_manifest


def test_read_manifest(tmp_path):
    manifest = tmp_path / "manifest.tsv"
    manifest.write_text("id1\t/path1\nid2\t/path2\n")
    assert read_manifest(manifest) == [("id1", "/path1"), ("id2", "/path2")]


def test_open_maybe_gz_reads_gzip(tmp_path):
    gz_path = tmp_path / "sample.fa.gz"
    with gzip.open(gz_path, "wt") as fh:
        fh.write(">seq\nACGT\n")
    with open_maybe_gz(gz_path, "rt") as reader:
        data = reader.read()
    assert "ACGT" in data
