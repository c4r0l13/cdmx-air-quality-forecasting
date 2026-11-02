"""Next-day forecasts of PM2.5 and ozone with a walk-forward (year-by-year) backtest.

At the end of day t we know pollutants and weather up to t, plus the calendar
of day t+1. We forecast the daily mean of day t+1.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier, LGBMRegressor
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import average_precision_score, brier_score_loss, mean_absolute_error, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

POLLUTANTS = ["co", "no", "no2", "nox", "o3", "pm10", "pm25", "so2"]
METEO = ["rh", "tmp", "wsp", "wdr"]
PM25_THRESHOLD = 25.0  # WHO 2021 interim target 4, 24-hour mean
TEST_YEARS = [2019, 2020, 2021, 2022, 2023]


def features(df: pd.DataFrame) -> pd.DataFrame:
    """Features known at the end of day t, used to predict day t+1."""
    X = pd.DataFrame(index=df.index)
    for c in POLLUTANTS + ["rh", "tmp", "wsp"]:
        X[f"{c}_t"] = df[c]
    for c in ["pm25", "o3", "pm10", "no2"]:
        X[f"{c}_lag1"] = df[c].shift(1)
        X[f"{c}_mean7"] = df[c].rolling(7).mean()
        X[f"{c}_delta"] = df[c] - df[c].shift(1)
    X["wdr_sin"] = np.sin(np.deg2rad(df["wdr"]))
    X["wdr_cos"] = np.cos(np.deg2rad(df["wdr"]))
    nxt = df.index + pd.Timedelta(days=1)  # calendar of the target day is known in advance
    doy = nxt.dayofyear
    X["doy_sin"] = np.sin(2 * np.pi * doy / 365.25)
    X["doy_cos"] = np.cos(2 * np.pi * doy / 365.25)
    X["target_weekday"] = nxt.weekday
    X["target_is_holiday"] = ((nxt.month == 12) & (nxt.day.isin([24, 25, 31]))) | ((nxt.month == 1) & (nxt.day == 1))
    X["target_is_holiday"] = X["target_is_holiday"].astype(int)
    return X


def climatology(train: pd.Series, index: pd.DatetimeIndex) -> np.ndarray:
    """Average of the target for the same day-of-year (±7 days) in the training years."""
    doy = train.index.dayofyear
    clim = pd.Series(
        [train[np.abs(((doy - d + 182) % 365) - 182) <= 7].mean() for d in range(1, 367)], index=range(1, 367)
    )
    return clim.loc[index.dayofyear].to_numpy()


def backtest_regression(df: pd.DataFrame, target: str, seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    X = features(df)
    y = df[target].shift(-1).rename("y")  # next day's value
    data = X.join(y).dropna()
    preds = []
    for year in TEST_YEARS:
        tr, te = data[data.index.year < year], data[data.index.year == year]
        Xtr, ytr, Xte = tr.drop(columns="y"), tr["y"], te.drop(columns="y")
        out = pd.DataFrame({"y": te["y"]}, index=te.index)
        out["Persistence (today = tomorrow)"] = Xte[f"{target}_t"]
        out["Seasonal climatology"] = climatology(ytr, te.index + pd.Timedelta(days=1))
        out["Ridge regression"] = make_pipeline(StandardScaler(), Ridge(alpha=10)).fit(Xtr, ytr).predict(Xte)
        gbm = LGBMRegressor(
            n_estimators=500,
            learning_rate=0.03,
            num_leaves=15,
            min_child_samples=30,
            subsample=0.8,
            subsample_freq=1,
            colsample_bytree=0.8,
            random_state=seed,
            verbose=-1,
        )
        out["LightGBM"] = gbm.fit(Xtr, ytr).predict(Xte)
        preds.append(out)
    p = pd.concat(preds)
    models = [c for c in p.columns if c != "y"]
    rows = []
    for m in models:
        mae = mean_absolute_error(p["y"], p[m])
        row = {"model": m, "MAE": mae}
        for year in TEST_YEARS:
            s = p[p.index.year == year]
            row[str(year)] = mean_absolute_error(s["y"], s[m])
        rows.append(row)
    table = pd.DataFrame(rows).set_index("model")
    base = table.loc["Persistence (today = tomorrow)", "MAE"]
    table.insert(1, "skill_vs_persistence", 1 - table["MAE"] / base)
    return table, p


def backtest_exceedance(df: pd.DataFrame, threshold: float = PM25_THRESHOLD, seed: int = 0):
    X = features(df)
    y = (df["pm25"].shift(-1) > threshold).astype(float).where(df["pm25"].shift(-1).notna()).rename("y")
    data = X.join(y).dropna()
    preds = []
    for year in TEST_YEARS:
        tr, te = data[data.index.year < year], data[data.index.year == year]
        Xtr, ytr, Xte = tr.drop(columns="y"), tr["y"], te.drop(columns="y")
        out = pd.DataFrame({"y": te["y"]}, index=te.index)
        out["Persistence"] = (Xte["pm25_t"] > threshold).astype(float)
        out["Logistic regression"] = (
            make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=0.5))
            .fit(Xtr, ytr)
            .predict_proba(Xte)[:, 1]
        )
        gbm = LGBMClassifier(
            n_estimators=400,
            learning_rate=0.03,
            num_leaves=15,
            min_child_samples=30,
            subsample=0.8,
            subsample_freq=1,
            colsample_bytree=0.8,
            random_state=seed,
            verbose=-1,
        )
        out["LightGBM"] = gbm.fit(Xtr, ytr).predict_proba(Xte)[:, 1]
        preds.append(out)
    p = pd.concat(preds)
    rows = []
    for m in [c for c in p.columns if c != "y"]:
        alert = p[m] >= 0.5
        tp = (alert & (p["y"] == 1)).sum()
        rows.append(
            {
                "model": m,
                "ROC-AUC": roc_auc_score(p["y"], p[m]) if p[m].nunique() > 2 else np.nan,
                "PR-AUC": average_precision_score(p["y"], p[m]) if p[m].nunique() > 2 else np.nan,
                "Brier": brier_score_loss(p["y"], p[m]),
                "recall@0.5": tp / max((p["y"] == 1).sum(), 1),
                "precision@0.5": tp / max(alert.sum(), 1),
            }
        )
    return pd.DataFrame(rows).set_index("model"), p
