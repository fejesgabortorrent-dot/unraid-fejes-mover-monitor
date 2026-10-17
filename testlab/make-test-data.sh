#!/bin/bash
set -euo pipefail
[[ -f /etc/unraid-version && "$(hostname -s)" == FejesMover-Test ]] || { echo 'Run only inside FejesMover-Test.' >&2; exit 1; }
share=/mnt/user/fejesmover-test
[[ -d "$share" && -d /mnt/cache/fejesmover-test ]] || { echo 'Create the test share with cache primary storage first.' >&2; exit 1; }
free_kib=$(df -Pk /mnt/cache | awk 'END {print $4}')
[[ "$free_kib" =~ ^[0-9]+$ && "$free_kib" -ge 1048576 ]] || { echo 'At least 1 GiB cache free required.' >&2; exit 1; }
run=$(mktemp -d "$share/run-XXXXXXXX")
head -c 268435456 /dev/urandom > "$run/test-256MiB.bin"
(cd "$run" && sha256sum test-256MiB.bin > SHA256SUMS && sha256sum -c SHA256SUMS)
printf 'Created test data. After Mover completes, verify:\n(cd %q && sha256sum -c SHA256SUMS)\n' "$run"
echo 'Also verify actual disk placement in Unraid; matching hashes do not prove movement.'
