from galaxy_data_helpers.chains import iter_chains, parse_chain_header, project_gene


def test_parse_chain_header_valid_line():
    header = parse_chain_header(
        "chain 123 chrA 1000 + 100 200 chrB 900 - 300 400 1"
    )
    assert header["tName"] == "chrA"
    assert header["qStrand"] == "-"


def test_iter_chains_yields_blocks(tmp_path):
    chain_text = """chain 1 chrA 1000 + 0 100 chrB 1000 + 0 100 1\n50\n"""
    chain_file = tmp_path / "test.chain"
    chain_file.write_text(chain_text)
    headers = list(iter_chains(chain_file))
    assert len(headers) == 1
    header, blocks = headers[0]
    assert header["tName"] == "chrA"
    assert blocks[0][0:2] == (0, 50)


def test_project_gene_positive_and_negative():
    blocks = [(0, 50, 0, 50, "+"), (50, 100, 50, 100, "+")]
    aligned, qmin, qmax = project_gene(10, 60, blocks)
    assert aligned == 50
    assert (qmin, qmax) == (10, 60)

    neg_blocks = [(0, 50, 50, 100, "-")]
    aligned, qmin, qmax = project_gene(0, 50, neg_blocks)
    assert aligned == 50
    assert (qmin, qmax) == (50, 100)
