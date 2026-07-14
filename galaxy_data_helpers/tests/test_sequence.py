from pathlib import Path

from galaxy_data_helpers.sequence import (
    classify_bed_interval,
    classify_repeat_signature,
    load_fasta_as_dict,
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
