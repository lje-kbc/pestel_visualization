"""Internal data model. Every loader produces a Dataset; everything downstream only sees this."""

from dataclasses import dataclass, field

MIN_SCORE = 1
MAX_SCORE = 5


class DataError(ValueError):
    """Invalid input data. The message is meant to be shown to the user as-is."""


@dataclass(frozen=True)
class Question:
    id: str
    dimension: str
    label: str  # short, used as tab title
    text: str = ""  # optional long question, shown as subtitle


@dataclass
class Dataset:
    questions: list[Question] = field(default_factory=list)
    # (iso3, question_id) -> integer score 1..5
    scores: dict[tuple[str, str], int] = field(default_factory=dict)
