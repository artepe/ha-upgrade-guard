import json
import tempfile
import unittest
from pathlib import Path

from ha_upgrade_guard.core import (build_snapshot, diff_snapshots, exit_code,
                                    read_snapshot, sanitized_capabilities,
                                    validate_snapshot, write_json)
from ha_upgrade_guard.reports import as_html, as_markdown


def state(id, value="on", **attrs):
    return {"entity_id": id, "state": value, "attributes": attrs,
            "last_changed": "2026-10-15T00:00:00Z", "context": {"user_id": "private"}}


class SnapshotTest(unittest.TestCase):
    def test_snapshot_does_not_save_raw_states_or_sensitive_attributes(self):
        snap = build_snapshot([state("person.private", "home", latitude=12.5, longitude=20,
                                     access_token="secret", friendly_name="Alice")])
        encoded = json.dumps(snap)
        self.assertNotIn("secret", encoded)
        self.assertNotIn("Alice", encoded)
        self.assertNotIn("latitude", encoded)
        self.assertNotIn("home\"", encoded)
        self.assertEqual(snap["entities"]["person.private"]["health"], "ok")

    def test_unavailable_unknown(self):
        snap = build_snapshot([state("sensor.a", "unavailable"), state("sensor.b", "unknown")])
        self.assertEqual(snap["entities"]["sensor.a"]["health"], "unavailable")
        self.assertEqual(snap["entities"]["sensor.b"]["health"], "unknown")

    def test_invalid_entries_skipped(self):
        self.assertEqual(build_snapshot([{}, {"entity_id": "bad", "state": "on"},
                                         {"entity_id": "sensor.foo", "state": 42}])["entities"], {})

    def test_allowlisted_caps_only(self):
        caps = sanitized_capabilities({"supported_features": 11, "options": ["A", "B"],
                                       "private_address": "123", "unit_of_measurement": "°C"})
        self.assertEqual(caps, {"unit_of_measurement": "°C", "supported_features": 11,
                                "options": ["A", "B"]})

    def test_array_order_ignored(self):
        a = build_snapshot([state("climate.x", "heat", hvac_modes=["heat", "off"])])
        b = build_snapshot([state("climate.x", "off", hvac_modes=["off", "heat"])])
        self.assertFalse(diff_snapshots(a, b)["changes"])

    def test_invalid_snapshot_schema(self):
        with self.assertRaises(ValueError):
            validate_snapshot({"schema_version": 200, "entities": {}})
        with self.assertRaises(ValueError):
            validate_snapshot({"schema_version": 1, "entities": {"sensor.x": {"health": "oops", "capabilities": {}}}})

    def test_roundtrip(self):
        snap = build_snapshot([state("sensor.x", "12")])
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "sub" / "snapshot.json"
            write_json(path, snap)
            self.assertEqual(read_snapshot(path), snap)


class DiffTest(unittest.TestCase):
    def test_degraded_removed_added(self):
        a = build_snapshot([state("sensor.a"), state("sensor.b")], version="2026.9")
        b = build_snapshot([state("sensor.a", "unavailable"), state("sensor.c")], version="2026.10")
        changes = diff_snapshots(a, b)
        self.assertEqual(changes["summary"]["removed"], 1)
        self.assertEqual(changes["summary"]["degraded"], 1)
        self.assertEqual(changes["summary"]["added"], 1)
        self.assertEqual(changes["severity_counts"]["critical"], 2)
        self.assertEqual(changes["before"]["home_assistant_version"], "2026.9")

    def test_recovered_health(self):
        a = build_snapshot([state("sensor.x", "unknown")])
        b = build_snapshot([state("sensor.x", "21")])
        self.assertEqual(diff_snapshots(a, b)["summary"]["recovered"], 1)

    def test_persistently_unavailable_not_flagged(self):
        a = build_snapshot([state("sensor.x", "unavailable")])
        b = build_snapshot([state("sensor.x", "unavailable")])
        self.assertFalse(diff_snapshots(a, b)["changes"])

    def test_capability_added_removed_changed(self):
        a = build_snapshot([state("climate.x", "heat", hvac_modes=["heat", "off"],
                                  supported_features=2, min_temp=15)])
        b = build_snapshot([state("climate.x", "heat", hvac_modes=["heat"],
                                  supported_features=3, max_temp=25)])
        diff = diff_snapshots(a, b)
        self.assertEqual(diff["summary"]["capability_changed"], 4)

    def test_ignore_patterns(self):
        a = build_snapshot([state("sensor.a"), state("sensor.b")])
        b = build_snapshot([])
        self.assertEqual(diff_snapshots(a, b, ignore=["sensor.*"])["changes"], [])

    def test_new_unavailable_warning(self):
        diff = diff_snapshots(build_snapshot([]), build_snapshot([state("sensor.x", "unavailable")]))
        self.assertEqual(diff["severity_counts"]["warning"], 1)

    def test_health_swap_is_warning(self):
        a = build_snapshot([state("sensor.x", "unavailable")])
        b = build_snapshot([state("sensor.x", "unknown")])
        self.assertEqual(diff_snapshots(a, b)["summary"]["health_changed"], 1)

    def test_fail_modes(self):
        report = diff_snapshots(build_snapshot([state("sensor.a")]), build_snapshot([]))
        self.assertEqual(exit_code(report, "never"), 0)
        self.assertEqual(exit_code(report, "critical"), 2)
        self.assertEqual(exit_code(report, "warning"), 2)
        self.assertEqual(exit_code(report, "any"), 2)

    def test_html_is_escaped(self):
        a = build_snapshot([state("sensor.x<evil>")])
        html = as_html(diff_snapshots(a, build_snapshot([])))
        self.assertNotIn("<evil>", html)
        self.assertIn("&lt;evil&gt;", html)
        self.assertIn("LOCAL", html)

    def test_markdown_contains_finding(self):
        a = build_snapshot([state("sensor.a")])
        self.assertIn("`sensor.a`", as_markdown(diff_snapshots(a, build_snapshot([]))))


if __name__ == "__main__":
    unittest.main()
