"""Shared rendering utilities for the AVM Intelligence Portal."""

from __future__ import annotations

import json
import os
import tempfile
from html import escape
from pathlib import Path
from typing import Any

from .scoring import DIM_ABBREV


def safe(value: Any) -> str:
    """Escape a value before placing it in generated HTML."""
    return escape("" if value is None else str(value), quote=True)


def score_class(score: float, has_data: bool) -> str:
    """Return the CSS class for a quality score."""
    if not has_data:
        return "score-grey"
    if score >= 80:
        return "score-green"
    if score >= 60:
        return "score-orange"
    return "score-red"


def status_badge(status: str) -> str:
    """Render a compact analysis-status badge."""
    if status == "pass":
        return '<span class="badge pass" title="pass">PASS</span>'
    if status in ("partial", "unchecked", "skip"):
        return f'<span class="badge partial" title="{safe(status)}">PART</span>'
    if status in ("fail", "missing", "failed"):
        return f'<span class="badge fail" title="{safe(status)}">FAIL</span>'
    return '<span class="badge none" title="no data">--</span>'


def status_cell_class(status: str) -> str:
    """Return the heatmap CSS class for a status value."""
    if status == "pass":
        return "hm-green"
    if status in ("partial", "unchecked", "skip"):
        return "hm-orange"
    if status in ("fail", "missing", "failed"):
        return "hm-red"
    return "hm-grey"


def stale_badge(days: int | None) -> str:
    """Render an analysis staleness badge."""
    if days is None:
        return ""
    if days > 30:
        return f'<span class="stale-badge stale-crit">stale {days}d</span>'
    if days > 14:
        return f'<span class="stale-badge stale-warn">stale {days}d</span>'
    return ""


def type_badge(module_type: str) -> str:
    """Render a module type badge."""
    return f'<span class="type-badge">{safe(module_type)}</span>'


def severity_badge(severity: str) -> str:
    """Render a provider or issue severity badge."""
    norm = severity.lower() if severity else "unknown"
    cls = {
        "critical": "severity-critical",
        "high": "severity-high",
        "medium": "severity-medium",
        "low": "severity-low",
    }.get(norm, "severity-unknown")
    return f'<span class="severity-badge {cls}">{safe(norm)}</span>'


def short_module_name(name: str) -> str:
    """Return a shorter display name while preserving the AVM identity."""
    return (
        name.replace("avm-res-", "")
        .replace("avm-ptn-", "")
        .replace("avm-utl-", "")
    )


def json_script(element_id: str, data: Any) -> str:
    """Embed JSON safely for client-side progressive enhancement."""
    encoded = json.dumps(data, ensure_ascii=True).replace("</", "<\\/")
    return f'<script type="application/json" id="{safe(element_id)}">{encoded}</script>'


def atomic_write(path: str | Path, content: str) -> None:
    """Write content atomically to avoid partial generated files."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=str(target.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
        os.replace(tmp_path, target)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def dim_legend() -> str:
    """Render the dimension abbreviation legend."""
    return " &nbsp;·&nbsp; ".join(
        f"<b>{safe(abbrev)}</b> = {safe(dim)}" for dim, abbrev in DIM_ABBREV.items()
    )

