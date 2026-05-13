"""Scoring helpers for AVM module analysis data."""

from __future__ import annotations

from datetime import datetime, timezone

DIMENSION_SEVERITY: dict[str, dict[str, int | str]] = {
    "security-hardening": {"level": "critical", "weight": 4},
    "avm-interface-compliance": {"level": "high", "weight": 3},
    "dependency-health": {"level": "high", "weight": 3},
    "provider-currency": {"level": "high", "weight": 3},
    "test-coverage": {"level": "medium", "weight": 2},
    "doc-quality": {"level": "medium", "weight": 2},
    "terraform-metadata": {"level": "low", "weight": 1},
}

STATUS_VALUE: dict[str, float] = {
    "pass": 1.0,
    "partial": 0.5,
    "unchecked": 0.5,
    "fail": 0.0,
    "missing": 0.0,
    "failed": 0.0,
    "skip": 0.5,
}

KEY_TO_DIM: dict[str, str] = {
    "analysis_terraform_metadata": "terraform-metadata",
    "analysis_avm_interface_compliance": "avm-interface-compliance",
    "analysis_security_hardening": "security-hardening",
    "analysis_test_coverage": "test-coverage",
    "analysis_doc_quality": "doc-quality",
    "analysis_dependency_health": "dependency-health",
    "analysis_provider_currency": "provider-currency",
}

DIM_ABBREV: dict[str, str] = {
    "terraform-metadata": "TM",
    "avm-interface-compliance": "AI",
    "security-hardening": "SH",
    "test-coverage": "TC",
    "doc-quality": "DQ",
    "dependency-health": "DH",
    "provider-currency": "PC",
}

DIM_ORDER = [
    "security-hardening",
    "avm-interface-compliance",
    "dependency-health",
    "provider-currency",
    "test-coverage",
    "doc-quality",
    "terraform-metadata",
]


def compute_score(analysis: dict[str, dict]) -> tuple[float, dict[str, str]]:
    """Return the weighted quality score and per-dimension statuses."""
    total_weight = 0.0
    weighted_sum = 0.0
    dim_statuses: dict[str, str] = {}
    for dim, meta in DIMENSION_SEVERITY.items():
        data = analysis.get(dim)
        if data is None:
            dim_statuses[dim] = "--"
            continue
        status = data.get("status", "")
        value = STATUS_VALUE.get(status, 0.5)
        weight = float(meta["weight"])
        weighted_sum += weight * value
        total_weight += weight
        dim_statuses[dim] = status
    score = (weighted_sum / total_weight * 100.0) if total_weight > 0 else 0.0
    return round(score, 1), dim_statuses


def staleness_days(analysis: dict[str, dict]) -> int | None:
    """Return the oldest analysis age in days, or None if no timestamps exist."""
    now = datetime.now(timezone.utc)
    oldest: int | None = None
    for data in analysis.values():
        checked = data.get("checked_at")
        if not checked:
            continue
        try:
            ts = datetime.fromisoformat(checked.replace("Z", "+00:00"))
        except ValueError:
            continue
        age = (now - ts).days
        if oldest is None or age > oldest:
            oldest = age
    return oldest

