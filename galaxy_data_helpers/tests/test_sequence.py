from pathlib import Path

from genome_io.sequence import (
    classify_bed_interval,
    classify_repeat_signature,
    extract_cds,
    extract_sequence,
    has_internal_stop,
    load_fasta_as_dict,
    revcomp,
    strip_internal_stops,
    translate,
)

DATA_DIR = Path(__file__).parent / "data" / "sequence"


def test_load_fasta_as_dict_uppercases_sequences():
    fasta = load_fasta_as_dict(DATA_DIR / "test.fa")
    assert set(fasta) == {"chr_poly", "chr_tandem", "chr_mixed"}
    assert fasta["chr_poly"] == "AAAAAAAAAA"
    # Ensure lowercase bases are uppercased
    assert fasta["chr_mixed"].isupper()


def test_classify_repeat_signature_poly():
    signature, score = classify_repeat_signature("AAAAAAAAAA")
    assert signature == "polyA"
    assert score == 1000


def test_classify_repeat_signature_tandem():
    signature, score = classify_repeat_signature("ATATATATAT")
    assert signature == "(AT)n"
    assert score >= 900


def test_classify_repeat_signature_low_complex():
    noisy = "ACGTCCAGTTCAGTAGCTA"
    signature, score = classify_repeat_signature(noisy)
    assert signature == "lc"
    assert score < 700


def test_classify_bed_interval_slice():
    fasta = load_fasta_as_dict(DATA_DIR / "test.fa")
    signature, score = classify_bed_interval(fasta, "chr_tandem", 0, 6)
    assert signature == "(AT)n"
    assert score >= 900


class DummyRecord:
    def __init__(self, seq: str):
        self.seq = seq

    def __getitem__(self, slc):
        return self.seq[slc]

    def __str__(self):
        return self.seq


class DummyFasta(dict):
    def __getitem__(self, key):
        return DummyRecord(super().__getitem__(key))


def test_revcomp_and_translate():
    assert revcomp("AaTtGc") == "gCaAtT"
    assert translate("ATGTAA") == "M*"


def test_strip_and_detect_internal_stops():
    cds = "ATGTAGAAA"  # TAG internal stop
    stripped = strip_internal_stops(cds)
    assert stripped.startswith("ATGNNN")
    assert has_internal_stop("ATGTAGAAA") is True
    assert has_internal_stop("ATGAAA") is False


def test_extract_sequence_strand_awareness():
    fasta = DummyFasta({"chr": "ACGTAC"})
    assert extract_sequence(fasta, "chr", 1, 4, "+") == "ACGT"
    assert extract_sequence(fasta, "chr", 1, 4, "-") == revcomp("ACGT")


def test_extract_cds_orders_segments_and_strand():
    fasta = DummyFasta({"chr": "ATGCGTACGT"})
    segments = [
        ("chr", 1, 4, "+", 0, "tx1"),
        ("chr", 5, 7, "+", 0, "tx1"),
    ]
    cds = extract_cds(segments, fasta)
    assert cds == "ATGCGTA"

    neg_segments = [
        ("chr", 5, 7, "-", 0, "tx2"),
        ("chr", 1, 4, "-", 0, "tx2"),
    ]
    cds_neg = extract_cds(neg_segments, fasta)
    assert cds_neg == revcomp("ATGCGTA")

