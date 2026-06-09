#!/usr/bin/env bash
# Fix the post-reboot mount mismatch that stalled the A->K run (v2).
#
# Real diagnosis: docker is only ~3.2G at the default /var/lib/docker (the
# "93GB" was virtual layer-sum). The disk-full was Galaxy's job/staging dir
# eating the last ~16G of an already-97%-full /, because Galaxy was never
# restarted after the galaxy.yml staging edit -> it used ~/galaxy/database on /.
#
# Fix: mount the fast disk at /media/anton/hd2 (fstab UUID, survives reboots)
# and the 4T at /media/anton/samsung; point Galaxy staging there; keep docker
# put (just drop the stale data-root override so the hd2 remount can't break it).
#
# Run as root:  sudo bash /home/anton/git/brc-tools/execution/fix_disks.sh
set -euo pipefail

FAST_UUID=95976ecf-b95d-4cb8-8b07-ad76446c2eaf   # nvme1n1, 938G, fast
BULK_UUID=dd77cea1-6668-4500-bbfd-a0a895dc7621   # sda1, 3.6T
USER_NAME=anton
GROUP_NAME=anton

say() { printf '\n=== %s ===\n' "$1"; }
[[ $EUID -eq 0 ]] || { echo "run with sudo"; exit 1; }

# --- 1. stop docker; keep it on /var/lib/docker (drop stale data-root) -------
say "stopping docker"
systemctl stop docker docker.socket || true
sleep 2
say "reverting daemon.json to default root (docker stays at /var/lib/docker)"
if [[ -f /etc/docker/daemon.json ]]; then
  cp /etc/docker/daemon.json /etc/docker/daemon.json.bak
  # remove only the data-root key; keep any other settings
  python3 - <<'PY'
import json,os
p="/etc/docker/daemon.json"
d=json.load(open(p))
d.pop("data-root",None)
json.dump(d,open(p,"w"),indent=2)
print("daemon.json now:",d)
PY
fi

# --- 2. free the fast disk (hd21) so it can be remounted ---------------------
say "freeing /media/anton/hd21 (close nautilus, fully stop galaxy)"
pkill -u "$USER_NAME" nautilus 2>/dev/null || true
su - "$USER_NAME" -c 'cd ~/galaxy && ./run.sh stop' 2>/dev/null || true
# galaxyctl 'stop' leaves supervisord up; shut it down so nothing holds the disk
su - "$USER_NAME" -c 'cd ~/galaxy && .venv/bin/galaxyctl shutdown' 2>/dev/null || true
pkill -u "$USER_NAME" -f 'gravity/supervisor/supervisord' 2>/dev/null || true
sleep 2
fuser -km /media/anton/hd21 2>/dev/null || true   # last resort: kill remaining holders
sleep 1

say "unmounting auto-mounts"
umount /media/anton/hd21 || { echo "hd21 still busy -- run: sudo fuser -vm /media/anton/hd21"; exit 1; }
umount "/media/anton/dd77cea1-6668-4500-bbfd-a0a895dc7621" 2>/dev/null || true

# --- 3. fixed mountpoints ----------------------------------------------------
say "preparing mountpoints"
# /media/anton/hd2 is a near-empty dir on / (docker skeleton 320K, Pv4test 3G).
# Preserve Pv4test ground truth: it must live ON the fast disk after remount.
# Move it aside to /var/tmp first (only ~3G, / has 29G free), restore after mount.
if [[ -d /media/anton/hd2/Pv4test ]]; then
  rm -rf /var/tmp/Pv4test_hold
  mv /media/anton/hd2/Pv4test /var/tmp/Pv4test_hold
fi
rm -rf /media/anton/hd2
mkdir -p /media/anton/hd2 /media/anton/samsung

# --- 4. persist both mounts in /etc/fstab (UUID; survives reboots) -----------
say "writing fstab entries"
sed -i '/media\/anton\/hd2 /d;  /media\/anton\/samsung /d' /etc/fstab
{
  echo "UUID=$FAST_UUID /media/anton/hd2     ext4 defaults,nofail,x-systemd.device-timeout=10 0 2"
  echo "UUID=$BULK_UUID /media/anton/samsung ext4 defaults,nofail,x-systemd.device-timeout=10 0 2"
} >> /etc/fstab
systemctl daemon-reload
mount -a
mountpoint -q /media/anton/hd2     && echo "fast disk -> /media/anton/hd2 OK"     || { echo "hd2 mount FAILED"; exit 1; }
mountpoint -q /media/anton/samsung && echo "4T -> /media/anton/samsung OK"        || echo "samsung mount FAILED (check)"

# --- 5. restore Pv4test + create Galaxy staging dirs on the fast disk --------
say "restoring Pv4test + creating galaxy staging dirs on fast disk"
# The earlier rsync already placed a complete Pv4test on the fast disk; only
# restore the held copy if the fast disk lacks it. Otherwise discard the hold.
if [[ -d /var/tmp/Pv4test_hold ]]; then
  if [[ -d /media/anton/hd2/Pv4test ]]; then
    echo "Pv4test already on fast disk (from earlier rsync) -- discarding hold"
    rm -rf /var/tmp/Pv4test_hold
  else
    mv /var/tmp/Pv4test_hold /media/anton/hd2/Pv4test
  fi
fi
mkdir -p /media/anton/hd2/galaxy_staging/{objects,tmp,jobs,cache} \
         /media/anton/hd2/nextflow_work \
         /media/anton/samsung/galaxy_bulk
chown -R "$USER_NAME:$GROUP_NAME" /media/anton/hd2 /media/anton/samsung/galaxy_bulk

# --- 6. restart docker; verify images survived ------------------------------
say "starting docker"
systemctl start docker
sleep 3
docker info 2>/dev/null | grep -i "docker root dir" || true
if docker images --format '{{.Repository}}:{{.Tag}}' | grep -qx 'toga2:local'; then
  echo "toga2:local PRESENT -- good"
else
  echo "WARNING: toga2:local NOT found -- rebuild before Phase C"
fi

# --- 7. report ---------------------------------------------------------------
say "final state"
df -h / /media/anton/hd2 /media/anton/samsung
echo
echo "DONE. Galaxy will be restarted by Claude (config now takes effect)."
