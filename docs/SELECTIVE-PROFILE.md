# Selective mover profile

The selective mover remains Observer by default. Advanced movement is opt-in and
still requires every existing preflight guard. A profile only describes the
reviewed environment; it does not grant permission to move files.

The optional file is:

`/boot/config/plugins/fejes.mover.monitor/selective-profile.json`

It must be a regular, non-symlink JSON file with this shape:

```json
{
  "version": 1,
  "pool": "cache",
  "share": "Filmek",
  "torrent_container": "binhex-qbittorrentvpn",
  "launcher_script": "Filmek_Mover_Threshold"
}
```

Pool, share, container, and script names are single Unraid names matching
`[A-Za-z0-9][A-Za-z0-9_-]{0,63}`. The mover derives the physical source,
`/mnt/user` canonical path, share configuration, and User Scripts launcher from
these names. Missing, malformed, unreadable, symlinked, or path-traversal
profiles fail closed. If the file is absent, the owner-tested compatibility
profile is used and the UI remains Observer by default.

Before publication, a profile must be reviewed on the target NAS in Observer
mode. The profile is not a replacement for the release gate, live read-back,
or an explicit Advanced-mode acknowledgement.
