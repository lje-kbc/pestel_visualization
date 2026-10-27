# pestel-map

Builds one self-contained, interactive HTML world map from country scores (1 = poor … 5 = good).
The file works offline. Send it by mail, Teams or SharePoint; recipients open it in any browser.

## Usage

```
uv run pestel-map --data data/sample_scores.csv --countries config/countries.json --out output/pestel_map.html
```

Options: `--title`, `--subtitle`.

## Input

**Focus countries** (`config/countries.json`): the countries that are coloured. All other countries are grey ("not assessed").
Use ISO3 codes or English/German names. Kosovo is `XKX`.

**Scores** (`.csv`, `;` or `,`, UTF-8): one row per country and question.

| column | required | |
|---|---|---|
| `country` | yes | ISO3 code or English/German name |
| `dimension` | yes | e.g. `Economic` (PESTEL dimensions are sorted in PESTEL order) |
| `question_id` | yes | |
| `score` | yes | whole number 1–5; empty = not scored yet |
| `question_label` | no | short tab title (defaults to `question_id`), on any one row |
| `question_text` | no | long question, shown above the map |

Other formats (e.g. JSON) go into `src/pestel_visualization/loaders.py` as another loader that returns a `Dataset`.

## Views and calculation

Top-level tabs: `Overall` (only with two or more dimensions) and one tab per dimension.
Inside a dimension with several questions, a second row switches between `Average` and the individual questions.

- `Overall`: mean of the dimension means, so every dimension weighs the same.
- `Average` of a dimension: mean of the available question scores.
- Means are never rounded in between. Only the final value is rounded half up (2.5 → 3) to pick the colour.
- If a country is missing some questions, the mean uses the available ones. The map shows a dashed border and the tooltip shows `1/2`.

## Development

```
uv run pytest
uv run python scripts/build_geodata.py   # re-download Natural Earth 1:50m borders (only when upgrading)
```

Bundled third-party assets: [d3](https://d3js.org) 7.9.0 (ISC) and [Natural Earth](https://www.naturalearthdata.com) admin-0 countries 1:50m v5.1.2 (public domain).
