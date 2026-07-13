"""GFF3 attribute parsing helpers for Galaxy tool wrappers."""


def parse_gff_attributes_to_dict(attr_str: str) -> dict:
    """Parse a GFF3 attribute string (column 9) into a dictionary.

    GFF3 attributes are semicolon-separated ``key=value`` pairs. The trailing
    semicolon, if present, is ignored. Empty values are preserved.

    Parameters
    ----------
    attr_str : str
        Raw ninth column of a GFF3 record.

    Returns
    -------
    dict
        Mapping of attribute key to value.

    Notes
    -----
    This is a minimal, strict parser used by the Liftoff triage and TOGA2
    merge tool wrappers. It does not unescape URL-encoded values; if that
    becomes required it should be added explicitly.
    """
    d = {}
    for kv in attr_str.strip().rstrip(";").split(";"):
        kv = kv.strip()
        if "=" in kv:
            key, value = kv.split("=", 1)
            d[key.strip()] = value.strip()
    return d
