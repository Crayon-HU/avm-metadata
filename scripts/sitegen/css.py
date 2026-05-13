"""Shared stylesheet for the AVM Intelligence Portal."""

from __future__ import annotations

from pathlib import Path

from .util import atomic_write

SITE_CSS = """
:root {
  --bg: #0d1117;
  --bg2: #161b22;
  --bg3: #21262d;
  --border: #30363d;
  --text: #e6edf3;
  --muted: #8b949e;
  --green: #3fb950;
  --orange: #d29922;
  --red: #f85149;
  --blue: #58a6ff;
  --purple: #bc8cff;
  color-scheme: dark;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 14px;
  background: var(--bg);
  color: var(--text);
}
a { color: var(--blue); text-decoration: none; }
a:hover { text-decoration: underline; }
code { font-family: ui-monospace, SFMono-Regular, SFMono, Consolas, monospace; }
.site-nav {
  position: sticky; top: 0; z-index: 100;
  min-height: 52px; padding: 0 24px;
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
  background: rgba(22,27,34,.96); border-bottom: 1px solid var(--border);
  backdrop-filter: blur(8px);
}
.nav-logo {
  color: var(--text); font-weight: 700; white-space: nowrap;
  margin-right: 4px;
}
.nav-links { display: flex; align-items: center; gap: 4px; flex-wrap: wrap; }
.nav-link {
  color: var(--muted); font-size: 13px; text-decoration: none;
  padding: 16px 8px 13px; border-bottom: 2px solid transparent;
}
.nav-link:hover { color: var(--text); text-decoration: none; }
.nav-link.active { color: var(--text); border-bottom-color: var(--blue); }
.nav-search {
  margin-left: auto; color: var(--muted); font-size: 12px; min-width: 180px;
  text-align: right;
}
.mobile-menu { display: none; margin-left: auto; }
.page {
  width: min(1480px, 100%); margin: 0 auto; padding: 24px;
}
h1 { font-size: 24px; font-weight: 650; margin-bottom: 4px; }
h2 { font-size: 16px; font-weight: 650; margin-bottom: 12px; }
h3 { font-size: 14px; font-weight: 650; margin-bottom: 8px; }
.subtitle { color: var(--muted); font-size: 13px; margin-bottom: 24px; }
.stats { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 24px; }
.stat-card {
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: 8px; padding: 12px 18px; min-width: 128px;
}
.stat-card .val { font-size: 22px; font-weight: 700; line-height: 1.2; }
.stat-card .lbl { color: var(--muted); font-size: 12px; margin-top: 2px; }
.panel, .chart-card, .empty-state {
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: 8px; padding: 16px; margin-bottom: 16px;
}
.chart-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 16px; margin-bottom: 16px;
}
.quick-grid, .tile-grid {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px; margin-bottom: 16px;
}
.quick-card, .resource-tile {
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: 8px; padding: 14px; color: var(--text);
}
.quick-card:hover, .resource-tile:hover {
  border-color: var(--blue); text-decoration: none;
}
.quick-card .label, .resource-tile .label {
  color: var(--muted); font-size: 12px; margin-top: 4px;
}
details { margin-bottom: 16px; }
summary {
  list-style: none; cursor: pointer;
  display: flex; align-items: center; gap: 8px;
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: 8px; padding: 10px 16px;
  font-weight: 600; font-size: 15px; user-select: none;
}
details[open] > summary { border-radius: 8px 8px 0 0; border-bottom-color: transparent; }
summary::before {
  content: ">"; font-size: 11px; color: var(--muted); transition: transform .15s;
}
details[open] summary::before { transform: rotate(90deg); }
.domain-stats {
  margin-left: auto; font-size: 12px; color: var(--muted);
  font-weight: 400; display: flex; gap: 10px; flex-wrap: wrap;
}
.table-wrap { overflow-x: auto; margin-bottom: 16px; }
table {
  width: 100%; border-collapse: collapse;
  background: var(--bg2); border: 1px solid var(--border);
}
th, td {
  padding: 7px 12px; text-align: left; border-bottom: 1px solid var(--border);
  white-space: nowrap; vertical-align: top;
}
tr:last-child td { border-bottom: none; }
th {
  background: var(--bg3); color: var(--muted); font-size: 12px; font-weight: 600;
  letter-spacing: .04em; text-transform: uppercase;
}
th button {
  all: unset; cursor: pointer; color: inherit;
}
td.name { font-family: ui-monospace, SFMono-Regular, SFMono, Consolas, monospace; font-size: 12px; }
.score { font-weight: 700; font-size: 13px; }
.score-green { color: var(--green); }
.score-orange { color: var(--orange); }
.score-red { color: var(--red); }
.score-grey { color: var(--muted); }
.badge, .severity-badge, .type-badge {
  display: inline-block; padding: 1px 6px; border-radius: 4px;
  font-size: 11px; font-weight: 600; line-height: 1.5; margin-right: 3px;
}
.pass { background: rgba(63,185,80,.15); color: var(--green); }
.partial { background: rgba(210,153,34,.15); color: var(--orange); }
.fail { background: rgba(248,81,73,.15); color: var(--red); }
.none { background: rgba(139,148,158,.1); color: var(--muted); }
.type-badge { background: rgba(188,140,255,.15); color: var(--purple); }
.severity-critical { background: rgba(248,81,73,.24); color: var(--red); }
.severity-high { background: rgba(248,81,73,.15); color: #ff9b96; }
.severity-medium { background: rgba(210,153,34,.18); color: var(--orange); }
.severity-low { background: rgba(88,166,255,.14); color: var(--blue); }
.severity-unknown { background: rgba(139,148,158,.12); color: var(--muted); }
.stale-badge {
  font-size: 11px; padding: 1px 5px; border-radius: 4px; margin-left: 4px;
}
.stale-warn { background: rgba(210,153,34,.2); color: var(--orange); }
.stale-crit { background: rgba(248,81,73,.2); color: var(--red); }
.version { font-size: 12px; color: var(--muted); font-family: ui-monospace, SFMono-Regular, SFMono, Consolas, monospace; }
.heatmap { margin-bottom: 16px; }
.heatmap th, .heatmap td {
  padding: 6px 10px; text-align: center; border: 1px solid var(--border);
  font-size: 12px;
}
.heatmap td.dom-name, .heatmap td.module-name {
  text-align: left; font-weight: 500; min-width: 160px;
}
.hm-green { background: rgba(63,185,80,.18); color: var(--green); font-weight: 600; }
.hm-orange { background: rgba(210,153,34,.18); color: var(--orange); font-weight: 600; }
.hm-red { background: rgba(248,81,73,.18); color: var(--red); font-weight: 600; }
.hm-grey { background: transparent; color: var(--muted); }
.owner-handle { font-family: ui-monospace, SFMono-Regular, SFMono, Consolas, monospace; font-size: 12px; color: var(--blue); }
.owner-name, .muted { color: var(--muted); }
.no-secondary { color: var(--red); font-size: 11px; }
.mod-chip {
  display: inline-block; font-family: ui-monospace, SFMono-Regular, SFMono, Consolas, monospace;
  font-size: 11px; background: var(--bg3); border: 1px solid var(--border);
  border-radius: 4px; padding: 1px 5px; margin: 1px 2px;
  color: var(--text); white-space: nowrap;
}
.filter-bar {
  display: flex; flex-wrap: wrap; gap: 10px; align-items: end;
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: 8px; padding: 12px; margin-bottom: 16px;
}
.filter-bar label { color: var(--muted); font-size: 12px; display: grid; gap: 4px; }
.filter-bar input, .filter-bar select {
  background: var(--bg); color: var(--text); border: 1px solid var(--border);
  border-radius: 6px; padding: 7px 9px; min-width: 150px;
}
.kanban {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 16px; align-items: start;
}
.kanban-column {
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: 8px; padding: 12px;
}
.kanban-card {
  background: var(--bg3); border: 1px solid var(--border);
  border-radius: 6px; padding: 10px; margin-bottom: 8px;
}
.kanban-card summary {
  background: transparent; border: 0; padding: 0; display: block;
}
.detail-row {
  display: grid; grid-template-columns: 120px 1fr; gap: 10px;
  padding: 6px 0; border-top: 1px solid var(--border);
}
.detail-row:first-child { border-top: 0; }
.detail-key { color: var(--muted); font-size: 12px; }
.footer {
  margin-top: 32px; color: var(--muted); font-size: 12px; text-align: center;
}
@media (max-width: 768px) {
  .page { padding: 16px; }
  .site-nav { padding: 8px 16px; }
  .nav-links { display: none; width: 100%; }
  .mobile-menu { display: block; }
  .mobile-menu summary {
    background: transparent; border: 1px solid var(--border); padding: 6px 10px;
    border-radius: 6px;
  }
  .mobile-nav-links { display: grid; gap: 6px; padding: 8px 0; }
  .mobile-nav-links a { color: var(--text); padding: 6px 0; }
  .nav-search { flex-basis: 100%; margin-left: 0; text-align: left; }
  .chart-grid { grid-template-columns: 1fr; }
  th, td { padding: 6px 8px; }
}
"""


def write_css(output_dir: str | Path) -> None:
    """Write the shared stylesheet into the generated site."""
    atomic_write(Path(output_dir) / "assets" / "style.css", SITE_CSS.strip() + "\n")

