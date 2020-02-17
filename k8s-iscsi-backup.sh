#!/bin/bash

# This script backs up all k8s iSCSI volumes mounted to the current machine using borg

REPOSITORY=/path/to/borg/repo
VOLUME_TYPE='kubernetes.io~iscsi'
K8S_NAMESPACE='default'

# exporting the passphrase means borg create/prune won't ask for it
export BORG_PASSPHRASE='passphrase-goes-here'

# first, build an associative array of volume name to PVC metadata name
# get volume name to PVC metadata name from kubectl using jq
JSON=$(kubectl --namespace=$K8S_NAMESPACE get pvc -o json | jq -r '{ (.items[].spec.volumeName): (.items[].metadata.name) }')
# turn JSON object into bash 4+ associative array
arrayAsString=$(echo $JSON | jq --raw-output '. | to_entries | map("[\(.key)]=\(.value)") | reduce .[] as $item ("associativeArray=("; . + $item + " ") + ")"')
declare -A "$arrayAsString"

if [[ ! -d $REPOSITORY ]]; then
    # initialize the borg repo if it doesn't exist
    borg init --encryption=repokey-blake2 $REPOSITORY
fi

for VOLUME in /var/lib/kubelet/pods/*/volumes/$VOLUME_TYPE/*; do
    # the repository will have archives named backup_date-pvc.metadata.name
    # the root of each archive should be a folder containing all the volume data
    VOLUME_NAME=$(basename $VOLUME)
    PVC_NAME=${associativeArray["$VOLUME_NAME"]}
    if [ ! -z "$PVC_NAME" ]; then
        # only try to create a backup if the volume appears to be an actual PVC we know about
        cd $VOLUME/..
        borg create -v --stats --compression auto,zstd $REPOSITORY::{now:%Y-%m-%d}-$PVC_NAME $VOLUME_NAME
    fi
done

borg prune -v --list $REPOSITORY --keep-daily=7 --keep-weekly=4 --keep-monthly=6
