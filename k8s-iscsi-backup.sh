#!/bin/bash

REPOSITORY=/path/to/borg/repo
VOLUME_TYPE='kubernetes.io~iscsi'

export BORG_PASSPHRASE='passphrase-goes-here'

if [[ ! -d $REPOSITORY ]]; then
    # initialize the borg repo if it doesn't exist
    borg init --encryption=repokey-blake2 $REPOSITORY
fi

for VOLUME in /var/lib/kubelet/pods/*/volumes/$VOLUME_TYPE/*; do
    # the repository will have archives named backup_date-volume_name
    # the root of each archive should be a folder with the volume name
    VOLUME_NAME=$(basename $VOLUME)
    cd $VOLUME/..
    borg create -v --stats --compression auto,zstd $REPOSITORY::{now:%Y-%m-%d}-$VOLUME_NAME $VOLUME_NAME
done

borg prune -v --list $REPOSITORY --keep-daily=7 --keep-weekly=4 --keep-monthly=6
