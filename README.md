# 🛡️ HA Upgrade Guard

Find out what changed after a Home Assistant update — before your automations break.

**Read-only • local-first • no telemetry • Python 3.10+**

HA Upgrade Guard compares two snapshots of your Home Assistant entities, reports removals, new unavailable or unknown states, feature/capability changes, added entities and recoveries. It produces offline HTML, Markdown and JSON reports.

Independent community project, not affiliated with Home Assistant or the Open Home Foundation.

## Demo (no Home Assistant required)

```bash
python3 guard.py compare examples/before.json examples/after.json --html demo.html
```

Open `demo.html` in your browser.

## Quick start

Download or clone this repository to a computer that can reach your Home Assistant installation. Generate a long-lived access token in Home Assistant under your profile security settings; do not share it or commit it to GitHub.

```bash
export HA_URL="http://homeassistant.local:8123"
read -rs HA_TOKEN; export HA_TOKEN

# Before updating Home Assistant
python3 guard.py snapshot --out before.json

# After updating and allowing integrations to initialize
python3 guard.py compare before.json --live --html report.html --markdown report.md --json-report report.json
open report.html
```

For Windows, set the equivalent PowerShell environment variables and run `py guard.py ...`. The script needs no runtime third-party packages or installation within Home Assistant OS.

## Additional commands

```bash
python3 guard.py snapshot --out after.json
python3 guard.py compare before.json after.json --html report.html
python3 guard.py compare before.json after.json --ignore 'sensor.test_*' --fail-on critical
python3 guard.py version
```

An optional installation with `python3 -m pip install .` adds the `ha-upgrade-guard` command.

## Security and privacy

Only read-only GET calls to the Home Assistant REST API are used. Snapshots contain IDs, coarse health (ok/unavailable/unknown) and an allowlist of capability metadata. The tool does **not** save access tokens, live temperatures, power readings, arbitrary attributes or geolocation. Entity IDs themselves may be sensitive; do not publish private snapshots.

Snapshots are point-in-time observations. An entity renamed during an update appears as one removed and one added entity. Not all breaking changes are detectable; intentional changes may be reported, too. The tool does not modify or repair Home Assistant.

## Testing

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

GitHub Actions runs the tests on Python 3.10, 3.12 and 3.13. Licensed under MIT. Contributions and issue reports are welcome; **never include credentials or unredacted private snapshots**.

For Finnish instructions see [README.fi.md](README.fi.md).
