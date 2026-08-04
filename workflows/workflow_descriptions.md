<!--
Prose for workflows/pipeline_io_map.html. Edit this file, then regenerate:

    python workflows/gen_pipeline_io_map.py

One `## <id>` section per workflow, where <id> matches an entry in VETTED in the
generator. Each needs a `### summary` (one line, shown in the Port detail
section) and a `### description` (the plain-language paragraph shown above the
diagram). Blank lines start a new paragraph. Inline **bold**, *italic*, `code`
and [links](https://example.org) work.
-->

# Workflow descriptions


## A

<!-- WF-A inventory -->

### summary

Panel inventory: sourmash sketch/compare for pairwise similarity, BUSCO for per-strain
completeness, and the derived panel bookkeeping (sizes, self-pairs, relabel map) that
WF-C needs — generated in-workflow rather than hand-authored.


### description

Before aligning anything, you want to know what is actually in the panel: how similar
the genomes are to each other, and whether any of them is missing a chunk of its gene
content. This workflow answers both. It takes the genome sequences and their protein
sets. It compares every genome against every other with sourmash, which comes to a
similarity score from shared k-mers without doing an alignment, so it is fast even on
whole genomes. Separately it runs BUSCO, which asks how many of the several hundred
genes expected to be present in exactly one copy in this clade can be found in each
strain. What comes out is an all-against-all similarity matrix with a clustered heatmap
and a tree, a completeness score per strain, and one QC report holding both. It also
writes the small bookkeeping files the alignment step needs later (chromosome lengths,
the list of genome pairs), so nobody has to make those by hand. The point is to catch a
bad assembly or an unexpected outlier here, before spending days of compute on it. On
the Pv4 panel it did exactly that: PvSY56 sits at about 0.24 similarity to everything
else while the rest sit at 0.63 to 0.70, and MHC087 came back only 87% complete.


## B

<!-- WF-B softmask -->

### summary

Soft-masking: four maintained low-complexity maskers run in parallel, each emitting a
content-annotated BED6 hub track; their union soft-masks the assembly.


### description

Genomes are full of repetitive and low-complexity sequence: homopolymer runs, short
tandem repeats, satellite arrays. Align without handling it and those regions generate
enormous numbers of meaningless matches, because a stretch of AT repeats matches every
other stretch of AT repeats in the genome. This workflow finds that sequence and
lowercases it. Lowercasing rather than cutting is deliberate: the bases stay where they
are, so every coordinate downstream is unchanged and nothing is lost, while alignment
tools that honour soft-masking can avoid seeding matches inside them. It takes the raw
genomes and runs four independent repeat finders over each one, then merges everything
any of them flagged and lowercases the union. Four tools rather than one because they
disagree with each other, and taking the union is the conservative choice. What comes
out is the soft-masked genome set that every later step uses, one browser track per tool
showing what it flagged and what kind of repeat it is, and a table of how much of each
genome each tool masked.


## C

<!-- WF-C align_chain -->

### summary

Pairwise alignment and chaining across the full ordered strain grid: KegAlign/LASTZ →
axtChain → chainNet → netChainSubset → reciprocal-best, one-click via native collection
operations.


### description

To compare two genomes you first have to establish which piece of one corresponds to
which piece of the other. This workflow aligns every genome against every other, all 56
ordered pairs for 8 genomes, and then assembles the thousands of short local alignments
into chains and nets. A chain is a run of alignments in consistent order and
orientation; the netting step picks the best chain for each region and discards the
rest. That turns a haystack of local hits into a statement about large-scale
correspondence, so a real inversion or translocation shows up as structure rather than
disappearing into noise. It takes the soft-masked genomes and their chromosome lengths.
What comes out is, for each ordered pair, the cleaned chains, the raw pairwise
alignments, and a reciprocal-best set, which keeps only the cases where two regions are
each other's best match. That reciprocal condition matters: it is the difference between
two regions being genuinely the same locus in two strains, and one of them being a
paralog elsewhere in the genome. This is by far the most expensive step, and the
alignment runs on a GPU.


## C2

<!-- WF-C2 project_annotations -->

### summary

Annotation projection: each anchor's curated genes are lifted onto every other strain
with Liftoff, then triaged and merged into a per-pair classification.


### description

Most genomes in a panel have no gene annotation worth trusting. This workflow borrows
one. Each anchor genome comes with a curated set of gene models, and those genes are
carried across the alignment onto every other genome: wherever the alignment says a
stretch of anchor sequence corresponds to a stretch of query sequence, the gene is
placed there. It takes the anchor genomes with their gene models, the genomes being
annotated, and the soft-masked sequence. Every projected gene is then examined, because
a gene landing somewhere is not the same as a gene surviving: the check asks whether it
still has an intact reading frame, or whether it is interrupted by a premature stop,
shifted out of frame, or missing exons. What comes out, for each anchor and query
combination, is a GFF3 of the projected genes and a table classifying each one as intact
or lost. That classification is the raw evidence the orthology step downstream uses to
decide which genes are shared across the whole panel. One limitation to be clear about:
this is projection, not gene finding. A gene present in a query genome but absent from
every anchor cannot be discovered this way.
