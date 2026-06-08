# GPU chained-run setup + resume runbook

The host reboot (to fix the GPU driver) will kill the Claude session. This is the
authoritative resume doc. After reboot, re-launch `claude` and point it here.

## Current state (pre-reboot)
- Repo home: **`~/git/brc-tools`**, branch `main` @ `79ca459` (pushed to `nekrut/brc-tools`).
- 35 tools planemo-green @ profile 26.0; 11 workflows compose e2e. Galaxy local_tool_conf
  points at `brc-tools/tools`.
- Galaxy: `cd ~/galaxy && GALAXY_SKIP_CLIENT_BUILD=1 ./run.sh --daemon` (stop: `./run.sh stop`).
  Admin/user keys in `~/git/pangenome_tools_wfs/.env`.
- Source archive: `~/git/pangenome_tools_wfs` (branch `galaxy-port-wrappers`).
- **Disks:** `/` (nvme0n1p2) 937G **99% full (~17G)**; **`/media/anton/hd2` (nvme1n1) 800G free, fast** → use for staging; `/media/anton/<sda1>` 2.9T HDD → bulk.
- Staging dirs already created on hd2: `galaxy_staging/{objects,jobs,tmp,cache}`, `nextflow_work`, `docker`.
- `toga2:local` Docker image (20G) lives in `/var/lib/docker` on `/`.

## Step 1 — relocate Docker to hd2 (root; frees tens of GB on /)
```bash
sudo systemctl stop docker docker.socket
sudo rsync -aP /var/lib/docker/ /media/anton/hd2/docker/        # migrate images incl toga2:local
echo '{ "data-root": "/media/anton/hd2/docker" }' | sudo tee /etc/docker/daemon.json
sudo systemctl start docker
docker images toga2:local          # confirm it survived the move
df -h /                            # / should have reclaimed the docker space
```

## Step 2 — GPU driver (root)
```bash
nvidia-smi                         # MUST list the GPU after reboot (was NVML mismatch)
# enable docker GPU access:
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker run --rm --gpus all ubuntu nvidia-smi   # MUST show the GPU inside a container
```

## Step 3 — point Galaxy staging at hd2 (edit ~/galaxy/config/galaxy.yml, under `galaxy:`)
```yaml
  file_path: /media/anton/hd2/galaxy_staging/objects
  new_file_path: /media/anton/hd2/galaxy_staging/tmp
  job_working_directory: /media/anton/hd2/galaxy_staging/jobs
```
(Old test datasets under `~/galaxy/database/` become inert — fine, they're disposable.)
Then restart Galaxy (Step 5 command).

## Step 4 — add a GPU job destination + route KegAlign
In `~/galaxy/config/job_conf.xml` (or the YAML job conf in use; mirror in repo:
`galaxy_config_job_conf.xml`) add a docker destination that passes the GPU, and route kegalign/batched_lastz to it:
```xml
<destination id="docker_gpu" runner="local">
  <param id="docker_enabled">true</param>
  <param id="docker_run_extra_arguments">--gpus all</param>
  <param id="docker_sudo">false</param>
  <env id="GALAXY_SLOTS">16</env>
</destination>
<!-- under <tools>: -->
<tool id="kegalign" destination="docker_gpu"/>
<tool id="batched_lastz" destination="docker_gpu"/>
```
Set `new_file_path`/tmp for jobs to hd2 too if the destination overrides tmp.

## Step 5 — restart Galaxy
```bash
cd ~/galaxy && ./run.sh stop ; GALAXY_SKIP_CLIENT_BUILD=1 ./run.sh --daemon
# wait for up:
curl -s localhost:8080/api/version
```

## Step 6 — install KegAlign (Tool Shed: owner richard-burhans, name kegalign)
KegAlign is on the **main Tool Shed** (`richard-burhans/kegalign`, GPU WGA; the two
tool ids WF-C uses are `kegalign` + `batched_lastz`). It was "not yet approved" — if
`shed-tools` can't find it by category, install by exact owner/name:
```bash
source ~/git/pangenome_tools_wfs/.env
shed-tools install -g http://localhost:8080 -a $GALAXY_API_KEY \
  -t toolshed.g2.bx.psu.edu --owner richard-burhans --name kegalign
# verify:
curl -s -H "x-api-key: $GALAXY_API_KEY" 'localhost:8080/api/tools?in_panel=false' | grep -i kegalign
```

## Step 7 — chained A→K run (Claude drives this)
Once GPU + KegAlign + hd2 staging are confirmed, resume Claude and have it run the
full pipeline on test_data, phase by phase, into one history:
A inventory → B softmask → C align_chain_project (KegAlign GPU + Liftoff + **TOGA2**
`toga2:local`, Nextflow workdir on `/media/anton/hd2/nextflow_work`) → D pggb →
E consensus → F msa → G trees → H selection → I multiz → J vcf_projection → K ucsc_hub.
Heavy steps to watch: TOGA2 (Nextflow, point `NXF_WORK`/tmp at hd2), multiz (RAM-bound),
pggb. Each phase's gxformat2 is in `workflows/<phase>/`; some need the editor/API map-over
staging per `ONE-CLICK-READINESS.md`.

## Open caveats to carry in
- `toga2:local` is local-only (pin a public digest before any non-local deploy).
- bcftools_sort installed is old `greg/1.4.0`; hyphy_busted has no `--srv` param (IUC 2.5.96).
- File the IUC liftoff `-f` bug (passes free text as a file path).
- Tool Shed publish of the 24 new tools + the 9 26.0 bumps is still pending (`planemo shed_update`).
