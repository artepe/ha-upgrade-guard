"""HA Upgrade Guard CLI."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .client import HAClient, HAError
from .core import build_snapshot, diff_snapshots, exit_code, read_snapshot, write_json
from .reports import as_html, as_markdown


def create_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ha-upgrade-guard", description="Spot entity regressions after Home Assistant updates (read-only).")
    cmds = p.add_subparsers(dest="command", required=True)
    snap = cmds.add_parser("snapshot", help="Save a privacy-conscious snapshot using HA_URL + HA_TOKEN")
    snap.add_argument("-o", "--out", required=True, help="Output JSON file, e.g. before.json")
    snap.add_argument("--timeout", type=int, default=15, help="Network timeout in seconds")

    compare = cmds.add_parser("compare", help="Compare two snapshots or before snapshot against live HA")
    compare.add_argument("before", help="Baseline snapshot file")
    group = compare.add_mutually_exclusive_group(required=True)
    group.add_argument("after", nargs="?", help="After snapshot file")
    group.add_argument("--live", action="store_true", help="Take fresh state from the API as the second snapshot")
    compare.add_argument("--html", help="Save offline HTML report")
    compare.add_argument("--markdown", help="Save Markdown report")
    compare.add_argument("--json-report", help="Save machine-readable JSON report")
    compare.add_argument("--ignore", action="append", default=[], metavar="GLOB", help="Ignore entities matching glob, repeatable")
    compare.add_argument("--fail-on", choices=["never", "critical", "warning", "any"], default="never",
                         help="Set exit code 2 for findings at this level (default: never)")
    compare.add_argument("--timeout", type=int, default=15)
    cmds.add_parser("version", help="Print application version")
    return p


def live_snapshot(timeout: int) -> dict:
    states, version = HAClient(timeout=timeout).snapshot_data()
    return build_snapshot(states, version=version)


def _write(path: str, content: str) -> None:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    args = create_parser().parse_args(argv)
    try:
        if args.command == "version":
            print("HA Upgrade Guard 0.1.0")
            return 0
        if args.command == "snapshot":
            snapshot = live_snapshot(args.timeout)
            write_json(args.out, snapshot)
            print(f"Saved {len(snapshot['entities'])} entities to {args.out} (HA {snapshot['home_assistant_version']}).")
            return 0
        if args.command == "compare":
            before = read_snapshot(args.before)
            after = live_snapshot(args.timeout) if args.live else read_snapshot(args.after)
            report = diff_snapshots(before, after, ignore=args.ignore)
            if args.html:
                _write(args.html, as_html(report))
            if args.markdown:
                _write(args.markdown, as_markdown(report))
            if args.json_report:
                write_json(args.json_report, report)
            print(as_markdown(report))
            for label, path in (("HTML", args.html), ("Markdown", args.markdown), ("JSON", args.json_report)):
                if path:
                    print(f"Saved {label}: {path}")
            return exit_code(report, args.fail_on)
    except (HAError, ValueError, OSError, json.JSONDecodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
