"""Portal page registry."""

from __future__ import annotations

from . import activity, catalog, home, issues, provider, resources, scoreboard

PAGES = {
    "index": home,
    "catalog": catalog,
    "scoreboard": scoreboard,
    "provider": provider,
    "resources": resources,
    "issues": issues,
    "activity": activity,
}

