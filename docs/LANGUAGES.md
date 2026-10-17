# Magyar · English (US) · Deutsch

The dashboard, monitor and optional settings page provide a 🌐 selector for
Hungarian, US English and German. Hungarian remains the default. A browser cookie
shares the choice across these pages for one year; invalid values fall back to
Hungarian. Changing language navigates to the current page with GET, discarding
unsaved edits without submitting settings. Existing Unraid menu metadata uses
static, neutral labels: Mover Monitor and Mover Settings.

Visible labels, tooltips, refresh states, empty states, validation errors and save
confirmations are translated. US English uses US number/time formatting. Filenames,
existing automation contents and log entries retain their original text.

`src/*.page` contains Hungarian source templates. `src/translations.json` maps
trusted source literals to English and German. `tools/localize.py` compiles all
three branches into each self-contained runtime page during the package build.
No runtime translation service, network request or additional runtime dependency
is required. Translation values are validated to prevent unsafe source literals.
Do not install the raw source templates as runtime pages; use the PLG.

Validation on 2026-10-17: 41 application fixture checks, including all three
languages, selectors, optional-script absence, full cache, validation messages,
successful settings saves, malformed-cookie fallback and unchanged runtime logs.
Rendered JavaScript syntax, refresh race tests, reproducible build/checksums,
isolated installer/update/rejection/uninstall and stale-artifact tests also pass.
The generated runtime PHP is linted by the isolated installer.

No live NAS deployment, Unraid WebGUI acceptance test or reboot test was performed.
