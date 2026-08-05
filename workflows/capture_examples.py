#!/usr/bin/env python3
"""Capture real per-step example data from a verified Galaxy invocation.

The per-workflow tabs on the published page show, for every step, a sample of
what that step actually produced. Those samples come from a real run -- but the
GitHub Pages job that regenerates the site has no access to the Galaxy instance,
so the samples must be frozen into a file that lives in the repo. This script
does the freezing; workflows/gen_pipeline_io_map.py only reads the result.

Run it on the Galaxy head node, with GALAXY_URL and GALAXY_API_KEY exported
(source /mnt/ssd/pv4_full/configs/env.sh), whenever you want to refresh the
examples or add a workflow:

    python workflows/capture_examples.py A 3c9d8677020e7fdd

Writes workflows/examples/wf_<id>_examples.json. Previews are deliberately
small: a few lines of text, or a base64 image if it is under IMAGE_MAX bytes.
Nothing here should make the committed JSON large.
"""
import base64
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREVIEW_LINES = 12          # lines of text to keep per output
PREVIEW_CHARS = 1400        # hard cap on a text preview
IMAGE_MAX = 120_000         # embed images below this; above it, describe only

TEXTY = {"txt", "tabular", "csv", "tsv", "bed", "bed12", "gff3", "gff", "fasta",
         "fastqsanger", "json", "yaml", "interval", "chain", "maf", "data"}


def api(path):
    key = os.environ["GALAXY_API_KEY"]; url = os.environ["GALAXY_URL"]
    out = subprocess.check_output(
        ["curl", "-s", "--max-time", "60", "-H", f"x-api-key: {key}", f"{url}{path}"])
    return json.loads(out)


def fetch(path, binary=False):
    key = os.environ["GALAXY_API_KEY"]; url = os.environ["GALAXY_URL"]
    out = subprocess.check_output(
        ["curl", "-s", "--max-time", "120", "-H", f"x-api-key: {key}", f"{url}{path}"])
    return out if binary else out.decode("utf-8", "replace")


def preview(ds):
    """Return a small, display-ready sample of one dataset."""
    ext = (ds.get("file_ext") or "").lower()
    size = ds.get("file_size") or 0
    info = {"ext": ext, "bytes": size}

    if ext in ("png", "jpg", "jpeg", "gif"):
        if size and size <= IMAGE_MAX:
            # binary=True is essential: without it the bytes are decoded as UTF-8
            # with errors="replace", which silently corrupts every non-UTF8 byte
            # and yields an image that will not render.
            blob = fetch(f"/api/datasets/{ds['id']}/display", binary=True)
            if not blob.startswith(b"\x89PNG") and ext == "png":
                info["note"] = f"unexpected PNG header {blob[:8]!r} -- not embedded"
                return info
            info["image"] = (f"data:image/{'jpeg' if ext in ('jpg','jpeg') else ext};base64,"
                             + base64.b64encode(blob).decode())
        else:
            info["note"] = f"{ext.upper()} image, {size:,} bytes -- too large to embed"
        return info

    if ext in ("html", "htm"):
        info["note"] = (f"Self-contained HTML report, {size:,} bytes -- too large to inline here. "
                        f"It is produced as a workflow output; retrieve it from the run rather "
                        f"than from this page.")
        return info

    if ext in TEXTY or size < 200_000:
        try:
            txt = fetch(f"/api/datasets/{ds['id']}/display?to_ext={ext or 'txt'}")
        except Exception as e:
            info["note"] = f"could not read: {e}"
            return info
        lines = txt.splitlines()
        info["total_lines"] = len(lines)
        body = "\n".join(lines[:PREVIEW_LINES])
        if len(body) > PREVIEW_CHARS:
            body = body[:PREVIEW_CHARS] + "\n..."
        info["text"] = body
        info["truncated"] = len(lines) > PREVIEW_LINES
        return info

    info["note"] = f"{ext or 'binary'}, {size:,} bytes"
    return info


def main(wf_id, invocation):
    inv = api(f"/api/invocations/{invocation}")
    out = {"workflow": wf_id, "invocation": invocation,
           "history": inv.get("history_id"), "when": (inv.get("create_time") or "")[:10],
           "state": inv.get("state"), "steps": {}}

    for s in inv.get("steps", []):
        d = api(f"/api/invocations/{invocation}/steps/{s['id']}")
        label = d.get("workflow_step_label")
        if not label:
            continue
        entry = {"order": d.get("order_index"), "outputs": []}

        # steps that ran once have a job; map-over steps expose collections
        if d.get("job_id"):
            job = api(f"/api/jobs/{d['job_id']}?full=true")
            for name, o in (job.get("outputs") or {}).items():
                ds = api(f"/api/datasets/{o['id']}")
                entry["outputs"].append({"name": name, "kind": "dataset", **preview(ds)})
        for name, c in (d.get("output_collections") or {}).items():
            try:
                cc = api(f"/api/dataset_collections/{c['id']}?instance_type=history")
            except Exception:
                continue
            els = cc.get("elements") or []
            if not els:
                continue
            first = els[0]
            ds = api(f"/api/datasets/{first['object']['id']}")
            entry["outputs"].append({
                "name": name, "kind": "collection",
                "elements": len(els),
                "element_ids": [e["element_identifier"] for e in els],
                "shown": first["element_identifier"],
                **preview(ds)})
        if entry["outputs"]:
            out["steps"][label] = entry

    dest = os.path.join(ROOT, "workflows", "examples", f"wf_{wf_id.lower()}_examples.json")
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    size = os.path.getsize(dest)
    print(f"wrote {os.path.relpath(dest, ROOT)} -- {len(out['steps'])} steps with output, {size:,} bytes")
    for lbl, e in sorted(out["steps"].items(), key=lambda x: x[1]["order"]):
        kinds = ", ".join(f"{o['name']}({o.get('elements','1')})" for o in e["outputs"])
        print(f"   {e['order']:>2} {lbl:22} {kinds}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: capture_examples.py <WF_ID> <INVOCATION_ID>")
    main(sys.argv[1], sys.argv[2])
