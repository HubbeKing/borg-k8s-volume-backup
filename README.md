# borg-k8s-volume-backup
Backing up kubernetes volumes on a node using borg backup

This repo will soon contain a docker image and kubernetes resource YAMLs for backing up kubernetes volumes in a cluster

The basic gist is as follows:
- Kubelet mounts pod volumes as `/var/lib/kubelet/pods/<pod_uuid>/volumes/<volume_type>/<volume_name>`
- By iterating over `/var/lib/kubelet/pods/*/volumes/*/*`, we can run operations on each mounted volume on a k8s node
  - For example, by iterating over `/var/lib/kubelet/pods/*/volumes/kubernetes.io~nfs/*`, we can back up each mounted NFS volume.
- This backup operation can be done in a pod, by running it as root and mounting `/var/lib/kubelet/pods/` using `hostPath`
- This pod can be operated as a `DaemonSet`, allowing for reasonably easy backup of all volumes in a k8s cluster to an NFS server
