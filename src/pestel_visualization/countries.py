"""Country lookup backed by the bundled Natural Earth borders.

Countries can be referred to by ISO 3166 alpha-3 code or by English or German name.
"""

import json
import re
from dataclasses import dataclass
from functools import cache
from importlib import resources

from .model import DataError

# Common short forms that differ from Natural Earth's names.
ALIASES = {
    "usa": "USA",
    "us": "USA",
    "united states": "USA",
    "moldau": "MDA",
    "moldawien": "MDA",
    "republic of moldova": "MDA",
    "tschechische republik": "CZE",
    "czech republic": "CZE",
    "turkiye": "TUR",
    "türkiye": "TUR",
    "mazedonien": "MKD",
    "macedonia": "MKD",
    "bosnia and herzegovina": "BIH",
    "bosnien-herzegowina": "BIH",
    "dominican republic": "DOM",
    "trinidad & tobago": "TTO",
    "kosovo": "XKX",
    "kos": "XKX",
}


def _normalize(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().casefold())


@dataclass(frozen=True)
class CountryIndex:
    names: dict[str, str]  # iso3 -> English display name
    lookup: dict[str, str]  # normalized name or code -> iso3

    def resolve(self, ref: str) -> str:
        iso3 = self.lookup.get(_normalize(ref))
        if iso3 is None:
            raise DataError(f"Unknown country '{ref}'. Use an ISO3 code (e.g. ESP) or an English/German name.")
        return iso3


def load_world_geojson() -> str:
    return resources.files(__package__).joinpath("assets", "world.geojson").read_text(encoding="utf-8")


@cache
def country_index() -> CountryIndex:
    names: dict[str, str] = {}
    lookup: dict[str, str] = {}
    for feature in json.loads(load_world_geojson())["features"]:
        p = feature["properties"]
        names[p["iso3"]] = p["name_long"] or p["name"]
        for ref in (p["iso3"], p["name"], p["name_long"], p["name_de"]):
            if ref:
                lookup.setdefault(_normalize(ref), p["iso3"])
    for alias, iso3 in ALIASES.items():
        lookup[_normalize(alias)] = iso3
    return CountryIndex(names=names, lookup=lookup)
