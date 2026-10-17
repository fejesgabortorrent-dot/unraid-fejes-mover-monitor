# Testing

Run `python3 tools/check.py` from the repository with Python 3 and PHP CLI installed. This verifies packaging and exercises install/update/remove in a temporary directory. It does not run the Unraid plugin manager.

Real Unraid installation, reboot persistence, WebGUI integration, optional script editor and live Mover activity still need acceptance testing. See [the current release status](RELEASE-STATUS.md) for the complete checklist. Do not interpret the earlier prototype's Linux tests as evidence for this candidate.
