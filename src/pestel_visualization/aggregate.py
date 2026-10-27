"""Turn a Dataset into map views: one per question, one per dimension, and an overall view.

Means are computed exactly (Fractions) and never rounded in between; only the final
value is rounded half-up into a colour category 1..5.
"""

import math
from dataclasses import dataclass
from fractions import Fraction

from .model import Dataset, Question

PESTEL_ORDER = ["political", "economic", "economical", "social", "technological", "environmental", "legal"]


@dataclass(frozen=True)
class Result:
    value: Fraction | None  # None = no data
    available: int  # questions with a score
    total: int  # questions in this view

    @property
    def category(self) -> int | None:
        return None if self.value is None else round_half_up(self.value)


@dataclass(frozen=True)
class View:
    id: str
    kind: str  # "question" | "dimension" | "overall"
    label: str
    dimension: str | None
    description: str
    results: dict[str, Result]


def round_half_up(value: Fraction) -> int:
    return math.floor(value + Fraction(1, 2))


def mean(values: list[Fraction]) -> Fraction | None:
    return sum(values, Fraction(0)) / len(values) if values else None


def dimension_order(dimensions: list[str]) -> list[str]:
    def key(d: str):
        k = d.casefold()
        return (PESTEL_ORDER.index(k) if k in PESTEL_ORDER else len(PESTEL_ORDER), k)

    return sorted(dimensions, key=key)


def build_views(dataset: Dataset, focus: list[str]) -> list[View]:
    by_dimension: dict[str, list[Question]] = {}
    for q in dataset.questions:
        by_dimension.setdefault(q.dimension, []).append(q)

    def dimension_result(iso3: str, questions: list[Question]) -> Result:
        scores = [Fraction(dataset.scores[(iso3, q.id)]) for q in questions if (iso3, q.id) in dataset.scores]
        return Result(mean(scores), len(scores), len(questions))

    # Order: overall, then per dimension its average followed by its questions.
    views: list[View] = []
    dimensions = dimension_order(list(by_dimension))
    if len(dimensions) > 1:
        overall: dict[str, Result] = {}
        for c in focus:
            per_dim = [dimension_result(c, by_dimension[d]) for d in dimensions]
            overall[c] = Result(
                mean([r.value for r in per_dim if r.value is not None]),
                sum(r.available for r in per_dim),
                sum(r.total for r in per_dim),
            )
        views.append(View(id="overall", kind="overall", label="Overall", dimension=None, description="", results=overall))

    for dim in dimensions:
        questions = by_dimension[dim]
        if len(questions) > 1:
            views.append(
                View(
                    id=f"d:{dim}",
                    kind="dimension",
                    label=dim,
                    dimension=dim,
                    description="",
                    results={c: dimension_result(c, questions) for c in focus},
                )
            )
        for q in questions:
            views.append(
                View(
                    id=f"q:{q.id}",
                    kind="question",
                    label=q.label,
                    dimension=dim,
                    description=q.text,
                    results={c: dimension_result(c, [q]) for c in focus},
                )
            )
    return views
