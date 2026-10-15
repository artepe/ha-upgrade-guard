"""Read-only Home Assistant snapshotting and regression detection.

Snapshots deliberately avoid live state values, coordinates, attribute values other
than a small set of capability descriptors, and authentication credentials.
"""

from __future__ import annotations

import fnmatch
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
BAD_STATES = {"unavailable", "unknown"}
CAPABILITY_KEYS = (
    "device_class", "state_class", "unit_of_measurement", "supported_features",
    "supported_color_modes", "hvac_modes", "fan_modes", "preset_modes",
    "swing_modes", "options", "source_list", "effect_list", "min_temp",
    "max_temp", "target_temp_step", "min_mireds", "max_mireds",
    "min_color_temp_kelvin", "max_color_temp_kelvin",
)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def health(state: str) -> str:
    return state if state in BAD_STATES else "ok"


def sanitized_capabilities(attrs: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in CAPABILITY_KEYS:
        if key not in attrs:
            continue
        value = attrs[key]
        if value is None or isinstance(value, (str, int, float, bool)):
            # Reject unexpected long strings to avoid accidental disclosure.
            if not isinstance(value, str) or len(value) <= 100:
                result[key] = value
        elif isinstance(value, (tuple, list)) and len(value) <= 50:
            # Only known capability collections; never arbitrary attribute data.
            if all(isinstance(item, str) and len(item) <= 100 for item in value):
                result[key] = sorted(set(value))
    return result


def build_snapshot(states: list[dict[str, Any]], *, version: str = "unknown", at: str | None = None) -> dict[str, Any]:
    entities: dict[str, dict[str, Any]] = {}
    for item in states:
        entity_id = item.get("entity_id")
        if not isinstance(entity_id, str) or "." not in entity_id or not isinstance(item.get("state"), str):
            continue
        attrs = item.get("attributes")
        if not isinstance(attrs, dict):
            attrs = {}
        entities[entity_id] = {
            "health": health(item["state"]),
            "capabilities": sanitized_capabilities(attrs),
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at": at or now_iso(),
        "home_assistant_version": str(version),
        "entities": dict(sorted(entities.items())),
    }


def validate_snapshot(obj: Any) -> dict[str, Any]:
    if not isinstance(obj, dict) or obj.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"Unsupported snapshot format: expected schema_version={SCHEMA_VERSION}")
    if not isinstance(obj.get("entities"), dict):
        raise ValueError("Invalid snapshot: entities must be an object")
    for entity_id, entity in obj["entities"].items():
        if not isinstance(entity_id, str) or not isinstance(entity, dict):
            raise ValueError("Invalid entity in snapshot")
        if entity.get("health") not in {"ok", "unknown", "unavailable"}:
            raise ValueError(f"Invalid health in snapshot for {entity_id}")
        if not isinstance(entity.get("capabilities"), dict):
            raise ValueError(f"Invalid capabilities in snapshot for {entity_id}")
    return obj


def read_snapshot(path: str | Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        return validate_snapshot(json.load(file))


def write_json(path: str | Path, data: dict[str, Any]) -> None:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def diff_snapshots(before: dict[str, Any], after: dict[str, Any], *, ignore: list[str] | None = None) -> dict[str, Any]:
    validate_snapshot(before)
    validate_snapshot(after)
    masks = ignore or []
    keep = lambda entity_id: not any(fnmatch.fnmatchcase(entity_id, mask) for mask in masks)
    old = {k: v for k, v in before["entities"].items() if keep(k)}
    new = {k: v for k, v in after["entities"].items() if keep(k)}
    changes: list[dict[str, Any]] = []

    def add(kind: str, severity: str, entity_id: str, detail: str) -> None:
        changes.append({"kind": kind, "severity": severity, "entity_id": entity_id, "detail": detail})

    for entity_id in sorted(old.keys() - new.keys()):
        add("removed", "critical", entity_id, "Entity no longer exists in the state API")
    for entity_id in sorted(new.keys() - old.keys()):
        status = new[entity_id]["health"]
        add("added", "warning" if status != "ok" else "info", entity_id,
            "New entity starts as " + status if status != "ok" else "New entity")

    for entity_id in sorted(old.keys() & new.keys()):
        prev, curr = old[entity_id], new[entity_id]
        h0, h1 = prev["health"], curr["health"]
        if h0 == "ok" and h1 in BAD_STATES:
            add("degraded", "critical", entity_id, f"Healthy → {h1}")
        elif h0 in BAD_STATES and h1 == "ok":
            add("recovered", "info", entity_id, f"{h0} → healthy")
        elif h0 != h1:
            add("health_changed", "warning", entity_id, f"{h0} → {h1}")

        caps0, caps1 = prev["capabilities"], curr["capabilities"]
        for key in sorted(caps0.keys() | caps1.keys()):
            if caps0.get(key) != caps1.get(key):
                if key not in caps1:
                    msg = f"Capability removed: {key}"
                elif key not in caps0:
                    msg = f"Capability added: {key}"
                else:
                    msg = f"Capability changed: {key} ({_safe_value(caps0[key])} → {_safe_value(caps1[key])})"
                add("capability_changed", "warning", entity_id, msg)

    rank = {"critical": 0, "warning": 1, "info": 2}
    changes.sort(key=lambda item: (rank[item["severity"]], item["entity_id"], item["kind"], item["detail"]))
    categories = ["removed", "added", "degraded", "recovered", "health_changed", "capability_changed"]
    return {
        "report_schema_version": 1,
        "generated_at": now_iso(),
        "before": {"captured_at": before.get("captured_at", "unknown"),
                   "home_assistant_version": before.get("home_assistant_version", "unknown"),
                   "entities": len(old)},
        "after": {"captured_at": after.get("captured_at", "unknown"),
                  "home_assistant_version": after.get("home_assistant_version", "unknown"),
                  "entities": len(new)},
        "summary": {kind: sum(1 for c in changes if c["kind"] == kind) for kind in categories},
        "severity_counts": {level: sum(1 for c in changes if c["severity"] == level) for level in rank},
        "ignored_patterns": masks,
        "changes": changes,
    }


def _safe_value(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return raw[:110] + ("…" if len(raw) > 110 else "")


def exit_code(report: dict[str, Any], fail_on: str) -> int:
    if fail_on == "never":
        return 0
    counts = report["severity_counts"]
    if fail_on == "critical":
        return 2 if counts["critical"] else 0
    if fail_on == "warning":
        return 2 if counts["critical"] or counts["warning"] else 0
    if fail_on == "any":
        return 2 if report["changes"] else 0
    raise ValueError("Invalid fail_on")
