"""Tests for the survey pipeline and helpers.  Run: python -m pytest -q (project root)."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pipeline import build  # noqa: E402
from survey_tools import code_open_ends, kish_ess, rake, two_prop_ci, weighted_shares  # noqa: E402


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    db = tmp_path_factory.mktemp("db") / "test.duckdb"
    c = build(db_path=db)
    yield c
    c.close()


# ---------- pipeline / data quality ----------
def test_staging_keeps_every_row(con):
    raw = con.execute("SELECT COUNT(*) FROM raw_survey").fetchone()[0]
    stg = con.execute("SELECT COUNT(*) FROM stg_survey").fetchone()[0]
    assert raw == stg == 4042


def test_submission_ids_unique(con):
    assert con.execute("SELECT COUNT(*) - COUNT(DISTINCT submission_id) FROM stg_survey").fetchone()[0] == 0


def test_ratings_within_scale(con):
    bad = con.execute("""SELECT COUNT(*) FROM stg_survey WHERE
        a_pref NOT BETWEEN 1 AND 5 OR b_pref NOT BETWEEN 1 AND 5 OR c_pref NOT BETWEEN 1 AND 5
        OR d_pref NOT BETWEEN 1 AND 5 OR expertise NOT BETWEEN 1 AND 10""").fetchone()[0]
    assert bad == 0


def test_analysis_base_excludes_flagged_rows(con):
    bad = con.execute("""SELECT COUNT(*) FROM mart_respondents WHERE COALESCE(dq_under_18, false)
        OR dq_incomplete_tasting OR dq_missing_outcome OR COALESCE(dq_straightlined, false)""").fetchone()[0]
    assert bad == 0


def test_exclusion_waterfall_is_monotonic(con):
    n = [r[0] for r in con.execute("SELECT respondents FROM mart_exclusions ORDER BY step").fetchall()]
    assert all(a >= b for a, b in zip(n, n[1:]))


def test_every_category_maps_to_an_order(con):
    # unmapped labels would silently become NULL ordinals
    assert con.execute("SELECT COUNT(*) FROM stg_survey WHERE age IS NOT NULL AND age_order IS NULL").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM stg_survey WHERE most_willing IS NOT NULL AND willing_order IS NULL").fetchone()[0] == 0


def test_shares_sum_to_one(con):
    sums = con.execute("SELECT expertise_band, SUM(share) FROM mart_pref_by_expertise GROUP BY 1").fetchall()
    assert all(abs(s - 1) < 1e-9 for _, s in sums)


# ---------- helpers ----------
def test_rake_hits_targets():
    df = pd.DataFrame({"g": ["M"] * 75 + ["F"] * 25})
    w = rake(df, {"g": {"M": 0.5, "F": 0.5}}, trim=(0.01, 100))
    s = weighted_shares(df.g, w)
    assert s["M"] == pytest.approx(0.5) and s["F"] == pytest.approx(0.5)
    assert w.mean() == pytest.approx(1.0)


def test_rake_leaves_out_of_scope_share_unchanged():
    df = pd.DataFrame({"g": ["M"] * 60 + ["F"] * 20 + ["X"] * 20})
    w = rake(df, {"g": {"M": 0.5, "F": 0.5}}, trim=(0.01, 100))
    s = weighted_shares(df.g, w)
    assert s["X"] == pytest.approx(0.2)
    assert s["M"] == pytest.approx(0.4)


def test_kish_ess_equal_weights_is_n():
    assert kish_ess(pd.Series(np.ones(50))) == pytest.approx(50)


def test_kish_ess_drops_with_unequal_weights():
    assert kish_ess(pd.Series([1.0] * 50 + [3.0] * 50)) < 100


def test_two_prop_ci_contains_diff():
    d, lo, hi = two_prop_ci(46, 100, 22, 100)
    assert d == pytest.approx(0.24) and lo < d < hi


def test_code_open_ends_multilabel():
    notes = pd.Series(["Fruity and a bit sour", "burnt, bitter", None])
    coded = code_open_ends(notes)
    assert coded.loc[0, "fruity / berry"] and coded.loc[0, "sour / acidic"]
    assert coded.loc[1, "bitter / burnt"] and not coded.loc[1, "fruity / berry"]
    assert not coded.loc[2].any()
