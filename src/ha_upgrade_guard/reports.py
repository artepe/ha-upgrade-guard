"""Portable, offline HTML and Markdown reports."""
from __future__ import annotations

import html
from typing import Any


def as_markdown(report: dict[str, Any]) -> str:
    old, new = report["before"], report["after"]
    counts = report["summary"]
    lines = [
        "# HA Upgrade Guard — Change Report", "",
        f"**Home Assistant:** `{old['home_assistant_version']}` → `{new['home_assistant_version']}`  ",
        f"**Snapshot dates:** {old['captured_at']} → {new['captured_at']}  ",
        f"**Entity count:** {old['entities']} → {new['entities']}", "",
        "| Finding | Count |", "|---|---:|",
        *[f"| {name.replace('_', ' ').title()} | {count} |" for name, count in counts.items()],
        "", "## Findings", "",
    ]
    if not report["changes"]:
        lines.append("No detected regressions or capability changes.")
    for change in report["changes"]:
        detail = change["detail"].replace("|", r"\|").replace("`", "'").replace("\n", " ")
        lines.append(f"- **{change['severity'].upper()}** `{change['entity_id']}` — {detail}")
    lines += ["", "> Read-only analysis. A reported change is not necessarily caused by the update.", ""]
    return "\n".join(lines)


def as_html(report: dict[str, Any]) -> str:
    esc = lambda x: html.escape(str(x), quote=True)
    before, after = report["before"], report["after"]
    severities = report["severity_counts"]
    rows = "\n".join(
        f'<tr data-severity="{esc(c["severity"])}"><td><span class="pill {esc(c["severity"])}">{esc(c["severity"])}</span></td>'
        f'<td><code>{esc(c["entity_id"])}</code></td><td>{esc(c["kind"].replace("_", " "))}</td><td>{esc(c["detail"])}</td></tr>'
        for c in report["changes"]
    ) or '<tr><td colspan="4" class="empty">No changes detected</td></tr>'
    cards = "\n".join(f'<div class="stat"><span>{esc(label)}</span><strong>{count}</strong></div>' for label, count in [
        ("Entities before", before["entities"]), ("Entities after", after["entities"]),
        ("Critical findings", severities["critical"]), ("Warnings", severities["warning"]),
    ])
    # Everything is escaped and embedded; no external JS, CSS, CDNs or network calls.
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>HA Upgrade Guard — Report</title>
<style>
:root {{ color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, sans-serif; background: #0a1221; color: #e9f1ff; }}
* {{ box-sizing: border-box }} body {{ max-width: 1220px; margin: auto; padding: clamp(18px, 5vw, 55px) }}
header {{ display:flex; flex-wrap:wrap; align-items:center; justify-content:space-between; gap:12px }}
.logo {{ font-weight:800; font-size:1.9rem; letter-spacing:-1px }} .logo b {{color:#4fe2b2}} .tag {{ padding:7px 12px; border:1px solid #344662; border-radius:99px; color:#a6bcde;font-size:.85rem }}
h1 {{ font-size:clamp(1.8rem,4vw,3rem);letter-spacing:-1.5px;margin:40px 0 8px }} .muted {{ color:#9aafcd }}
.grid {{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:14px;margin:28px 0 36px}}
.stat {{border:1px solid #253752;background:linear-gradient(135deg,#14223b,#101c31);padding:21px 24px;border-radius:15px;display:flex; flex-direction:column; gap:14px}}
.stat span {{color:#adbed8;font-size:.88rem}} .stat strong {{font-size:2rem}}
.panel {{border:1px solid #263954;border-radius:16px;overflow:hidden;background:#101b2f}}
.toolbar {{padding:20px 22px;display:flex; flex-wrap:wrap;justify-content:space-between;gap:14px;align-items:center}}
.toolbar h2 {{margin:0}} .toolbar select {{background:#192a44;color:#eff7ff;border:1px solid #4c637f;border-radius:10px;padding:9px 12px;font:inherit}}
.scroll {{overflow-x:auto}}table {{border-collapse:collapse; width:100%;font-size:.89rem}}th,td {{text-align:left;padding:15px 19px;border-top:1px solid #243752;vertical-align:top}}th {{color:#a4bad9;text-transform:uppercase;letter-spacing:.05em;font-size:.74rem}}
code {{white-space:nowrap;color:#dbe9ff}}td:last-child {{min-width:260px;color:#b9cbea}} .pill {{display:inline-block;padding:4px 9px;border-radius:7px;text-transform:uppercase;font-size:.69rem;font-weight:800}}
.pill.critical {{color:#ffb4bc;background:#5f2634}} .pill.warning {{color:#ffd39e;background:#63461e}} .pill.info {{color:#b0e9d3;background:#1a5347}}
footer {{color:#8da3c4;margin:26px 0;line-height:1.6;font-size:.85rem}}.empty {{padding:35px;text-align:center}}
</style></head><body>
<header><div class="logo">HA <b>UPGRADE</b> GUARD</div><div class="tag">LOCAL · READ-ONLY · NO CLOUD</div></header>
<h1>What changed after your update?</h1><p class="muted">Version {esc(before['home_assistant_version'])} → {esc(after['home_assistant_version'])} &nbsp;|&nbsp; {esc(before['captured_at'])} → {esc(after['captured_at'])}</p>
<div class="grid">{cards}</div>
<div class="panel"><div class="toolbar"><h2>Detected changes</h2><label>Severity &nbsp; <select id="filter" aria-label="Filter findings by severity"><option value="all">All</option><option value="critical">Critical</option><option value="warning">Warnings</option><option value="info">Informational</option></select></label></div>
<div class="scroll"><table><thead><tr><th>Severity</th><th>Entity</th><th>Change</th><th>Details</th></tr></thead><tbody>{rows}</tbody></table></div></div>
<footer>Snapshots store entity IDs, health classification and an allowlist of capabilities — not live states or credentials. Findings are comparisons, not proof of causation. Generated by HA Upgrade Guard. Open this report offline.</footer>
<script>document.getElementById('filter').addEventListener('change',function(){{for(const row of document.querySelectorAll('tr[data-severity]'))row.hidden=this.value!=='all'&&row.dataset.severity!==this.value;}});</script>
</body></html>'''
