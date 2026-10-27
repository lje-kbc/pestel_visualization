import argparse
import sys
from pathlib import Path

from .aggregate import build_views
from .countries import country_index
from .loaders import load_data, load_focus_countries
from .model import DataError
from .render import render_html


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pestel-map", description="Build an interactive, self-contained country score map.")
    parser.add_argument("--data", required=True, type=Path, help="scores file (.csv)")
    parser.add_argument("--countries", required=True, type=Path, help="focus countries (.json)")
    parser.add_argument("--out", type=Path, default=Path("pestel_map.html"), help="output HTML file")
    parser.add_argument("--title", default="Country Assessment")
    parser.add_argument("--subtitle", default="")
    args = parser.parse_args(argv)

    try:
        countries = country_index()
        focus = load_focus_countries(args.countries, countries)
        dataset = load_data(args.data, countries)
        outside = sorted({c for c, _ in dataset.scores} - set(focus))
        if outside:
            names = ", ".join(f"{countries.names[c]} ({c})" for c in outside)
            raise DataError(f"Scores given for countries not in {args.countries.name}: {names}")
        if not dataset.questions:
            raise DataError(f"{args.data.name} contains no questions")
        views = build_views(dataset, focus)
    except (DataError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_html(views, focus, countries, args.title, args.subtitle), encoding="utf-8")
    missing = [countries.names[c] for c in focus if not any((c, q.id) in dataset.scores for q in dataset.questions)]
    print(f"Wrote {args.out} ({len(views)} views, {len(focus)} countries)")
    if missing:
        print(f"Note: no scores at all for {', '.join(missing)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
