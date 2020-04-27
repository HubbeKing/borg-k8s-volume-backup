import glob
import json
import os
import subprocess
import sys

REPOSITORY = os.environ.get("REPOSITORY", None)
# default to in-tree kubernetes.io iscsi volume type
VOLUME_TYPE = os.environ.get("VOLUME_TYPE", "kubernetes.io~iscsi")
K8S_NAMESPACE = os.environ.get("K8S_NAMESPACE", "default")
BORG_PASSPHRASE = os.environ.get("BORG_PASSPHRASE", None)

if None in (REPOSITORY, BORG_PASSPHRASE):
    print("Required ENV vars not set!")
    sys.exit(1)

# get PVC data for namespace as JSON
json_fetch = subprocess.check_output(["kubectl", "--namespace", K8S_NAMESPACE, "get", "pvc", "-o", "json"])

# get items from output, this is the list/array of PVCs in the namespace
pvc_data = json.loads(json_fetch.decode("utf-8"))
pvc_data = pvc_data.get("items", [])

# turn PVC data list into a dict of volumeName to metadata name
# 'get pvc' output has the volume name in .spec.volumeName and the metadata name in .metadata.name
pvc_data = { item["spec"]["volumeName"] : item["metadata"]["name"] for item in pvc_data }

# initialize borg repo if it doesn't already exist
if not os.path.exists(REPOSITORY):
    subprocess.check_call(["borg", "init", "--encryption=repokey-blake2", REPOSITORY], env={"BORG_PASSPHRASE": BORG_PASSPHRASE})

# iterate over mounted volume directories on this node
# note - glob.glob() simply returns empty list if it doesn't have read/listdir permissions
for volume in glob.glob(f"/var/lib/kubelet/pods/*/volumes/{VOLUME_TYPE}/*"):
    # get the volume's name
    volume_name = os.path.basename(volume)
    # get the pvc metadata name using the parsed get pvc output
    pvc_name = pvc_data.get(volume_name, "")
    if pvc_name:
        # create a borg archive named according to pvc.metadata.name-YYYY-MM-DD, cd-ing into the volume directory first
        # contents of archive will be identical to contents of the PVC at time of archive creation, to simplify backup restore
        # to restore a backup to the current folder: 'borg extract ${REPOSITORY}::pvc.metadata.name-YYYY-MM-DD'
        # example backup command : borg create /mnt/repo::sonarr-2020-02-01 .
        # example restory command: borg extract /mnt/repo::sonarr-2020-02-01
        subprocess.check_call(["borg", "create", "-v", "--stats", "--compression", "auto,zstd",
                              f"{REPOSITORY}::{pvc_name}-{{now:%Y-%m-%d}}", "."],
                              cwd=volume, env={"BORG_PASSPHRASE": BORG_PASSPHRASE})

        # prune borg repo, removing old backups for this pvc_name
        # note the --prefix, to limit pruning
        subprocess.check_call(["borg", "prune", "-v", "--list", REPOSITORY, "--prefix", pvc_name,
                              "--keep-daily=7", "--keep-weekly=4", "--keep-monthly=6", "--keep-yearly=1"],
                              env={"BORG_PASSPHRASE": BORG_PASSPHRASE})
