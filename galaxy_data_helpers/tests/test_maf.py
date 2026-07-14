from galaxy_data_helpers.maf import species_of


def test_species_of_accession_with_version():
    assert species_of("GCA_900093555.2.LT635612.2") == "GCA_900093555.2"


def test_species_of_accession_gcf():
    assert species_of("GCF_001234567.1.chromosome") == "GCF_001234567.1"


def test_species_of_ucsc_species():
    assert species_of("musMusculus.chr1") == "musMusculus"


def test_species_of_single_token():
    assert species_of("PanTro4") == "PanTro4"
