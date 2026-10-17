#!/bin/bash
# Host-side preflight and creation of NEW virtual disk files only.
set -euo pipefail
mode=${1:---check}
[[ $# -le 1 && ( "$mode" == --check || "$mode" == --prepare ) ]] || { echo 'Usage: bash prepare-host.sh [--check|--prepare]' >&2; exit 2; }
[[ -f /etc/unraid-version && -f /var/local/emhttp/var.ini ]] || { echo 'Unraid host required.' >&2; exit 1; }
[[ -c /dev/kvm && -r /dev/kvm && -w /dev/kvm ]] || { echo 'KVM is unavailable.' >&2; exit 1; }
for cmd in qemu-img virsh findmnt df awk; do command -v "$cmd" >/dev/null || { echo "Missing command: $cmd" >&2; exit 1; }; done
parent=/mnt/user/domains
target=$parent/FejesMover-Test
[[ -d "$parent" ]] || { echo 'Existing /mnt/user/domains share required.' >&2; exit 1; }
fs=$(findmnt -n -o FSTYPE -T "$parent")
[[ -n "$fs" && "$fs" != tmpfs && "$fs" != rootfs && "$fs" != overlay ]] || { echo 'domains is not on persistent storage.' >&2; exit 1; }
[[ ! -e "$target" && ! -L "$target" ]] || { echo "Target already exists; inspect manually: $target" >&2; exit 1; }
free_kib=$(df -Pk "$parent" | awk 'END {print $4}')
[[ "$free_kib" =~ ^[0-9]+$ && "$free_kib" -ge 52428800 ]] || { echo 'At least 50 GiB free required.' >&2; exit 1; }
mem_kib=$(awk '/^MemAvailable:/ {print $2}' /proc/meminfo)
[[ "$mem_kib" =~ ^[0-9]+$ && "$mem_kib" -ge 5242880 ]] || { echo 'At least 5 GiB MemAvailable required for this plan.' >&2; exit 1; }
virsh -c qemu:///system list --all >/dev/null || { echo 'VM Manager/libvirt unavailable.' >&2; exit 1; }
if virsh -c qemu:///system dominfo FejesMover-Test >/dev/null 2>&1; then echo 'VM name already exists; inspect it manually.' >&2; exit 1; fi
printf 'Preflight PASS: free=%s KiB, available RAM=%s KiB, storage=%s\n' "$free_kib" "$mem_kib" "$fs"
echo 'USB identity, licensing, network and per-device free space still need manual verification.'
[[ "$mode" == --prepare ]] || exit 0
umask 077
mkdir -- "$target"
qemu-img create -f raw "$target/parity-24GiB.img" 24G
qemu-img create -f raw "$target/data-16GiB.img" 16G
qemu-img create -f raw "$target/cache-8GiB.img" 8G
for image in "$target"/*.img; do qemu-img info "$image"; done
echo 'Three new RAW virtual disks prepared. VM has NOT been defined or started.'
