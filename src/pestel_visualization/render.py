"""Bundle views, borders and d3 into one self-contained HTML file."""

import json
import re
from datetime import date
from importlib import resources

from .aggregate import View
from .countries import CountryIndex, load_world_geojson


def _asset(name: str) -> str:
    return resources.files(__package__).joinpath("assets", name).read_text(encoding="utf-8")


def _script_safe(text: str) -> str:
    # Inline <script> content must not contain a closing tag.
    return text.replace("</", "<\\/")


def build_payload(views: list[View], focus: list[str], countries: CountryIndex, title: str, subtitle: str) -> dict:
    return {
        "title": title,
        "subtitle": subtitle,
        "generated": date.today().isoformat(),
        "focus": focus,
        "names": {c: countries.names[c] for c in focus},
        "views": [
            {
                "id": v.id,
                "kind": v.kind,
                "label": v.label,
                "dimension": v.dimension,
                "description": v.description,
                "results": {
                    c: {
                        "value": None if r.value is None else round(float(r.value), 4),
                        "category": r.category,
                        "available": r.available,
                        "total": r.total,
                    }
                    for c, r in v.results.items()
                },
            }
            for v in views
        ],
    }


def render_html(views: list[View], focus: list[str], countries: CountryIndex, title: str, subtitle: str) -> str:
    payload = build_payload(views, focus, countries, title, subtitle)
    replacements = {
        "__TITLE__": title.replace("&", "&amp;").replace("<", "&lt;"),
        "__D3__": _script_safe(_asset("d3.min.js")),
        "__WORLD__": _script_safe(load_world_geojson()),
        "__DATA__": _script_safe(json.dumps(payload, ensure_ascii=False)),
    }
    # Single pass, so placeholder-like text inside the inserted data is left alone.
    return re.sub("|".join(replacements), lambda m: replacements[m.group(0)], _asset("template.html"))
