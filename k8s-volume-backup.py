import glob
import json
import os
import subprocess
import sys

REPOSITORY = os.environ.get("REPOSITORY", None)
VOLUME_TYPE = os.environ.get("VOLUME_TYPE", None)
K8S_NAMESPACE = os.environ.get("K8S_NAMESPACE", "default")
BORG_PASSPHRASE = os.environ.get("BORG_PASSPHRASE", None)

if None in (REPOSITORY, VOLUME_TYPE, BORG_PASSPHRASE):
    print("Required ENV vars not set!")
    sys.exit(1)

# get PVC data for namespace as JSON
json_fetch = subprocess.run(["kubectl", "--namespace", K8S_NAMESPACE, "get", "pvc", "-o", "json"], stdout=subprocess.PIPE)

if json_fetch.returncode != 0:
    sys.exit(json_fetch.returncode)

# get items from output, this is the list/array of PVCs in the namespace
pvc_data = json.loads(json_fetch.stdout.decode("utf-8"))
pvc_data = dict(pvc_data).get("items", [])
if len(pvc_data) == 0:
    print("No PVCs defined in namespace!")
    sys.exit(1)

# turn PVC data list into a dict of volumeName to metadata name
pvc_data = { item["spec"]["volumeName"] : item["metadata"]["name"] for item in pvc_data }

# initialize borg repo if it doesn't already exist
if not os.path.exists(REPOSITORY):
    create = subprocess.run(["borg", "init", "--encryption=repokey-blake2", REPOSITORY], env={"BORG_PASSPHRASE": BORG_PASSPHRASE})
    if create.return_code != 0:
        sys.exit(create.return_code)

# iterate over mounted volume directories on this node
# note - glob.glob() simply returns empty list if it doesn't have read/listdir permissions
for volume in glob.glob(f"/var/lib/kubelet/pods/*/volumes/{VOLUME_TYPE}/*"):
    # get the volume's name
    volume_name = os.path.basename(volume)
    # get the pvc metadata name using the parsed get pvc output
    pvc_name = pvc_data.get(volume_name, "")
    if pvc_name:
        # create a borg archive named according to YYYY-MM-DD-pvc.metadata.name, containing a single folder with pvc.spec.volumeName as its name
        borg_create = subprocess.run(["borg", "create", "-v", "--stats", "--compression", "auto,zstd", f"{REPOSITORY}::\{now:%Y-%m-%d\}-{pvc_name}", volume_name], cwd=os.path.dirname(volume), stdout=subprocess.PIPE)
        # print the borg output so it can be captured and redirected for eventual log storage
        print(borg_create.stdout.decode("utf-8"))
