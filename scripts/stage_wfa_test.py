#!/usr/bin/env python3
"""Stage WF-A's input set on a Galaxy server: 23 assemblies, 7 proteomes, 2 anchors.

⛔ THE THREE COLLECTIONS ARE INDEPENDENT, AND CONFLATING THEM IS WHAT HELD WF-A TO SIX GENOMES.
They were all built from one dict, so `assemblies` could never be larger than the set with protein
FASTAs -- while WF-B masked 19. Nothing in the workflow joins them: `assemblies` feeds sourmash,
faidx and the identifier list, `proteomes` feeds BUSCO alone, `anchor_gene_gff3s` feeds anchor_prep
alone. The gates are therefore different, and only BUSCO needs an annotation.

⚠ NOTHING DOWNSTREAM COMPARES THEM EITHER. `proteomes` and `assemblies` meet only at multiqc, which
merges a BUSCO summary keyed by one collection's identifiers with plots keyed by the other's and
compares nothing -- scripts/check_workflow_ports.py says so in as many words. So the containments
are asserted HERE, before anything is uploaded: every proteome and every anchor must name a member
of the assembly set.

⛔ THE PROTEOMES ARE ONE PROTEIN PER GENE, WHICH IS NOT WHAT NCBI SHIPS. RefSeq publishes every
isoform and BUSCO's duplication figure is read straight off the file: cs10's 33,674 isoform records
beside the T2T pair's 31,109 one-per-gene records would report cs10 as massively duplicated for a
reason that is not biology. That matters more than cosmetics here, because eight panel members are
haplotype pairs where `duplicated` genuinely means an uncollapsed haplotype.

⚠ AND THE `_primary` FILES DO NOT ALL SHARE ONE RULE YET. The six NCBI ones took RefSeq's DESIGNATED
primary transcript -- their record counts equal NCBI's own protein_coding totals exactly, and the
records cs10 discards average 513 aa against the 438 aa kept, so it is not the longest isoform.
That designation does not exist in GenBank submitter annotations or in GigaDB's files, so
scripts/primary_proteome.py implements longest-per-gene, which needs only the FASTA. Cannbio-2 is
built with it; regenerating the two RefSeq files the same way is still owed.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys
import time
import urllib.request

#: Where the `_primary` proteome and anchor GFF3 files live. ⚠ NOT IN THIS REPOSITORY -- they are
#: several GB of NCBI downloads, so this points outside it and $WFA_PROTEOMES overrides. The script
#: refuses rather than staging a partial panel if a file is missing, because a collection that is
#: silently short is far worse than one that was never built.
PROTEOMES = pathlib.Path(os.environ.get("WFA_PROTEOMES", "proteomes")).expanduser()

#: ⚠ EXERCISED END TO END ON 2026-09-08, which is what this script was held back for. It staged
#: the six on usegalaxy.org (history bbd44e69cb8906b5527ce2de06686d41: 4 assemblies copied from the
#: raw panel, JL_Father and JL_Mother fetched from NCBI server-side, 6 proteomes and 2 anchors
#: uploaded, 14 datasets and 3 collections, all ok). WF-A UDT then ran to completion against that
#: input set on vgp -- invocation 5d295f4593883e8d, 19/19 jobs ok, all 13 outputs, with cs10's
#: anchor_bed12s at exactly the 40,185 rows udt/anchor_prep.gxtool.yml records.
#:
#: Where the resulting collection ids are written, for the workflow driver to read.
OUT_DIR = pathlib.Path(os.environ.get("WFA_OUT_DIR", ".")).expanduser()
RAW_HDCA = "cab4808ec6fe5c51"          # the staged 19-genome raw panel

#: Panel members the raw collection does NOT hold, so they are fetched by URL instead of copied.
#:
#: ⛔ WF-A INVENTORIES 23; WF-C MAY ALIGN A SUBSET, AND THE BOOKKEEPING MUST THEN BE REBUILT FOR
#: THAT SUBSET. `relabel_map` has n**2-n rows over whatever identifier list produced it -- 506 at 23
#: -- and WF-C's relabel step runs in strict mode, comparing that row count against the collection
#: it renames. Feed WF-C a 19-genome collection with the 23-genome map and Galaxy refuses the step
#: on the count (342 against 506). That is the desired behaviour, not a problem: `self_pairs` and
#: `relabel_map` are pure functions of an identifier list and are two small UDT jobs, so rebuild
#: them from the collection WF-C actually receives (scripts/regen_relabel_map.py), and
#: scripts/check_relabel_strict.py is what notices if they ever drift apart.
#:
#: ⚠ THIS DELIBERATELY RELAXES THE PANEL'S RECORDED CRITERION, which was "chromosome-level or
#: better" -- the raw collection's history is titled that way, and the two Jamaican Lion genomes are
#: Contig level. The reason given for the filter was that WindowMasker estimates its frequency model
#: from the assembly so fragmentation degrades the mask. Measured against NCBI, that used assembly
#: LEVEL as a proxy for fragmentation and the proxy is wrong here: contig N50 is 3.28 Mb (JL_Mother)
#: and 1.67 Mb (JL_Father) against cs10's 1.96 Mb. cs10 leads only on SCAFFOLD N50 (91.9 Mb), which
#: is scaffolding, not contiguity. The criterion to apply from here is contig N50.
#:
#: ⚠ FOUR EXTRAS, AND THREE OF THEM ARE A TRIO. NCBI's BioSample attributes make this a designed
#: cross rather than four copies of one plant: `JL_Father` (cultivar `Jamaican Lion ^4`, isolate
#: Father, male, ecotype **Type II**) x `JL_Mother` (same cultivar, isolate Mother, female, **Type
#: II**) -> `JL5` (same cultivar, isolate JL5, female, **Type III**). Two balanced-chemotype parents
#: and a CBD-dominant offspring is B-locus segregation in a family, which is what makes the trio
#: worth having for variation work: Mendelian checks, phasing, and a way to TEST a projected
#: annotation rather than only produce one. `JL_DASH` is a different cultivar (`Jamaican Lion DASH`,
#: The DASH DAO) and is here as an independent cross-group assembly, useful as an
#: assembly-discordance control rather than as part of the cross.
#:
#: All four clear the contig-N50 bar: JL_DASH 3.81 Mb, JL5 3.49 Mb, JL_Mother 3.28 Mb, JL_Father
#: 1.67 Mb, against cs10's 1.96 Mb. The four NCBI assemblies still excluded fail it outright --
#: ASM151000v1 at 2.6 kb over 311,039 sequences, Chemdog91_175268 at 2.2 kb over 190,122,
#: ASM209043v1 at 52 kb and ASM186575v1 at 129 kb.
PANEL_EXTRA = ("JL_Father", "JL_Mother", "JL5", "JL_DASH")

#: How many assemblies the finished collection must hold: the raw panel's 19 plus PANEL_EXTRA.
#: Asserted, because the panel collection is fetched at run time and a silently shorter one would
#: otherwise stage a short panel and report success.
EXPECTED_ASSEMBLIES = 23

#: element identifier -> assembly_name its proteome/GFF3 files are keyed by.
#:
#: ⛔ A SUBSET OF THE ASSEMBLIES, AND NO LONGER THE SAME TABLE. `proteomes` feeds ONE step, `busco`,
#: and BUSCO runs -m prot so it needs a protein FASTA; `assemblies` feeds sourmash, faidx and the
#: identifier list, which need nothing but sequence. Coupling the two through a single dict is what
#: held WF-A to 6 genomes while WF-B masked 19 -- not any property of the workflow, which never
#: joins the two collections.
#:
#: ⚠ SEVEN IS THE CEILING, AND THAT IS A FINDING RATHER THAN A GAP. A genus-wide NCBI sweep returns
#: 29 Cannabis assemblies and exactly SIX carry an annotation; there is no seventh annotated
#: assembly at NCBI. The pangenome paper reports ~35,000 genes per genome but its deposits publish
#: only targeted families (EDTA TEs, SV BEDs, cannabinoid synthases; TPS GFFs and NLR BEDs), and the
#: eight PUJ haplotypes' `*-cs10-copies-99.gff` are themselves projections FROM cs10. Cannbio-2 is
#: the one addition available anywhere: GigaDB publishes its full annotation. The other 14 panel
#: members get their genes from WF-C2 by projection, which is why those workflows exist.
PROTEOMES_FOR = {
    "cs10_NCBI_RefSeq_softmasked": "cs10",
    "ASM2916894v1": "ASM2916894v1",
    "T2T_GCA_054642775.1_IMPD": "ASM5464277v1",
    "T2T_GCA_054642815.1_IMPD": "ASM5464281v1",
    "JL_Father": "JL_Father",
    "JL_Mother": "JL_Mother",
    "Cannbio2_GigaDB": "Cannbio2",
}
#: URLs for the members not pre-staged. Everything has one, so a server holding nothing pre-staged
#: fetches all of them and gets identical bytes.
BY_URL = {
    "cs10_NCBI_RefSeq_softmasked": ("GCF_900626175.2", "cs10"),
    "ASM2916894v1": ("GCF_029168945.1", "ASM2916894v1"),
    "T2T_GCA_054642775.1_IMPD": ("GCA_054642775.1", "ASM5464277v1"),
    "T2T_GCA_054642815.1_IMPD": ("GCA_054642815.1", "ASM5464281v1"),
    "JL_Father": ("GCA_013030025.1", "JL_Father"),
    "JL_Mother": ("GCA_012923435.1", "JL_Mother"),
    "JL5": ("GCA_016415525.1", "JL5"),
    # ⚠ The assembly_name IS that long, and ncbi_fasta() builds the FTP path from it, so it has to
    # match NCBI's directory exactly. Verified: the URL returns 200.
    "JL_DASH": ("GCA_003660325.2", "Oct15_3.7Mb_N50_Jamaican_Lion_Assembly"),
}

#: ⛔ COPYING IS TRIED WHEREVER THE COLLECTION IS REACHABLE, NOT ONLY ON ONE SERVER. This was
#: `os.environ.get("WFA_SERVER", "") == ""`, i.e. gated on the EMPTY suffix -- so on vgp (`_2`)
#: `have` stayed empty and the script refused every identifier without a URL, even though creds()
#: below records that vgp SHARES MAIN'S DATABASE AND OBJECT STORE and the same collection id
#: resolves there. Ask the server rather than inferring from a variable.
#:
#: ⚠ AND THE PRE-STAGED COLLECTION IS REQUIRED, NOT AN OPTIMISATION -- the older comment here
#: claimed "everything has a URL, so a server that holds nothing pre-staged fetches all of them",
#: which is false and would have been read as a fallback that exists. BY_URL declares 8 of the 23:
#: the eight PUJ haplotypes come from Zenodo, Cannbio-2 from GigaDB, and six NCBI members never had
#: a URL written down. Without the collection this resolves to 8 and the EXPECTED_ASSEMBLIES check
#: refuses -- which is the right outcome, but for the opposite reason to the one recorded before.
COPY_IF_PRESENT = True
#: ⚠ ANCHORS ARE A SUBSET, AND THE WORKFLOW SAYS SO ("shorter than assemblies"). The two RefSeq
#: annotations are the curated ones; the T2T pair are submitter annotations, fine as targets but a
#: different provenance to mix into a reference set.
ANCHORS = {"cs10_NCBI_RefSeq_softmasked": "cs10", "ASM2916894v1": "ASM2916894v1"}


def creds() -> tuple[str, str]:
    """Server chosen by $WFA_SERVER: "" for usegalaxy.org, "_2" for vgp, "_3" for laila.

    ⚠ `_2` (vgp.usegalaxy.org) IS THE ONE TO REACH FOR ON A BIG PANEL. It has more resources
    dedicated to it than main, and it could not run user-defined tools at all until
    galaxyproject/usegalaxy-playbook#472 (deployed 2026-09-08) fixed two things: the app config
    lacked `enable_beta_tool_formats`, and its TPV had no destination accepting
    `tool_type_user_defined`, so an already-registered UDT was accepted at submit and then errored
    with exit_code None.

    ⚠ AND vgp SHARES MAIN'S DATABASE AND OBJECT STORE, so staging twice is waste: a history staged
    here against usegalaxy.org -- datasets and collections both -- is visible and usable from vgp by
    the same ids. Measured 2026-09-08.

    ⚠ ONE SCRIPT, TWO SERVERS, because the two staging runs must produce the SAME inputs. Forking it
    per server is how the collections quietly drift apart and a difference in the RESULT gets
    blamed on the workflow.
    """
    sfx = os.environ.get("WFA_SERVER", "")
    u = os.environ.get(f"GALAXY_URL{sfx}", "").rstrip("/")
    k = os.environ.get(f"GALAXY_API_KEY{sfx}", "")
    if not (u and k):
        sys.exit(f"set GALAXY_URL{sfx} and GALAXY_API_KEY{sfx}")
    print(f"  server {u}")
    return u, k


URL, KEY = creds()


def api(path, payload=None):
    r = urllib.request.Request(URL + path, method="POST" if payload is not None else "GET",
                               headers={"x-api-key": KEY, "content-type": "application/json"},
                               data=json.dumps(payload).encode() if payload is not None else None)
    with urllib.request.urlopen(r, timeout=900) as f:
        return json.load(f)


def upload(history: str, path: pathlib.Path, name: str, ext: str) -> str:
    """Upload a LOCAL file through /api/tools/fetch as multipart.

    ⛔ NOT bioblend's upload_file, AND NOT `upload1`. Both fail here, for different reasons worth
    recording:

      * bioblend uses the TUS protocol on any Galaxy >= 22.01 with no way to opt out, and the TUS
        endpoint Galaxy hands back is built from ITS OWN configured base URL -- `localhost:8080` on
        laila. Behind an SSH tunnel that address is the sandbox's own localhost, not Galaxy's, so
        every chunk goes nowhere. `TusUploadFailed ... Max retries exceeded`.
      * `upload1` is the classic upload tool and simply is not in laila's panel, which carries 63
        tools. `Tool not found`, 400014.

    /api/tools/fetch takes the file as a multipart part and the plan as a JSON string, and is
    present on both servers.

    ⚠ `trust_env=False` for the tunnel. host.docker.internal must NOT go through the sandbox's
    outbound proxy; usegalaxy.org must.
    """
    import requests
    local = "host.docker.internal" in URL or "localhost" in URL
    s = requests.Session()
    s.headers.update({"x-api-key": KEY})
    s.trust_env = not local
    targets = [{"destination": {"type": "hdas"},
                "elements": [{"src": "files", "name": name, "ext": ext,
                              "to_posix_lines": False, "space_to_tab": False}]}]
    last = None
    for attempt in range(5):
        try:
            with path.open("rb") as fh:
                r = s.post(f"{URL}/api/tools/fetch",
                           data={"history_id": history, "targets": json.dumps(targets)},
                           files={"files_0|file_data": (name, fh)}, timeout=3600)
            r.raise_for_status()
            outs = r.json().get("outputs") or []
            if not outs:
                raise RuntimeError(f"fetch returned no output: {r.text[:200]}")
            return outs[0]["id"]
        except Exception as exc:                                    # noqa: BLE001
            last = exc
            print(f"      upload {name} attempt {attempt+1} failed "
                  f"({type(exc).__name__}: {str(exc)[:90]}); retrying", flush=True)
            time.sleep(10 * (attempt + 1))
    raise SystemExit(f"upload {name}: gave up after 5 attempts -- {type(last).__name__}: {last}")


def ncbi_fasta(acc: str, name: str) -> str:
    prefix, num = acc.split("_")
    num = num.split(".")[0]
    safe = name.replace(" ", "_")
    return (f"https://ftp.ncbi.nlm.nih.gov/genomes/all/{prefix}/{num[0:3]}/{num[3:6]}/{num[6:9]}/"
            f"{acc}_{safe}/{acc}_{safe}_genomic.fna.gz")


def wait(ids, label):
    while True:
        st = {i: api(f"/api/datasets/{i}")["state"] for i in ids}
        bad = [i for i, s in st.items() if s == "error"]
        if bad:
            sys.exit(f"{label}: error on {bad}")
        # ⛔ `empty` IS NOT DONE. This used to accept it alongside `ok`, so a zero-byte upload or a
        # server-side fetch that returned nothing passed staging and went into a collection. At 23
        # members that is 23 chances instead of 6, and a panel one genome short is exactly the kind
        # of thing every guard downstream assumes has already been ruled out.
        bad_empty = [i for i, s in st.items() if s == "empty"]
        if bad_empty:
            sys.exit(f"{label}: {len(bad_empty)} dataset(s) staged EMPTY: {bad_empty}. A zero-byte "
                     f"member is not a staged member -- delete the history and retry rather than "
                     f"building a collection around it.")
        left = [i for i, s in st.items() if s != "ok"]
        if not left:
            return
        print(f"    {label}: {len(ids)-len(left)}/{len(ids)} ready", flush=True)
        time.sleep(20)


def one_file(pattern, ident, what):
    """The single file matching `pattern`, or a refusal that names what was being staged.

    ⛔ THIS WAS `next(PROTEOMES.glob(...))`, WHICH THE DOCSTRING ABOVE ALREADY PROMISED IT WAS NOT.
    A missing file raised an uncaught StopIteration -- a traceback with no mention of the genome or
    the pattern -- and TWO matching files silently took whichever the filesystem yielded first,
    which is how a panel ends up staged against the wrong proteome with nothing to show it.
    """
    hits = sorted(PROTEOMES.glob(pattern))
    if not hits:
        sys.exit(f"no {what} for {ident}: nothing matches {pattern!r} under {PROTEOMES}. Set "
                 f"$WFA_PROTEOMES if the files live elsewhere; a partial panel is worse than none.")
    if len(hits) > 1:
        sys.exit(f"{len(hits)} files match {pattern!r} for {ident}'s {what}: "
                 f"{[h.name for h in hits]}. Which one is intended is not something to guess at.")
    return hits[0]


def collection(history, name, pairs):
    return api(f"/api/histories/{history}/contents", {
        "type": "dataset_collection", "collection_type": "list", "name": name,
        "element_identifiers": [{"src": "hda", "id": i, "name": n} for n, i in pairs]})


def main() -> int:
    # ⚠ NAMED FROM THE ASSERTED CONSTANT, NOT A LITERAL. This said "(4 genomes)" for as long as the
    # panel had six in it -- the count was left behind when two genomes were added, and a history
    # whose label disagrees with its contents is read as the contents being wrong. EXPECTED_
    # ASSEMBLIES is checked against what actually resolves, below, so the label cannot drift again.
    hist = api("/api/histories",
               {"name": f"WF-A UDT edition — cannabis panel ({EXPECTED_ASSEMBLIES} genomes)"})["id"]
    print(f"  history {hist}")

    have = {}
    if COPY_IF_PRESENT:
        try:
            raw = api(f"/api/dataset_collections/{RAW_HDCA}?instance_type=history")
            have = {e["element_identifier"]: e["object"]["id"] for e in raw["elements"]}
        # ⚠ A DELIBERATE BROAD BOUNDARY: an unreachable pre-staged collection is not an error, it is
        # a server that has to fetch. Everything in BY_URL still resolves, so say so and carry on.
        except Exception as exc:                                             # noqa: BLE001
            print(f"  raw panel {RAW_HDCA} not reachable here ({type(exc).__name__}); "
                  f"fetching every member by URL instead")

    # ⛔ THE ASSEMBLY SET IS THE PANEL PLUS PANEL_EXTRA, DERIVED RATHER THAN LISTED. A second
    # hardcoded copy of the 19 identifiers would be a list that can disagree with the collection it
    # describes, and nothing would notice; the collection is the source of truth for its own
    # members.
    wanted = list(have) + [i for i in PANEL_EXTRA if i not in have]
    missing = [k for k in wanted if k not in have and k not in BY_URL]
    if missing:
        sys.exit(f"no source for {missing}: not in the raw panel and no URL declared")
    if len(wanted) != EXPECTED_ASSEMBLIES:
        sys.exit(f"the panel resolves to {len(wanted)} assemblies, expected "
                 f"{EXPECTED_ASSEMBLIES} ({len(have)} from {RAW_HDCA} + {len(PANEL_EXTRA)} extra). "
                 f"A silently shorter panel stages cleanly and every downstream count is then "
                 f"wrong, so this refuses rather than guessing which members went missing.")

    # ⛔ BOTH CONTAINMENTS, CHECKED BEFORE ANYTHING IS UPLOADED. Nothing in WF-A compares these
    # collections -- they meet only at multiqc, which joins a BUSCO summary keyed by one to plots
    # keyed by the other and compares nothing -- so a proteome or an anchor for a genome that is not
    # in the panel would run green and be attributed to a strain that is not there.
    stray_prot = sorted(set(PROTEOMES_FOR) - set(wanted))
    stray_anch = sorted(set(ANCHORS) - set(PROTEOMES_FOR))
    if stray_prot:
        sys.exit(f"PROTEOMES_FOR names {stray_prot}, which are not in the assembly set. BUSCO would "
                 f"report a completeness number for a genome the panel does not contain.")
    if stray_anch:
        sys.exit(f"ANCHORS names {stray_anch}, which have no proteome. An anchor must be a panel "
                 f"member with an annotation, since its GFF3 and its proteome come from the same "
                 f"annotation release.")

    asm = []
    for ident in wanted:
        if ident in have:
            d = api(f"/api/histories/{hist}/contents",
                    {"source": "hda", "content": have[ident], "type": "dataset"})
            asm.append((ident, d["id"]))
    print(f"  copied {len(asm)} assemblies from the staged panel")

    # ⚠ SERVER-SIDE FETCH, NOT AN UPLOAD. These two are not in the panel collection and their FASTAs
    # are not on this machine; Galaxy pulls them from NCBI directly, which costs no tunnel traffic.
    fetch = [{"src": "url", "url": ncbi_fasta(acc, nm), "name": ident, "ext": "fasta.gz",
              "to_posix_lines": False, "space_to_tab": False}
             for ident, (acc, nm) in BY_URL.items() if ident in wanted and ident not in have]
    if fetch:
        r = api("/api/tools/fetch", {"history_id": hist,
                                     "targets": [{"destination": {"type": "hdas"},
                                                  "elements": fetch}]})
        for o in r.get("outputs", []):
            asm.append((o["name"], o["id"]))
        print(f"  fetching {len(fetch)} assembly FASTA(s) from NCBI")

    prot, anch = [], []
    for ident, key in PROTEOMES_FOR.items():
        f = one_file(f"*_{key}_protein_primary.faa.gz", ident, "proteome")
        prot.append((ident, upload(hist, f, f"{ident}.faa.gz", "fasta.gz")))
        print(f"    uploaded proteome {ident}")
    for ident, key in ANCHORS.items():
        f = one_file(f"*_{key}_genomic.gff.gz", ident, "anchor GFF3")
        anch.append((ident, upload(hist, f, f"{ident}.gff3", "gff3")))
        print(f"    uploaded anchor   {ident}")

    wait([i for _, i in asm + prot + anch], "staging")

    c_asm = collection(hist, "assemblies", asm)
    c_prot = collection(hist, "proteomes", prot)
    c_anch = collection(hist, "anchor_gene_gff3s", anch)
    out = {"server": URL, "history": hist, "assemblies": c_asm["id"], "proteomes": c_prot["id"],
           "anchor_gene_gff3s": c_anch["id"]}
    print(f"\n  assemblies        {c_asm['id']}  ({len(asm)})")
    print(f"  proteomes         {c_prot['id']}  ({len(prot)})")
    print(f"  anchor_gene_gff3s {c_anch['id']}  ({len(anch)})")
    dest = OUT_DIR / f"wfa_inputs{os.environ.get('WFA_SERVER', '')}.json"
    dest.write_text(json.dumps(out, indent=1))
    print(f"  wrote {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
