#!/bin/bash
# Host-side preflight and creation of NEW virtual disk files only.
set -euo pipefail
export LC_ALL=C
mode=${1:---check}
[[ $# -le 1 && ( "$mode" == --check || "$mode" == --prepare || "$mode" == --create-vm ) ]] || { echo 'Usage: bash prepare-host.sh [--check|--prepare|--create-vm]' >&2; exit 2; }
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
if [[ "$mode" == --create-vm ]]; then
  for firmware in /usr/share/qemu/ovmf-x64/OVMF_CODE-pure-efi.fd /usr/share/qemu/ovmf-x64/OVMF_VARS-pure-efi.fd; do [[ -r "$firmware" ]] || { echo "Required Unraid OVMF file missing: $firmware" >&2; exit 1; }; done
  virsh -c qemu:///system net-list --name | awk '$0=="default" {found=1} END {exit !found}' || { echo 'An existing active libvirt default NAT network is required; no network will be changed.' >&2; exit 1; }
fi
printf 'Preflight PASS: free=%s KiB, available RAM=%s KiB, storage=%s\n' "$free_kib" "$mem_kib" "$fs"
echo 'USB identity, licensing, network and per-device free space still need manual verification.'
[[ "$mode" != --check ]] || exit 0
umask 077
mkdir -- "$target"
qemu-img create -f raw "$target/parity-24GiB.img" 24G
qemu-img create -f raw "$target/data-16GiB.img" 16G
qemu-img create -f raw "$target/cache-8GiB.img" 8G
for image in "$target"/*.img; do qemu-img info "$image"; done
echo 'Three new RAW virtual disks prepared. VM has NOT been defined or started.'

[[ "$mode" == --create-vm ]] || exit 0
cat > "$target/domain.xml" <<'XML'
<domain type='kvm'>
  <name>FejesMover-Test</name>
  <description>Disposable Unraid Mover plugin test VM; attach a separate licensed test USB before first boot.</description>
  <memory unit='MiB'>4096</memory>
  <currentMemory unit='MiB'>4096</currentMemory>
  <vcpu placement='static'>2</vcpu>
  <os>
    <type arch='x86_64' machine='q35'>hvm</type>
    <loader readonly='yes' type='pflash'>/usr/share/qemu/ovmf-x64/OVMF_CODE-pure-efi.fd</loader>
    <nvram template='/usr/share/qemu/ovmf-x64/OVMF_VARS-pure-efi.fd'>/mnt/user/domains/FejesMover-Test/nvram.fd</nvram>
    <boot dev='hd'/>
    <bootmenu enable='yes'/>
  </os>
  <features><acpi/><apic/></features>
  <cpu mode='host-passthrough' check='none'/>
  <clock offset='utc'/>
  <on_poweroff>destroy</on_poweroff>
  <on_reboot>restart</on_reboot>
  <on_crash>destroy</on_crash>
  <devices>
    <controller type='usb' model='qemu-xhci'/>
    <controller type='sata' index='0'/>
    <disk type='file' device='disk'>
      <driver name='qemu' type='raw'/>
      <source file='/mnt/user/domains/FejesMover-Test/parity-24GiB.img'/>
      <target dev='sda' bus='sata'/><serial>FMTESTPARITY24</serial>
    </disk>
    <disk type='file' device='disk'>
      <driver name='qemu' type='raw'/>
      <source file='/mnt/user/domains/FejesMover-Test/data-16GiB.img'/>
      <target dev='sdb' bus='sata'/><serial>FMTESTDATA16</serial>
    </disk>
    <disk type='file' device='disk'>
      <driver name='qemu' type='raw'/>
      <source file='/mnt/user/domains/FejesMover-Test/cache-8GiB.img'/>
      <target dev='sdc' bus='sata'/><serial>FMTESTCACHE08</serial>
    </disk>
    <interface type='network'><source network='default'/><model type='virtio'/></interface>
    <graphics type='vnc' port='-1' autoport='yes' websocket='-1'>
      <listen type='address' address='127.0.0.1'/>
    </graphics>
    <video><model type='vga' heads='1' primary='yes'/></video>
    <input type='tablet' bus='usb'/>
    <memballoon model='none'/>
  </devices>
</domain>
XML
virsh -c qemu:///system define "$target/domain.xml"
virsh -c qemu:///system autostart --disable FejesMover-Test
virsh -c qemu:///system dominfo FejesMover-Test
printf '\nVM DEFINED, STOPPED. No physical disks or USB devices attached.\n'
echo 'Next: select only the separate test USB in the Unraid VM editor; choose it as the boot device, then start with VNC.'
echo 'The default NAT network normally requires guest GUI mode/VNC for WebGUI access; direct LAN access is not configured.'
