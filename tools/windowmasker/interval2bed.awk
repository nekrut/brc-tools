# NCBI dustmasker/windowmasker `-outfmt interval` -> BED3 (chrom, start, end).
# interval format: ">seqid" header lines, then "from - to". Start clamped to >=0.
# (content for cols 4-6 is added downstream by lc_classify.py)
BEGIN { OFS = "\t" }
/^>/  { c = substr($1, 2); next }
/[0-9]+ *- *[0-9]+/ { gsub(/-/, " "); s = $1 - 1; if (s < 0) s = 0; print c, s, $2 }
