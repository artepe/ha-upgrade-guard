# HA Upgrade Guard — Change Report

**Home Assistant:** `2026.9.3` → `2026.10.1`  
**Snapshot dates:** 2026-10-14T07:00:00+00:00 → 2026-10-15T07:00:00+00:00  
**Entity count:** 5 → 5

| Finding | Count |
|---|---:|
| Removed | 1 |
| Added | 1 |
| Degraded | 1 |
| Recovered | 1 |
| Health Changed | 0 |
| Capability Changed | 1 |

## Findings

- **CRITICAL** `sensor.heat_pump_power` — Healthy → unavailable
- **CRITICAL** `sensor.old_energy_meter` — Entity no longer exists in the state API
- **WARNING** `climate.living_room` — Capability changed: hvac_modes (["heat", "off"] → ["heat"])
- **INFO** `sensor.new_device` — New entity
- **INFO** `sensor.recovered_later` — unavailable → healthy

> Read-only analysis. A reported change is not necessarily caused by the update.
