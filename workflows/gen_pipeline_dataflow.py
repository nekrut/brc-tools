#!/usr/bin/env python3
"""Generate workflows/pipeline_dataflow.html — an ERD-style data-flow diagram of
the Pv4 pipeline (workflows A→K), showing which output of one workflow feeds which
input of another.

Node lists (each workflow's inputs/outputs) are parsed live from the workflow
files, so they stay in sync automatically. The inter-workflow EDGES are curated
below (they encode cross-workflow data semantics that can't be auto-derived from
a single file) and are VALIDATED against the parsed ports: if a workflow renames
or drops a port that an edge references, this script exits non-zero — which is the
CI gate that keeps the diagram honest.

Run:  python workflows/gen_pipeline_dataflow.py   (needs PyYAML)
"""
import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# id -> (relative file, phase letter, column index, short title)
WF_META = {
    "A":  ("workflows/inventory/inventory.gxwf.yml",                     "A",  0, "WF-A inventory"),
    "B":  ("workflows/softmask/softmask.gxwf.yml",                       "B",  0, "WF-B softmask"),
    "C":  ("workflows/align_chain_project/align_chain.gxwf.yml",         "C",  1, "WF-C align_chain"),
    "C2": ("workflows/align_chain_project/project_annotations.gxwf.yml", "C2", 1, "WF-C2 project_annotations"),
    "D":  ("workflows/pggb-pangenome-build/pggb-pangenome-build.ga",     "D",  1, "WF-D pggb"),
    "E":  ("workflows/consensus/consensus.gxwf.yml",                     "E",  2, "WF-E consensus_orthology"),
    "I":  ("workflows/multiz/multiz.gxwf.yml",                           "I",  2, "WF-I multiz"),
    "J":  ("workflows/vcf_projection/vcf_projection.gxwf.yml",           "J",  2, "WF-J vcf_projection"),
    "F":  ("workflows/msa/msa.gxwf.yml",                                 "F",  3, "WF-F msa"),
    "G":  ("workflows/trees/trees.gxwf.yml",                             "G",  4, "WF-G trees"),
    "H":  ("workflows/selection/selection.gxwf.yml",                     "H",  4, "WF-H selection"),
    "K":  ("workflows/ucsc_hub/ucsc_hub.gxwf.yml",                       "K",  5, "WF-K ucsc_hub"),
}

COLNAMES = [
    "Phase A–B\n(inventory · mask)",
    "Phase C · C2 · D\n(align · project · graph)",
    "Phase E · I · J\n(orthology · multiz · vcf)",
    "Phase F\n(MSA)",
    "Phase G · H\n(trees · selection)",
    "Phase K\n(UCSC hub)",
]

COL = {
    "A": "#2563eb", "B": "#0891b2", "C": "#7c3aed", "C2": "#9333ea", "D": "#db2777",
    "E": "#059669", "F": "#65a30d", "G": "#ca8a04", "H": "#ea580c", "I": "#0d9488",
    "J": "#4f46e5", "K": "#dc2626",
}

# Curated inter-workflow data edges: (from_wf, from_output, to_wf, to_input)
# Source = each consuming workflow's own input doc (e.g. WF-C masked_fastas "(WF-B)").
EDGES = [
    ("A", "sizes", "C", "sizes"),
    ("A", "self_pairs", "C", "self_pairs"),
    ("A", "relabel_map", "C", "relabel_map"),
    ("B", "softmasked_fasta", "C", "masked_fastas"),
    ("B", "softmasked_fasta", "C2", "query_masked"),
    ("B", "softmasked_fasta", "F", "ref_fasta"),
    ("B", "softmasked_fasta", "F", "query_fasta"),
    ("B", "softmasked_fasta", "J", "target_fastas"),
    ("C", "rbest_chains", "E", "rbest_chains"),
    ("C", "pairwise_axt", "I", "pairwise_axts"),
    ("C", "cleaned_chains", "J", "cleaned_chains"),
    ("C", "cleaned_chains", "K", "cleaned_chains"),
    ("C2", "classifications", "E", "c4_classifications"),
    ("C2", "merged_annotations", "F", "query_gff"),
    ("C2", "merged_annotations", "K", "annotation_gffs"),
    ("D", "odgi_og", "E", "graph"),
    ("A", "similarity_matrix", "I", "compare_csv"),
    ("A", "sizes", "I", "target_sizes"),
    ("A", "sizes", "I", "query_sizes"),
    ("E", "ortholog_table", "F", "ortholog_table"),
    ("E", "ortholog_table", "K", "ortholog_table"),
    ("F", "codon_alignments_clean", "G", "codon_alignments"),
    ("F", "codon_alignments", "H", "codon_alignments"),
    ("G", "treefiles", "H", "treefiles"),
    ("H", "busted_json", "K", "busted_strict"),
    ("H", "busted_json", "K", "busted_relaxed"),
    ("I", "multiz_mafs", "K", "multiz_mafs"),
]


def slug(s):
    return re.sub(r"_+", "_", re.sub(r"[^0-9a-zA-Z]+", "_", s)).strip("_").lower()


def parse_workflow(path):
    """Return (inputs[(name,doc)], outputs[(name,doc)]) for a .gxwf.yml or .ga."""
    full = os.path.join(ROOT, path)
    if path.endswith(".ga"):
        d = json.load(open(full))
        ins, outs = [], []
        for s in d.get("steps", {}).values():
            if s.get("type") in ("data_input", "data_collection_input"):
                lbl = s.get("label") or s.get("annotation") or ""
                if lbl:
                    ins.append((slug(lbl), lbl))
            for o in s.get("workflow_outputs", []):
                lbl = o.get("label") or o.get("output_name") or ""
                if lbl:
                    outs.append((slug(lbl), lbl))
        return ins, outs
    d = yaml.safe_load(open(full))
    ins = [(k, (v.get("doc", "") if isinstance(v, dict) else "").strip())
           for k, v in (d.get("inputs") or {}).items()]
    outs = [(k, (v.get("doc", "") if isinstance(v, dict) else "").strip())
            for k, v in (d.get("outputs") or {}).items()]
    return ins, outs


def main():
    wf = {}
    for wid, (path, ph, col, title) in WF_META.items():
        ins, outs = parse_workflow(path)
        wf[wid] = {"ph": ph, "col": col, "title": title, "ins": ins, "outs": outs,
                   "in_names": {n for n, _ in ins}, "out_names": {n for n, _ in outs}}

    # ---- validate edges against parsed ports (CI gate) ----
    errs = []
    for f, fo, t, ti in EDGES:
        if f not in wf:
            errs.append(f"edge from unknown workflow {f}")
        elif fo not in wf[f]["out_names"]:
            errs.append(f"{f} has no output '{fo}' (edge -> {t}.{ti})")
        if t not in wf:
            errs.append(f"edge to unknown workflow {t}")
        elif ti not in wf[t]["in_names"]:
            errs.append(f"{t} has no input '{ti}' (edge from {f}.{fo})")
    if errs:
        print("EDGE VALIDATION FAILED — workflow ports changed; update EDGES in this script:", file=sys.stderr)
        for e in errs:
            print("  -", e, file=sys.stderr)
        sys.exit(1)

    connected = set()
    for f, fo, t, ti in EDGES:
        connected.add(("out", f, fo))
        connected.add(("in", t, ti))

    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    def card(wid):
        w = wf[wid]
        c = COL[wid]
        r = [f'<div class="hdr" style="background:{c}"><span class="badge">{w["ph"]}</span>{esc(w["title"])}</div>',
             '<div class="body"><div class="sec-lbl">inputs</div>']
        for name, doc in w["ins"]:
            conn = ("in", wid, name) in connected
            cls = "port in" + ("" if conn else " raw")
            tip = f' title="{esc(doc)}"' if doc else ""
            tag = "" if conn else '<span class="ext">ext</span>'
            r.append(f'<div class="{cls}"{tip}><span class="dot in" id="port|{wid}|in|{name}" style="--c:{c}"></span>'
                     f'<span class="pn">{esc(name)}</span>{tag}</div>')
        r.append('<div class="sec-lbl">outputs</div>')
        for name, doc in w["outs"]:
            conn = ("out", wid, name) in connected
            cls = "port out" + ("" if conn else " term")
            tip = f' title="{esc(doc)}"' if doc else ""
            r.append(f'<div class="{cls}"{tip}><span class="pn">{esc(name)}</span>'
                     f'<span class="dot out" id="port|{wid}|out|{name}" style="--c:{c}"></span></div>')
        r.append("</div>")
        return f'<div class="card" data-wf="{wid}">' + "".join(r) + "</div>"

    cols = {}
    for wid in WF_META:
        cols.setdefault(wf[wid]["col"], []).append(wid)
    colhtml = []
    for ci in sorted(cols):
        cards = "".join(card(w) for w in cols[ci])
        colhtml.append(f'<div class="col"><div class="coltitle">{COLNAMES[ci]}</div>{cards}</div>')

    edges_js = json.dumps([{"from": f, "fp": fo, "to": t, "tp": ti} for f, fo, t, ti in EDGES])
    wfcolor_js = json.dumps({w: COL[w] for w in WF_META})

    html = TEMPLATE.format(cols="".join(colhtml), edges=edges_js, wfcolor=wfcolor_js,
                           nwf=len(WF_META), nedge=len(EDGES))
    out = os.path.join(ROOT, "workflows/pipeline_dataflow.html")
    open(out, "w").write(html)
    print(f"wrote workflows/pipeline_dataflow.html ({len(html)} bytes) — {len(WF_META)} workflows, {len(EDGES)} edges")


TEMPLATE = r'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pv4 pipeline — workflow data flow</title>
<style>
:root{{--bg:#0f172a;--panel:#1e293b;--ink:#e2e8f0;--mut:#94a3b8;--line:#334155}}
*{{box-sizing:border-box}}
body{{margin:0;font:13px/1.4 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink)}}
header{{padding:14px 22px;border-bottom:1px solid var(--line);position:sticky;top:0;background:#0b1220;z-index:30;display:flex;gap:18px;align-items:baseline;flex-wrap:wrap}}
header h1{{font-size:17px;margin:0;font-weight:650}}
header .sub{{color:var(--mut);font-size:12px}}
.legend{{margin-left:auto;display:flex;gap:14px;align-items:center;color:var(--mut);font-size:11px}}
.legend .k{{display:flex;gap:5px;align-items:center}}
.legend .sw{{width:22px;height:0;border-top:2px solid #64748b}}
.legend .ddot{{width:9px;height:9px;border-radius:50%;border:2px solid #64748b}}
.legend .ddot.f{{background:#64748b}}
#canvas{{position:relative;overflow:auto;padding:26px;min-height:calc(100vh - 56px)}}
#edges{{position:absolute;top:0;left:0;pointer-events:none;z-index:1}}
.cols{{position:relative;z-index:2;display:flex;gap:74px;align-items:flex-start}}
.col{{display:flex;flex-direction:column;gap:22px;min-width:230px}}
.coltitle{{color:var(--mut);font-size:11px;text-transform:uppercase;letter-spacing:.06em;white-space:pre-line;text-align:center;margin-bottom:2px}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:10px;overflow:hidden;box-shadow:0 6px 18px rgba(0,0,0,.35);transition:box-shadow .15s}}
.card.dim{{opacity:.28}}
.card.hot{{box-shadow:0 0 0 2px var(--hot,#fff),0 10px 26px rgba(0,0,0,.5)}}
.hdr{{color:#fff;font-weight:650;padding:7px 11px;display:flex;align-items:center;gap:8px;font-size:13px}}
.badge{{background:rgba(255,255,255,.22);border-radius:6px;padding:1px 7px;font-size:11px;font-weight:700}}
.body{{padding:6px 0 8px}}
.sec-lbl{{color:var(--mut);font-size:9.5px;text-transform:uppercase;letter-spacing:.08em;padding:5px 12px 2px}}
.port{{display:flex;align-items:center;gap:7px;padding:2.5px 11px;cursor:default}}
.port .pn{{font-size:12px}}
.port.out{{justify-content:flex-end}}
.port.raw .pn,.port.term .pn{{color:var(--mut)}}
.ext{{font-size:9px;color:#64748b;border:1px solid #475569;border-radius:4px;padding:0 4px;margin-left:auto}}
.dot{{width:9px;height:9px;border-radius:50%;background:#0b1220;border:2px solid var(--c);flex:none}}
.port.raw .dot,.port.term .dot{{border-color:#475569}}
.dot.in{{margin-left:-15px}}
.dot.out{{margin-right:-15px}}
.path{{fill:none;stroke-width:2;opacity:.45;transition:opacity .15s,stroke-width .15s}}
.path.dim{{opacity:.05}}
.path.hot{{opacity:1;stroke-width:3.2}}
footer{{color:var(--mut);font-size:11px;padding:10px 22px 26px}}
footer code{{color:#cbd5e1}}
</style></head>
<body>
<header>
  <h1>Pv4 pangenome pipeline — workflow data flow</h1>
  <span class="sub">{nwf} workflows, {nedge} cross-workflow edges · hover a workflow to trace its links · hover a port for its doc</span>
  <div class="legend">
    <span class="k"><span class="ddot f"></span>connected port</span>
    <span class="k"><span class="ddot"></span>raw input / terminal output</span>
    <span class="k"><span class="sw"></span>data edge (colored by source)</span>
  </div>
</header>
<div id="canvas"><svg id="edges"></svg><div class="cols">{cols}</div></div>
<footer>Inter-workflow edges are data dependencies taken from each workflow's input docs (e.g. WF-C <code>masked_fastas</code> ← WF-B <code>softmasked_fasta</code>). “ext” = raw/external pipeline input. Auto-generated by <code>workflows/gen_pipeline_dataflow.py</code> from <code>workflows/*/*.gxwf.yml</code> + <code>pggb-pangenome-build.ga</code> — do not edit by hand.</footer>
<script>
const EDGES={edges}, WFCOLOR={wfcolor};
function draw(){{
  const cv=document.getElementById('canvas'), svg=document.getElementById('edges');
  svg.setAttribute('width',cv.scrollWidth); svg.setAttribute('height',cv.scrollHeight);
  const cr=cv.getBoundingClientRect(); svg.innerHTML='';
  const ns='http://www.w3.org/2000/svg';
  EDGES.forEach(e=>{{
    const a=document.getElementById('port|'+e.from+'|out|'+e.fp), b=document.getElementById('port|'+e.to+'|in|'+e.tp);
    if(!a||!b) return;
    const ar=a.getBoundingClientRect(), br=b.getBoundingClientRect();
    const x1=ar.left+ar.width/2-cr.left+cv.scrollLeft, y1=ar.top+ar.height/2-cr.top+cv.scrollTop;
    const x2=br.left+br.width/2-cr.left+cv.scrollLeft, y2=br.top+br.height/2-cr.top+cv.scrollTop;
    const dx=Math.max(48,Math.abs(x2-x1)*0.45);
    const p=document.createElementNS(ns,'path');
    p.setAttribute('d',`M${{x1}},${{y1}} C${{x1+dx}},${{y1}} ${{x2-dx}},${{y2}} ${{x2}},${{y2}}`);
    p.setAttribute('class','path'); p.setAttribute('stroke',WFCOLOR[e.from]);
    p.dataset.from=e.from; p.dataset.to=e.to; svg.appendChild(p);
  }});
}}
function hover(wf){{
  document.querySelectorAll('.card').forEach(c=>c.classList.remove('hot','dim'));
  document.querySelectorAll('.path').forEach(p=>p.classList.remove('hot','dim'));
  if(!wf) return;
  const linked=new Set([wf]);
  EDGES.forEach(e=>{{ if(e.from===wf||e.to===wf){{linked.add(e.from);linked.add(e.to);}} }});
  document.querySelectorAll('.card').forEach(c=>{{
    const w=c.dataset.wf;
    if(w===wf){{c.classList.add('hot'); c.style.setProperty('--hot',WFCOLOR[w]);}}
    else if(!linked.has(w)) c.classList.add('dim');
  }});
  document.querySelectorAll('.path').forEach(p=>{{
    if(p.dataset.from===wf||p.dataset.to===wf) p.classList.add('hot'); else p.classList.add('dim');
  }});
}}
document.querySelectorAll('.card').forEach(c=>{{
  c.addEventListener('mouseenter',()=>hover(c.dataset.wf));
  c.addEventListener('mouseleave',()=>hover(null));
}});
window.addEventListener('resize',draw);
window.addEventListener('load',()=>setTimeout(draw,60));
draw(); setTimeout(draw,200);
</script>
</body></html>'''


if __name__ == "__main__":
    main()
