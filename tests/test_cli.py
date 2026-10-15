import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ha_upgrade_guard.cli import create_parser, main
from ha_upgrade_guard.client import HAClient, HAError
from ha_upgrade_guard.core import build_snapshot, write_json


class CLITest(unittest.TestCase):
    def test_parser_live(self):
        args = create_parser().parse_args(["compare", "before.json", "--live", "--html", "report.html"])
        self.assertTrue(args.live)
        self.assertEqual(args.html, "report.html")

    def test_parser_offline(self):
        args = create_parser().parse_args(["compare", "before.json", "after.json"])
        self.assertEqual(args.after, "after.json")
        self.assertFalse(args.live)

    def test_offline_command_generates_reports_and_exit_code(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            write_json(root / "before.json", build_snapshot([{"entity_id": "sensor.x", "state": "3", "attributes": {}}]))
            write_json(root / "after.json", build_snapshot([{"entity_id": "sensor.x", "state": "unavailable", "attributes": {}}]))
            with contextlib.redirect_stdout(io.StringIO()) as output:
                code = main(["compare", str(root / "before.json"), str(root / "after.json"),
                             "--html", str(root / "report.html"),
                             "--markdown", str(root / "report.md"),
                             "--json-report", str(root / "report.json"),
                             "--fail-on", "critical"])
            self.assertEqual(code, 2)
            self.assertTrue((root / "report.html").is_file())
            self.assertTrue((root / "report.md").is_file())
            self.assertTrue((root / "report.json").is_file())
            self.assertIn("sensor.x", output.getvalue())

    def test_snapshot_mock_api(self):
        with tempfile.TemporaryDirectory() as td:
            with patch("ha_upgrade_guard.cli.HAClient") as client:
                client.return_value.snapshot_data.return_value = (
                    [{"entity_id": "sensor.x", "state": "on", "attributes": {}}], "2026.10.1")
                with contextlib.redirect_stdout(io.StringIO()):
                    code = main(["snapshot", "-o", str(Path(td) / "snap.json")])
                self.assertEqual(code, 0)
                self.assertTrue((Path(td) / "snap.json").exists())

    def test_error_does_not_echo_token(self):
        with self.assertRaises(HAError) as error:
            HAClient("https://example.org", "")
        self.assertNotIn("anything-secret", str(error.exception))

    def test_reject_credentials_in_url(self):
        with self.assertRaises(HAError):
            HAClient("https://admin:pass@example.org", "safe-token")

    def test_no_redirects(self):
        from ha_upgrade_guard.client import NoRedirects
        self.assertIsNone(NoRedirects().redirect_request(None, None, 302, "Redirect", {}, "https://bad.example"))


if __name__ == "__main__":
    unittest.main()
