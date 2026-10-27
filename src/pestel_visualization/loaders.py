"""Input loaders. Each one turns a file into a Dataset; add a JSON loader here once its format is fixed."""

import csv
import json
from pathlib import Path

from .countries import CountryIndex
from .model import MAX_SCORE, MIN_SCORE, Dataset, DataError, Question

REQUIRED_COLUMNS = ("country", "dimension", "question_id", "score")


def parse_score(raw: str, where: str) -> int | None:
    """Empty means 'not scored yet'; anything else must be an integer 1..5."""
    raw = raw.strip()
    if not raw:
        return None
    if not raw.isdigit() or not MIN_SCORE <= int(raw) <= MAX_SCORE:
        raise DataError(f"{where}: score must be a whole number {MIN_SCORE}-{MAX_SCORE}, got '{raw}'")
    return int(raw)


def load_csv(path: Path, countries: CountryIndex) -> Dataset:
    """Long format, one row per country and question.

    Columns: country; dimension; question_id; score  [; question_label; question_text]
    Delimiter ';' or ','. Label and text may be given on any row of the question.
    """
    text = path.read_text(encoding="utf-8-sig")
    delimiter = ";" if text.splitlines()[0].count(";") >= text.splitlines()[0].count(",") else ","
    reader = csv.DictReader(text.splitlines(), delimiter=delimiter)
    header = [c.strip() for c in reader.fieldnames or []]
    reader.fieldnames = header
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        raise DataError(f"{path.name}: missing column(s) {', '.join(missing)}. Found: {', '.join(header)}")

    questions: dict[str, Question] = {}
    seen: set[tuple[str, str]] = set()  # includes rows with an empty score
    dataset = Dataset()
    for line_no, row in enumerate(reader, start=2):
        where = f"{path.name} line {line_no}"
        row = {k: (v or "").strip() for k, v in row.items() if k}
        if not any(row.values()):
            continue
        qid, dimension = row["question_id"], row["dimension"]
        if not qid or not dimension:
            raise DataError(f"{where}: question_id and dimension must not be empty")
        try:
            iso3 = countries.resolve(row["country"])
        except DataError as e:
            raise DataError(f"{where}: {e}") from None

        existing = questions.get(qid)
        if existing and existing.dimension != dimension:
            raise DataError(f"{where}: question '{qid}' is in dimension '{existing.dimension}' elsewhere, here '{dimension}'")
        # First non-empty label/text wins; the label falls back to the id.
        questions[qid] = Question(
            id=qid,
            dimension=dimension,
            label=(existing.label if existing else "") or row.get("question_label", ""),
            text=(existing.text if existing else "") or row.get("question_text", ""),
        )

        if (iso3, qid) in seen:
            raise DataError(f"{where}: duplicate entry for {row['country']} / {qid}")
        seen.add((iso3, qid))
        score = parse_score(row["score"], where)
        if score is not None:
            dataset.scores[(iso3, qid)] = score

    dataset.questions = [Question(q.id, q.dimension, q.label or q.id, q.text) for q in questions.values()]
    return dataset


def load_data(path: Path, countries: CountryIndex) -> Dataset:
    loaders = {".csv": load_csv}
    loader = loaders.get(path.suffix.lower())
    if loader is None:
        raise DataError(f"No loader for '{path.suffix}' files yet (supported: {', '.join(loaders)})")
    return loader(path, countries)


def load_focus_countries(path: Path, countries: CountryIndex) -> list[str]:
    """JSON: {"countries": ["Spanien", "PRT", ...]} or just the list."""
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    refs = raw["countries"] if isinstance(raw, dict) else raw
    focus: list[str] = []
    for ref in refs:
        iso3 = countries.resolve(ref)
        if iso3 in focus:
            raise DataError(f"{path.name}: '{ref}' is listed twice")
        focus.append(iso3)
    return focus
