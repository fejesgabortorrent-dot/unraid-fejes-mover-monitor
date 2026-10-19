#!/bin/bash
set -Eeuo pipefail
umask 077

# Csak alacsony cache-szabadhely esetén indítjuk az Unraid beépített Moverét.

POOL="/mnt/cache"
FILMEK="/mnt/user/Filmek"
KUSZOB_GIB=300
UJRA_PROBALKOZAS_MP=360
ALLAPOT="/var/run/filmek_mover_last_attempt"

log() {
    echo "[Filmek Mover] $*"
}

hiba() {
    log "HIBA: $*" >&2
    exit 1
}

[[ -d "$POOL" ]] || hiba "A cache pool nem érhető el: $POOL"
[[ -d "$FILMEK" ]] || hiba "A Filmek megosztás nem érhető el: $FILMEK"

FREE_KIB=$(df -Pk "$POOL" | awk 'NR == 2 {print $4}')
[[ "$FREE_KIB" =~ ^[0-9]+$ ]] || hiba "Nem sikerült a cache szabad helyét kiolvasni."

KUSZOB_KIB=$((KUSZOB_GIB * 1024 * 1024))
FREE_GIB=$(awk -v kb="$FREE_KIB" 'BEGIN {printf "%.1f", kb/1048576}')
MOST=$(date +%s)

if (( FREE_KIB >= KUSZOB_KIB )); then
    rm -f "$ALLAPOT"
    log "Cache: ${FREE_GIB} GiB szabad | küszöb: ${KUSZOB_GIB} GiB | OK"
    exit 0
fi


# Do not start Mover while Appdata Backup is active.
if [[ -f /tmp/appdata.backup/running ]]; then
  BACKUP_PID="$(cat /tmp/appdata.backup/running 2>/dev/null || true)"
  if [[ "${BACKUP_PID:-}" =~ ^[0-9]+$ ]] && kill -0 "$BACKUP_PID" 2>/dev/null; then
    log "Cache: ${FREE_GIB} GiB szabad | Appdata mentes fut | Mover halasztva"
    exit 0
  fi
fi

# Do not start Mover during parity check, sync or rebuild.
MD_RESYNC="$(grep -Po '^mdResync=\K\S+' /proc/mdstat 2>/dev/null || true)"
if [[ "${MD_RESYNC:-0}" =~ ^[0-9]+$ ]] && (( MD_RESYNC > 0 )); then
  log "Cache: ${FREE_GIB} GiB szabad | Paritasmuvelet fut | Mover halasztva"
  exit 0
fi
if [[ -f /var/run/mover.pid ]]; then
    log "Cache: ${FREE_GIB} GiB szabad | küszöb: ${KUSZOB_GIB} GiB | Mover már fut"
    exit 0
fi

if [[ -r "$ALLAPOT" ]]; then
    read -r UTOLSO < "$ALLAPOT" || true

    if [[ "${UTOLSO:-}" =~ ^[0-9]+$ ]] &&
       (( MOST - UTOLSO < UJRA_PROBALKOZAS_MP * 60 )); then

        HATRA=$((UJRA_PROBALKOZAS_MP - (MOST - UTOLSO) / 60))
        log "Cache: ${FREE_GIB} GiB szabad | küszöb: ${KUSZOB_GIB} GiB | várakozás aktív, még kb. ${HATRA} perc"
        exit 0
    fi
fi

printf '%s\n' "$MOST" > "$ALLAPOT"

log "Cache: ${FREE_GIB} GiB szabad | küszöb: ${KUSZOB_GIB} GiB | MOVER INDÍTÁS"

/usr/local/sbin/mover start
