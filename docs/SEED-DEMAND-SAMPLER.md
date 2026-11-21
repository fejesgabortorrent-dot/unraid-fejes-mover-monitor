# Read-only owner demand sampler

Development helper `tools/seed_demand.py` uses the existing local qBittorrent
read adapter. It never changes torrents, moves files or queries trackers/Emby.
It stores SHA256-derived torrent identifiers, upload counters, Docker start
identity, timestamps and non-overlapping 30-minute windows. Names, content
paths, tracker URLs and credentials are not retained. Output is aggregate only.

A recurring-demand signal requires two windows with at least 64 MiB uploaded
within the last day. Polling more often does not duplicate windows. A container
restart, counter decrease or observation gap over one hour discards that
item's baseline/history. Corrupt data or API failure prevents a new state write.
The counter is qBittorrent's cumulative uploaded total; a daemon restart that
preserves that total does not by itself invalidate the delta. Docker restart
identity and counter regression are the reset signals currently implemented.

This is torrent-level demand, not per-file popularity, placement eligibility,
peer performance after movement or tracker seed credit. Multi-file torrent
attribution remains unresolved. It is not a reverse executor and installation
of the public plugin does not enable it.

Owner operation: invoke every five minutes with `--state` pointing at a private
persistent file. First invocation establishes a baseline; at least an hour and
two qualifying windows are required for a recurring-demand signal. A longer
24–72 hour observation period is recommended before placement decisions.
