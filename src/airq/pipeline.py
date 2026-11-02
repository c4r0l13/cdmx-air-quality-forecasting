"""SQL analysis + forecasting backtests + figures. Run: python -m airq.pipeline"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import db, style
from .forecast import PM25_THRESHOLD, TEST_YEARS, backtest_exceedance, backtest_regression

OUT = Path("reports")


def fig_overview(df: pd.DataFrame, figs: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10, 5.2), sharex=True)
    for ax, col, label, color in (
        (axes[0], "pm25", "PM2.5 (µg/m³)", style.SERIES[0]),
        (axes[1], "o3", "Ozone (ppb)", style.SERIES[1]),
    ):
        ax.plot(df.index, df[col], color=color, lw=0.4, alpha=0.45)
        ax.plot(df.index, df[col].rolling(30, center=True).mean(), color=color, lw=1.8)
        ax.set_ylabel(label)
    axes[0].axhline(PM25_THRESHOLD, color=style.INK_2, ls="--", lw=1)
    axes[0].text(
        df.index[-1],
        PM25_THRESHOLD + 2,
        "WHO interim target 4 (25 µg/m³)",
        fontsize=8,
        color=style.INK_2,
        ha="right",
        va="bottom",
        bbox={"facecolor": style.SURFACE, "edgecolor": "none", "pad": 1},
    )
    for ax in axes:
        ax.axvspan(pd.Timestamp("2020-03-23"), pd.Timestamp("2020-05-31"), color=style.GRID, alpha=0.8, lw=0)
    axes[0].text(
        pd.Timestamp("2020-04-10"),
        df["pm25"].max() * 0.92,
        "COVID\nlockdown",
        fontsize=8,
        color=style.INK_2,
        ha="center",
        va="top",
    )
    axes[0].set_title("Mexico City daily air quality 2015–2023 (thin: daily, thick: 30-day mean)")
    axes[1].xaxis.set_major_locator(mdates.YearLocator())
    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    fig.savefig(figs / "overview.png")
    plt.close(fig)


def fig_seasonal_weekday(df: pd.DataFrame, figs: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.8))
    m = df.groupby(df.index.month)[["pm25", "o3"]].mean()
    axes[0].plot(m.index, m["pm25"], marker="o", color=style.SERIES[0], label="PM2.5 (µg/m³)")
    axes[0].plot(m.index, m["o3"], marker="o", color=style.SERIES[1], label="Ozone (ppb)")
    axes[0].set_xticks(range(1, 13), list("JFMAMJJASOND"))
    axes[0].set_title("Dry season is worst; rains clean the air")
    axes[0].legend(loc="lower left")
    w = df.groupby(df.index.weekday)[["no2", "o3"]].mean()
    w = w / w.mean() * 100 - 100
    x = np.arange(7)
    axes[1].bar(x - 0.2, w["no2"], 0.38, color=style.SERIES[2], label="NO₂ (traffic)")
    axes[1].bar(x + 0.2, w["o3"], 0.38, color=style.SERIES[1], label="Ozone")
    axes[1].axhline(0, color=style.INK_2, lw=0.8)
    axes[1].set_xticks(x, ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
    axes[1].set_ylabel("% vs weekly average")
    axes[1].set_title("Weekend effect: less traffic, more ozone")
    axes[1].legend(loc="lower left")
    axes[1].grid(axis="x", visible=False)
    fig.tight_layout()
    fig.savefig(figs / "seasonality_weekday.png")
    plt.close(fig)


def fig_covid(df: pd.DataFrame, figs: Path) -> dict:
    am = df[df.index.month.isin([4, 5])]
    base = am[am.index.year.isin(range(2015, 2020))][["no2", "co", "pm25", "o3"]].mean()
    lock = am[am.index.year == 2020][["no2", "co", "pm25", "o3"]].mean()
    change = (lock / base - 1) * 100
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    labels = {"co": "CO", "no2": "NO₂", "pm25": "PM2.5", "o3": "Ozone"}
    order = ["co", "no2", "pm25", "o3"]
    colors = [style.SERIES[0] if change[c] < 0 else style.SERIES[1] for c in order]
    ax.barh([labels[c] for c in order], change[order], color=colors, height=0.6)
    for i, c in enumerate(order):
        v = change[c]
        ax.text(
            v + (1.5 if v >= 0 else -1.5),
            i,
            f"{v:+.0f}%",
            va="center",
            ha="left" if v >= 0 else "right",
            fontsize=9,
            color=style.INK,
        )
    ax.axvline(0, color=style.INK_2, lw=0.8)
    ax.set_xlim(-65, 25)
    ax.set_xlabel("April–May 2020 vs April–May 2015–2019")
    ax.set_title("Lockdown cut traffic pollution, but ozone went up")
    ax.grid(axis="y", visible=False)
    fig.savefig(figs / "covid_lockdown.png")
    plt.close(fig)
    return {k: round(float(v), 1) for k, v in change.items()}


def fig_forecast(pred: pd.DataFrame, figs: Path) -> None:
    s = pred.loc["2022-01-01":"2022-06-30"]
    fig, ax = plt.subplots(figsize=(10, 3.8))
    ax.plot(s.index, s["y"], color=style.INK_2, lw=1.2, label="Observed")
    ax.plot(s.index, s["LightGBM"], color=style.SERIES[0], lw=1.4, label="LightGBM forecast (day ahead)")
    ax.plot(
        s.index,
        s["Persistence (today = tomorrow)"],
        color=style.SERIES[1],
        lw=0.9,
        alpha=0.7,
        ls="--",
        label="Persistence",
    )
    ax.axhline(PM25_THRESHOLD, color=style.MUTED, ls=":", lw=1)
    ax.set_ylabel("PM2.5 (µg/m³)")
    ax.set_title("Next-day PM2.5 forecast, first half of 2022 (out of sample)")
    ax.legend(loc="upper right", ncol=3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    fig.savefig(figs / "pm25_forecast_2022.png")
    plt.close(fig)


def fig_skill(tables: dict[str, pd.DataFrame], figs: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6), sharey=True)
    for ax, (name, t) in zip(axes, tables.items(), strict=True):
        t = t.drop(index="Persistence (today = tomorrow)")
        colors = [style.SERIES[0] if v > 0 else style.SERIES[7] for v in t["skill_vs_persistence"]]
        ax.barh(t.index, t["skill_vs_persistence"] * 100, color=colors, height=0.6)
        for i, v in enumerate(t["skill_vs_persistence"] * 100):
            ax.text(
                v + (0.5 if v >= 0 else -0.5),
                i,
                f"{v:+.1f}%",
                va="center",
                ha="left" if v >= 0 else "right",
                fontsize=9,
                color=style.INK,
            )
        ax.axvline(0, color=style.INK_2, lw=0.8)
        ax.set_title(name)
        ax.set_xlabel("MAE improvement over persistence (%)")
        ax.grid(axis="y", visible=False)
        ax.set_xlim(min(-25, t["skill_vs_persistence"].min() * 130), max(30, t["skill_vs_persistence"].max() * 140))
    fig.suptitle(
        f"Forecast skill, walk-forward backtest {TEST_YEARS[0]}–{TEST_YEARS[-1]}",
        x=0.01,
        ha="left",
        fontsize=12,
        fontweight="bold",
        color=style.INK,
    )
    fig.tight_layout()
    fig.savefig(figs / "forecast_skill.png")
    plt.close(fig)


def main() -> None:
    figs = OUT / "figures"
    figs.mkdir(parents=True, exist_ok=True)
    style.apply_style()
    db.main()  # SQL answers -> reports/sql_answers.md
    con = db.build_db(":memory:")
    df = db.daily_frame(con)

    fig_overview(df, figs)
    fig_seasonal_weekday(df, figs)
    covid = fig_covid(df, figs)

    pm, pm_pred = backtest_regression(df, "pm25")
    o3, _ = backtest_regression(df, "o3")
    exc, _ = backtest_exceedance(df)
    fig_forecast(pm_pred, figs)
    fig_skill({"PM2.5": pm, "Ozone": o3}, figs)

    metrics = {
        "data": {"days": len(df), "start": str(df.index.min().date()), "end": str(df.index.max().date())},
        "covid_change_pct": covid,
        "pm25_regression": pm.round(4).to_dict(orient="index"),
        "o3_regression": o3.round(4).to_dict(orient="index"),
        "pm25_exceedance": exc.round(4).to_dict(orient="index"),
        "exceedance_base_rate_test": float((pm_pred["y"] > 25).mean()),
    }
    (OUT / "metrics.json").write_text(json.dumps(metrics, indent=2, default=float))
    md = [
        "# Forecast results",
        "",
        f"Walk-forward backtest: train on all years before, test on each year {TEST_YEARS}.",
        "",
        "## Next-day PM2.5 (MAE, µg/m³)",
        "",
        pm.round(3).to_markdown(),
        "",
        "## Next-day ozone (MAE, ppb)",
        "",
        o3.round(3).to_markdown(),
        "",
        f"## Will tomorrow exceed {PM25_THRESHOLD:.0f} µg/m³ PM2.5?",
        "",
        exc.round(3).to_markdown(),
        "",
    ]
    (OUT / "results.md").write_text("\n".join(md))
    print(pm.round(3).to_string())
    print(o3.round(3).to_string())
    print(exc.round(3).to_string())
    print(covid)
    print("base rate", metrics["exceedance_base_rate_test"])


if __name__ == "__main__":
    main()
