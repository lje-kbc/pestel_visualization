"""Download Natural Earth 1:50m country borders and trim them into the bundled asset.

Run once (or when upgrading Natural Earth):  uv run python scripts/build_geodata.py
The output is committed, so generating maps never needs network access.
"""

import json
import urllib.request
from pathlib import Path

SOURCE_URL = (
    "https://cdn.jsdelivr.net/gh/nvkelso/natural-earth-vector@v5.1.2/"
    "geojson/ne_50m_admin_0_countries.geojson"
)
OUT = Path(__file__).resolve().parents[1] / "src" / "pestel_visualization" / "assets" / "world.geojson"

# Natural Earth codes without an official ISO 3166 alpha-3 entry.
CODE_OVERRIDES = {"KOS": "XKX"}
DROP = {"ATA"}  # Antarctica only wastes map space
PRECISION = 3  # ~100 m, plenty for a 1:50m dataset


def valid(code) -> bool:
    return code not in ("-99", "", None)


def iso3(props: dict, official: set[str]) -> str:
    """ISO_A3 if set; else ISO_A3_EH (e.g. France, Norway) unless that code
    belongs to the parent state of a dependency; else Natural Earth's own code."""
    adm = props["ADM0_A3"]
    if adm in CODE_OVERRIDES:
        return CODE_OVERRIDES[adm]
    if valid(props["ISO_A3"]):
        return props["ISO_A3"]
    if valid(props["ISO_A3_EH"]) and props["ISO_A3_EH"] not in official:
        return props["ISO_A3_EH"]
    return adm


def round_coords(coords):
    if isinstance(coords[0], (int, float)):
        return [round(c, PRECISION) for c in coords]
    return [round_coords(c) for c in coords]


def main() -> None:
    with urllib.request.urlopen(SOURCE_URL) as resp:
        source = json.load(resp)

    official = {f["properties"]["ISO_A3"] for f in source["features"] if valid(f["properties"]["ISO_A3"])}
    features = []
    seen: set[str] = set()
    for f in source["features"]:
        p = f["properties"]
        if p["ADM0_A3"] in DROP:
            continue
        code = iso3(p, official)
        if code in seen:
            raise SystemExit(f"Duplicate country code {code} ({p['NAME']})")
        seen.add(code)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "iso3": code,
                    "name": p["NAME"],
                    "name_long": p["NAME_LONG"],
                    "name_de": p["NAME_DE"],
                },
                "geometry": {
                    "type": f["geometry"]["type"],
                    "coordinates": round_coords(f["geometry"]["coordinates"]),
                },
            }
        )

    OUT.write_text(
        json.dumps({"type": "FeatureCollection", "features": features}, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Wrote {len(features)} countries to {OUT}")


if __name__ == "__main__":
    main()
