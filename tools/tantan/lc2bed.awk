# tantan soft-masked FASTA (low-complexity lower-cased) -> BED3 (chrom, start, end).
# Tracks absolute 0-based position within each record; emits maximal lowercase runs.
# (content for cols 4-6 is added downstream by lc_classify.py)
BEGIN { OFS = "\t"; st = -1 }
/^>/ { if (st >= 0) print c, st, pos; c = substr($1, 2); pos = 0; st = -1; next }
{
    n = length($0)
    for (i = 1; i <= n; i++) {
        ch = substr($0, i, 1); low = (ch >= "a" && ch <= "z")
        if (low) { if (st < 0) st = pos }
        else     { if (st >= 0) { print c, st, pos; st = -1 } }
        pos++
    }
}
END { if (st >= 0) print c, st, pos }
