#!/usr/bin/env python3
"""generate_site.py - Generate the AVM Intelligence Portal.

Usage:
    python3 scripts/generate_site.py [options]
    ./avm.sh site [options]

Options:
    --output-dir DIR   Multi-page output directory (default: docs/site).
    --output FILE      Legacy single-file output path.
    --domains LIST     Comma-separated domain slugs (or 'all').
    --types LIST       Comma-separated module types: res, ptn, utl (or 'all').
    --pages LIST       Comma-separated pages to generate (default: all).
    --pagefind         Include Pagefind UI asset tags after building the index.
    --validate         Validate generated HTML and internal links.
    --open             Open the generated index/file in the default browser.
"""

from __future__ import annotations

import json
import os
import sys
import webbrowser
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

from sitegen.css import write_css
from sitegen.data import (
    load_activity,
    load_module_issues,
    load_modules,
    load_resources,
    module_resource_symbols,
)
from sitegen.layout import generated_timestamp, shell
from sitegen.legacy import render_legacy
from sitegen.pages import PAGES
from sitegen.scoring import DIM_ORDER, compute_score
from sitegen.util import atomic_write

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_OUT_DIR = REPO_ROOT / "docs" / "site"
DEFAULT_LEGACY_OUT = DEFAULT_OUT_DIR / "index.html"


class _HTMLValidator(HTMLParser):
    """Minimal stdlib HTML parser used to catch malformed generated pages."""


def _split_list(value: str) -> list[str]:
    """Split a comma-separated CLI list, treating 'all' as no filter."""
    return [item.strip() for item in value.split(",") if item.strip() and item.strip() != "all"]


def _parse_args(argv: list[str]) -> dict[str, Any]:
    """Parse CLI arguments without adding external dependencies."""
    args: dict[str, Any] = {
        "domains": None,
        "types": None,
        "output": None,
        "output_dir": str(DEFAULT_OUT_DIR),
        "pages": None,
        "include_pagefind": False,
        "validate": False,
        "open_browser": False,
    }
    i = 0
    while i < len(argv):
        token = argv[i]
        if token in ("--help", "-h"):
            print(__doc__)
            sys.exit(0)
        if token in ("--domains", "--domain") and i + 1 < len(argv):
            i += 1
            args["domains"] = _split_list(argv[i])
        elif token in ("--types", "--type") and i + 1 < len(argv):
            i += 1
            args["types"] = _split_list(argv[i])
        elif token in ("--output", "-o") and i + 1 < len(argv):
            i += 1
            args["output"] = argv[i]
        elif token == "--output-dir" and i + 1 < len(argv):
            i += 1
            args["output_dir"] = argv[i]
        elif token == "--pages" and i + 1 < len(argv):
            i += 1
            args["pages"] = _split_list(argv[i])
        elif token == "--pagefind":
            args["include_pagefind"] = True
        elif token == "--no-pagefind":
            args["include_pagefind"] = False
        elif token == "--validate":
            args["validate"] = True
        elif token == "--open":
            args["open_browser"] = True
        else:
            print(f"Unknown or incomplete option: {token}", file=sys.stderr)
            sys.exit(2)
        i += 1

    if args["output"] and "--output-dir" in argv:
        print("--output and --output-dir are mutually exclusive.", file=sys.stderr)
        sys.exit(2)
    return args


def _module_json(modules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return compact module data for client-side use."""
    rows: list[dict[str, Any]] = []
    for module in modules:
        score, statuses = compute_score(module["analysis"])
        rows.append(
            {
                "name": module["name"],
                "domain": module.get("domain", ""),
                "type": module.get("type", ""),
                "status": module.get("status", ""),
                "display_name": module.get("display_name", ""),
                "score": score,
                "dimensions": {dim: statuses.get(dim, "--") for dim in DIM_ORDER},
                "resources": sorted(module_resource_symbols(module)),
            }
        )
    return rows


def _write_json(path: Path, data: Any) -> None:
    """Write deterministic JSON for generated site data."""
    atomic_write(path, json.dumps(data, indent=2, sort_keys=True) + "\n")


def _validate_html(path: Path) -> None:
    """Parse HTML to catch gross syntax errors."""
    parser = _HTMLValidator()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()


def _validate_links(output_dir: Path) -> None:
    """Check simple internal hrefs point at generated files."""
    href_re = __import__("re").compile(r'href="([^"#:]+\.html)"')
    for page in output_dir.glob("*.html"):
        for href in href_re.findall(page.read_text(encoding="utf-8")):
            target = (page.parent / href).resolve()
            if not target.is_file():
                raise FileNotFoundError(f"{page.name} links to missing {href}")


def generate_legacy_site(
    *,
    filter_domains: list[str] | None = None,
    filter_types: list[str] | None = None,
    output: str = str(DEFAULT_LEGACY_OUT),
    open_browser: bool = False,
) -> None:
    """Generate the legacy single-file dashboard used by --output."""
    modules = load_modules(filter_domains, filter_types)
    if not modules:
        print("No modules found.", file=sys.stderr)
        sys.exit(1)
    html = render_legacy(modules)
    atomic_write(output, html)
    print(f"  Generated legacy dashboard: {output}")
    if open_browser:
        webbrowser.open(f"file://{Path(output).resolve()}")


def generate_site(
    *,
    filter_domains: list[str] | None = None,
    filter_types: list[str] | None = None,
    output_dir: str = str(DEFAULT_OUT_DIR),
    page_filter: list[str] | None = None,
    include_pagefind: bool = True,
    validate: bool = False,
    open_browser: bool = False,
) -> None:
    """Generate the multi-page static portal."""
    modules = load_modules(filter_domains, filter_types)
    if not modules:
        print("No modules found.", file=sys.stderr)
        sys.exit(1)

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    write_css(output_path)

    resources = load_resources()
    module_issues = load_module_issues(modules)
    activity = load_activity()
    generated_at = generated_timestamp()
    selected_pages = page_filter or list(PAGES.keys())

    unknown_pages = sorted(set(selected_pages) - set(PAGES.keys()))
    if unknown_pages:
        print(f"Unknown page(s): {', '.join(unknown_pages)}", file=sys.stderr)
        sys.exit(2)

    _write_json(output_path / "data" / "modules.json", _module_json(modules))
    _write_json(output_path / "data" / "resources.json", resources)
    _write_json(output_path / "data" / "issues.json", module_issues)
    if activity:
        _write_json(output_path / "data" / "activity.json", activity)

    for slug, page_module in PAGES.items():
        if slug not in selected_pages:
            continue
        body, extra_head, extra_body = page_module.render(
            modules,
            resources=resources,
            module_issues=module_issues,
            activity=activity,
        )
        html = shell(
            page_module.TITLE,
            body,
            active_page=slug,
            extra_head=extra_head,
            extra_body_end=extra_body,
            generated_at=generated_at,
            include_pagefind=include_pagefind,
        )
        filename = "index.html" if slug == "index" else f"{slug}.html"
        atomic_write(output_path / filename, html)

    atomic_write(
        output_path / "404.html",
        shell(
            "Not Found - AVM Intelligence Portal",
            '<h1>Page not found</h1><p class="subtitle">Return to <a href="index.html">AVM Intelligence Portal</a>.</p>',
            active_page="",
            generated_at=generated_at,
            include_pagefind=False,
        ),
    )

    if validate:
        for page in output_path.glob("*.html"):
            _validate_html(page)
        _validate_links(output_path)

    print(f"  Generated portal: {output_path}")
    print(f"     {len(modules)} modules | {len(resources)} provider symbols | {len(selected_pages)} pages")
    if open_browser:
        webbrowser.open(f"file://{(output_path / 'index.html').resolve()}")


def main(argv: list[str] | None = None) -> None:
    """CLI entry point."""
    parsed = _parse_args(sys.argv[1:] if argv is None else argv)
    if parsed["output"]:
        generate_legacy_site(
            filter_domains=parsed["domains"] or None,
            filter_types=parsed["types"] or None,
            output=parsed["output"],
            open_browser=parsed["open_browser"],
        )
        return
    generate_site(
        filter_domains=parsed["domains"] or None,
        filter_types=parsed["types"] or None,
        output_dir=parsed["output_dir"],
        page_filter=parsed["pages"] or None,
        include_pagefind=parsed["include_pagefind"],
        validate=parsed["validate"],
        open_browser=parsed["open_browser"],
    )


if __name__ == "__main__":
    main()
