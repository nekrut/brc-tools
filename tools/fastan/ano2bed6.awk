# FASTGA ANOtoBED output (tab-separated; col1 = full FASTA header) -> BED6.
# ANOtoBED columns: <header>  beg  end  unit_size  identity  strand
#   name   = "u<unit_size>" (tandem-repeat unit length)
#   score  = identity, clamped 0-1000 (UCSC grayscale)
#   strand = + / - (real orientation), else .
BEGIN { FS = "\t"; OFS = "\t" }
/^#/  { next }
{
    split($1, a, " ")                       # chrom = first token of the header
    sc = $5; if (sc > 1000) sc = 1000; if (sc < 0) sc = 0
    st = $6; if (st != "+" && st != "-") st = "."
    print a[1], $2, $3, "u" $4, sc, st
}
