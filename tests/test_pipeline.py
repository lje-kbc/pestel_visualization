from fractions import Fraction
from pathlib import Path

import pytest

from pestel_visualization.aggregate import build_views, round_half_up
from pestel_visualization.cli import main
from pestel_visualization.countries import country_index
from pestel_visualization.loaders import load_csv
from pestel_visualization.model import Dataset, DataError, Question

ROOT = Path(__file__).resolve().parents[1]
HEADER = "country;dimension;question_id;question_label;question_text;score\n"


def write_csv(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "scores.csv"
    path.write_text(HEADER + body, encoding="utf-8")
    return path


def views_by_id(dataset: Dataset, focus: list[str]):
    return {v.id: v for v in build_views(dataset, focus)}


# ---------- rounding ----------

@pytest.mark.parametrize(
    "value, expected",
    [(Fraction(5, 2), 3), (Fraction(7, 2), 4), (Fraction(9, 2), 5), (Fraction(3, 2), 2),
     (Fraction(7, 3), 2), (Fraction(8, 3), 3), (Fraction(1), 1)],
)
def test_round_half_up(value, expected):
    assert round_half_up(value) == expected


# ---------- aggregation ----------

def test_dimension_mean_is_unrounded_and_category_rounds_half_up():
    ds = Dataset(
        questions=[Question("Q1", "Economic", "Q1"), Question("Q2", "Economic", "Q2")],
        scores={("ESP", "Q1"): 2, ("ESP", "Q2"): 3},
    )
    r = views_by_id(ds, ["ESP"])["d:Economic"].results["ESP"]
    assert r.value == Fraction(5, 2)
    assert r.category == 3
    assert (r.available, r.total) == (2, 2)


def test_partial_data_uses_available_questions():
    ds = Dataset(
        questions=[Question("Q1", "Economic", "Q1"), Question("Q2", "Economic", "Q2")],
        scores={("ESP", "Q1"): 4},
    )
    views = views_by_id(ds, ["ESP", "PRT"])
    assert views["d:Economic"].results["ESP"].value == 4
    assert views["d:Economic"].results["ESP"].available == 1
    assert views["d:Economic"].results["PRT"].value is None
    assert views["q:Q2"].results["ESP"].category is None


def test_overall_weights_dimensions_equally_without_intermediate_rounding():
    ds = Dataset(
        questions=[
            Question("E1", "Economic", "E1"), Question("E2", "Economic", "E2"),
            Question("S1", "Social", "S1"), Question("S2", "Social", "S2"),
        ],
        # Economic 2.5, Social 3.5 -> overall 3.0 (rounding first would give 3 and 4 -> 3.5 -> 4)
        scores={("ESP", "E1"): 2, ("ESP", "E2"): 3, ("ESP", "S1"): 3, ("ESP", "S2"): 4},
    )
    r = views_by_id(ds, ["ESP"])["overall"].results["ESP"]
    assert r.value == 3
    assert r.category == 3
    assert (r.available, r.total) == (4, 4)


def test_overall_with_uneven_dimensions():
    ds = Dataset(
        questions=[Question("E1", "Economic", "E1"), Question("S1", "Social", "S1"),
                   Question("S2", "Social", "S2"), Question("S3", "Social", "S3")],
        scores={("ESP", "E1"): 2, ("ESP", "S1"): 3, ("ESP", "S2"): 4, ("ESP", "S3"): 3},
    )
    # Economic 2, Social 10/3 -> (2 + 10/3) / 2 = 8/3, not the plain mean of all four scores (3)
    assert views_by_id(ds, ["ESP"])["overall"].results["ESP"].value == Fraction(8, 3)


def test_view_set_and_order():
    ds = Dataset(questions=[Question("S1", "Social", "S1"), Question("E1", "Economic", "E1"), Question("E2", "Economic", "E2")])
    ids = [v.id for v in build_views(ds, ["ESP"])]
    # overall first, PESTEL order, dimension average (only with >1 question) before its questions
    assert ids == ["overall", "d:Economic", "q:E1", "q:E2", "q:S1"]


def test_single_dimension_has_no_overall_view():
    ds = Dataset(questions=[Question("E1", "Economic", "E1"), Question("E2", "Economic", "E2")])
    assert "overall" not in views_by_id(ds, ["ESP"])


# ---------- CSV loading ----------

def test_csv_resolves_german_names_and_keeps_labels(tmp_path):
    path = write_csv(tmp_path, "Spanien;Economic;Q1;Labour;Long text;4\nKosovo;Economic;Q1;;;\nTürkei;Economic;Q1;;;5\n")
    ds = load_csv(path, country_index())
    assert ds.scores == {("ESP", "Q1"): 4, ("TUR", "Q1"): 5}
    assert ds.questions == [Question("Q1", "Economic", "Labour", "Long text")]


def test_label_falls_back_to_question_id(tmp_path):
    ds = load_csv(write_csv(tmp_path, "ESP;Economic;Q7;;;4\n"), country_index())
    assert ds.questions[0].label == "Q7"


@pytest.mark.parametrize("bad", ["0", "6", "3.5", "3,5", "good", "-1"])
def test_invalid_scores_are_rejected(tmp_path, bad):
    with pytest.raises(DataError, match="line 2"):
        load_csv(write_csv(tmp_path, f"ESP;Economic;Q1;;;{bad}\n"), country_index())


def test_unknown_country_is_rejected(tmp_path):
    with pytest.raises(DataError, match="Atlantis"):
        load_csv(write_csv(tmp_path, "Atlantis;Economic;Q1;;;3\n"), country_index())


def test_duplicate_rows_are_rejected(tmp_path):
    with pytest.raises(DataError, match="duplicate"):
        load_csv(write_csv(tmp_path, "ESP;Economic;Q1;;;3\nSpanien;Economic;Q1;;;\n"), country_index())


def test_question_in_two_dimensions_is_rejected(tmp_path):
    with pytest.raises(DataError, match="dimension"):
        load_csv(write_csv(tmp_path, "ESP;Economic;Q1;;;3\nPRT;Social;Q1;;;3\n"), country_index())


def test_comma_delimiter_is_accepted(tmp_path):
    path = tmp_path / "scores.csv"
    path.write_text("country,dimension,question_id,score\nESP,Economic,Q1,2\n", encoding="utf-8")
    assert load_csv(path, country_index()).scores == {("ESP", "Q1"): 2}


# ---------- end to end ----------

def test_cli_builds_self_contained_html(tmp_path):
    out = tmp_path / "not_yet_created" / "map.html"
    code = main(["--data", str(ROOT / "data/sample_scores.csv"), "--countries", str(ROOT / "config/countries.json"), "--out", str(out)])
    assert code == 0
    html = out.read_text(encoding="utf-8")
    assert "__DATA__" not in html and "__WORLD__" not in html and "__D3__" not in html
    assert "<script src=" not in html  # nothing loaded from the network
    assert '"XKX"' in html


def test_cli_rejects_scores_outside_focus_list(tmp_path, capsys):
    data = write_csv(tmp_path, "Frankreich;Economic;Q1;;;3\n")
    focus = tmp_path / "focus.json"
    focus.write_text('{"countries": ["Spanien"]}', encoding="utf-8")
    assert main(["--data", str(data), "--countries", str(focus), "--out", str(tmp_path / "x.html")]) == 1
    assert "France" in capsys.readouterr().err
