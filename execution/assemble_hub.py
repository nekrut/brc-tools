#!/usr/bin/env python3
"""Out-of-band assembly of the Pv4 UCSC assembly hub from the K-final outputs."""
import os,json,urllib.request,shutil
KEY=os.environ["GALAXY_API_KEY"]; BASE="http://localhost:8080"
KH="b701da857886499b"; HUB="/media/anton/hd2/galaxy_AtoK/K/hub"
def api(p): return json.load(urllib.request.urlopen(urllib.request.Request(BASE+p,headers={"x-api-key":KEY})))
def dl(dsid,dest):
    data=urllib.request.urlopen(urllib.request.Request(BASE+f"/api/datasets/{dsid}/display",headers={"x-api-key":KEY})).read()
    open(dest,"wb").write(data)
def coll_elems(cid):
    d=api(f"/api/histories/{KH}/contents/dataset_collections/{cid}?instance_type=history")
    return {e["element_identifier"]:e["object"]["id"] for e in d["elements"]}
# invocation outputs
inv=api(f"/api/invocations?history_id={KH}")[0]["id"]; iv=api(f"/api/invocations/{inv}")
DS=iv["outputs"]; CO=iv["output_collections"]
strains=["PvP01","PvW1","PAM","PvT01","MHC087"]; targets=strains[1:]
if os.path.exists(HUB): shutil.rmtree(HUB)
os.makedirs(HUB)
# hub.txt
open(f"{HUB}/hub.txt","w").write(
"hub Pv4_pangenome\nshortLabel Pv4 pangenome\nlongLabel Pv4 5-strain P. vivax pangenome (A->K Galaxy pipeline)\n"
"genomesFile genomes.txt\nemail anton@nekrut.org\n")
# genomes.txt (downloaded)
dl(DS["genomes_txt"]["id"], f"{HUB}/genomes.txt")
# per-genome dirs + 2bit + groups + description
twob=coll_elems(CO["twobit_track"]["id"])
for s in strains:
    os.makedirs(f"{HUB}/{s}",exist_ok=True)
    dl(twob[s], f"{HUB}/{s}/{s}.2bit")
    open(f"{HUB}/{s}/groups.txt","w").write("name annotation\nlabel Annotation\npriority 1\ndefaultIsClosed 0\n\nname comparative\nlabel Comparative\npriority 2\ndefaultIsClosed 0\n")
    open(f"{HUB}/{s}/description.html","w").write(f"<h2>{s}</h2><p>Pv4 panel strain {s}.</p>")
    if s!="PvP01": open(f"{HUB}/{s}/trackDb.txt","w").write("")  # no tracks on non-ref genomes
# PvP01 tracks
P=f"{HUB}/PvP01"
bigmaf=coll_elems(CO["bigmaf_track"]["id"]); dl(bigmaf["PvP01"], f"{P}/multiz.bb")
annot=coll_elems(CO["annotation_track"]["id"]); dl(annot["PvP01"], f"{P}/annotation.bb")
dl(DS["selection_strict_track"]["id"], f"{P}/selection_strict.bb")
dl(DS["selection_relaxed_track"]["id"], f"{P}/selection_relaxed.bb")
dl(DS["orthogroup_track"]["id"], f"{P}/orthogroup.bb")
chains=coll_elems(CO["bigchain_track"]["id"]); links=coll_elems(CO["biglink_track"]["id"])
for t in targets:
    dl(chains[f"PvP01.{t}"], f"{P}/chain_{t}.bb"); dl(links[f"PvP01.{t}"], f"{P}/link_{t}.bb")
# PvP01 trackDb.txt
tdb=[]
tdb.append("track multiz\nshortLabel Multiz\nlongLabel Multiz 5-way alignment (PvP01 ref)\ntype bigMaf\nbigDataUrl multiz.bb\nspeciesOrder PvW1 PAM PvT01 MHC087\nvisibility pack\n")
tdb.append("track annotation\nshortLabel Genes\nlongLabel PvP01 gene models\ntype bigBed 12\nbigDataUrl annotation.bb\nvisibility pack\n")
tdb.append("track selection_strict\nshortLabel BUSTED strict\nlongLabel BUSTED selection strict (min_intact=4)\ntype bigBed 12 +\nbigDataUrl selection_strict.bb\nvisibility dense\n")
tdb.append("track selection_relaxed\nshortLabel BUSTED relaxed\nlongLabel BUSTED selection relaxed (min_intact=3)\ntype bigBed 12 +\nbigDataUrl selection_relaxed.bb\nvisibility dense\n")
tdb.append("track orthogroups\nshortLabel Orthogroups\nlongLabel Orthogroup membership\ntype bigBed 12\nbigDataUrl orthogroup.bb\nvisibility dense\n")
for t in targets:
    tdb.append(f"track chain_{t}\nshortLabel Chain {t}\nlongLabel PvP01-{t} cleaned chain\ntype bigChain {t}\nbigDataUrl chain_{t}.bb\nlinkDataUrl link_{t}.bb\nvisibility hide\n")
open(f"{P}/trackDb.txt","w").write("\n".join(tdb))
print("hub assembled at",HUB)
os.system(f"find {HUB} -type f | sort")
