# Linux VM lifecycle acceptance

This is an **Alpine Linux VM with simulated Unraid paths**, not Unraid.
It proves guest reboot and the package/startup model, not genuine Unraid boot
integration or real Mover file transfer. No Unraid license is used.

The lab uses one vCPU, 768 MiB RAM, a private QCOW2 overlay, read-only cloud-init
seed and the existing private NAT network. No real NAS disk or share is attached.
The official Alpine 3.24.2 cloud image was checked against its published SHA512.

Validated on 2026-10-19:

- Missing PHP ctype fails the installer before runtime activation. Installing
  the module in the guest permits installation and application tests.
- Package reproduction/checksums, isolated install/remove/rejection, Python
  unit tests, PHP application fixtures, mode guards and JS refresh checks pass.
- Real guest reboot changes its kernel boot ID. An OpenRC lab hook reinstalls
  the package into a fresh tmpfs runtime; all 11 files match the manifest and
  the saved Demo settings remain identical. A Demo dry-run POST renders.

Removal followed by a second real guest reboot also passed: the package stayed absent, settings and helper hashes remained identical. A final reinstall passed before guest shutdown. The real NAS boot ID and protected files were unchanged during the VM tests. Disks and rollback material were retained.

[Machine-readable results](linux-vm-acceptance-20261019.json). The final tested build is 2026.10.19.92.

## Reproducing the guest-side probe

Use a disposable Alpine guest with bash, Python 3, PHP 8 with ctype/JSON,
Node.js, coreutils and util-linux. Copy the repository and generated package
under `/opt/fejeslab`; copy `tools/vm_package_probe.py` to
`/opt/fejeslab/vm_package_probe.py`.

Explicitly mark only that disposable guest:

```sh
printf '%s\n' FEJES_MOVER_DISPOSABLE_LAB > /etc/fejes-mover-disposable-lab
python3 /opt/fejeslab/vm_package_probe.py init
reboot  # guest only
python3 /opt/fejeslab/vm_package_probe.py verify
python3 /opt/fejeslab/vm_package_probe.py remove
reboot  # guest only
python3 /opt/fejeslab/vm_package_probe.py verify-removed
```

The probe refuses non-Alpine systems and requires the explicit marker. It creates
simulated host markers/directories and a guest-only boot hook, mounts tmpfs,
installs/removes package runtime files and retains settings/helpers. Never run
it on a production machine. The source package remains under `/opt/fejeslab`.

Live NAS controls, guest credentials, host IPs and private filenames are not part
of this public probe. Real Unraid reboot and real guarded movement remain
separate acceptance tests.
