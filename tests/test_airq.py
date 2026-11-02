import numpy as np
import pandas as pd
import pytest

from airq.db import parse_questions
from airq.forecast import climatology, features


@pytest.fixture
def daily():
    idx = pd.date_range("2015-01-01", periods=800, freq="D")
    rng = np.random.default_rng(0)
    seas = 10 * np.sin(2 * np.pi * idx.dayofyear / 365.25)
    df = pd.DataFrame(index=idx)
    for c in ["co", "no", "no2", "nox", "o3", "pm10", "pm25", "so2", "rh", "tmp", "wsp"]:
        df[c] = 20 + seas + rng.normal(0, 2, len(idx))
    df["wdr"] = rng.uniform(0, 360, len(idx))
    return df


def test_features_use_only_past_and_target_calendar(daily):
    X = features(daily)
    shocked = daily.copy()
    shocked.iloc[500:, :] += 1000  # future shock
    Xs = features(shocked)
    pd.testing.assert_frame_equal(X.iloc[:500], Xs.iloc[:500])
    # calendar features describe the NEXT day
    assert X.loc["2015-12-31", "target_is_holiday"] == 1
    assert X.loc["2015-12-23", "target_is_holiday"] == 1  # 24 Dec is next
    assert X.loc["2015-12-26", "target_is_holiday"] == 0


def test_climatology_matches_seasonal_mean(daily):
    train = daily["pm25"].loc[:"2016-06-30"]
    target_idx = pd.date_range("2016-07-01", periods=30)
    clim = climatology(train, target_idx)
    assert np.allclose(clim, train[train.index.month == 7].mean(), atol=3)


def test_sql_question_parser():
    text = "-- name: a\n-- q: Question A?\nSELECT 1;\n\n-- name: b\n-- q: Question B?\nSELECT 2 AS x;\n"
    qs = parse_questions(text)
    assert [q["name"] for q in qs] == ["a", "b"]
    assert qs[1]["question"] == "Question B?" and "SELECT 2" in qs[1]["sql"]
