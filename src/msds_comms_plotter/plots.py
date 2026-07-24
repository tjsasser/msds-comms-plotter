"""Visualizations for the World Cup 2022 dataset (matplotlib only)."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless rendering
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter, MaxNLocator

from msds_comms_plotter import worldcup

# Final standings top 3, with validated categorical colors (palette slots 1-3,
# which clear the all-pairs CVD checks). The tournament average is drawn as a
# neutral reference line, not a categorical entity.
TOP3 = ["Argentina", "France", "Croatia"]
TEAM_COLOR = {"Argentina": "#2a78d6", "France": "#eb6834", "Croatia": "#1baf7a"}
TEAM_MARKER = {"Argentina": "o", "France": "s", "Croatia": "^"}
AVG_COLOR = "#52514e"

FIG_DIR = worldcup.PROJECT_ROOT / "reports" / "figures"


def _mmss(x, _pos=None):
    x = max(0.0, x)
    return f"{int(x):02d}:{int(round((x - int(x)) * 60)) % 60:02d}"


def goal_timing_top3_vs_average(goals=None, save=True):
    """Plot when the top-3 teams score their Nth goal vs the tournament average.

    X axis = goal number within a match (1st, 2nd, 3rd ... goal a team scored).
    Y axis = clock time it was scored (mm:ss). Faint markers show every
    individual team-match goal; bold lines show each team's per-ordinal mean;
    the dashed line is the mean across all 32 teams.
    """
    if goals is None:
        goals = worldcup.build_goal_events()

    # Cap the x-axis at the highest goal number any top-3 team reached, so the
    # comparison isn't stretched by lopsided routs (e.g. Spain 7-0).
    max_n = int(goals[goals["team"].isin(TOP3)]["goal_number"].max())
    xs = range(1, max_n + 1)

    fig, ax = plt.subplots(figsize=(9, 6))
    ax.set_axisbelow(True)
    ax.grid(True, axis="y", color="#e6e6e3", linewidth=0.8)

    # Tournament average (all teams) per goal number, restricted to xs.
    grp = goals[goals["goal_number"] <= max_n].groupby("goal_number")["time_min"]
    avg = grp.mean().reindex(xs)
    counts = grp.count().reindex(xs)
    ax.plot(avg.index, avg.values, color=AVG_COLOR, lw=2.2, ls="--",
            marker="D", ms=6, zorder=5, label="All teams (avg)")
    # Annotate how many team-matches back each average point.
    for n in xs:
        ax.annotate(f"n={int(counts[n])}", (n, avg[n]), textcoords="offset points",
                    xytext=(0, -14), ha="center", fontsize=7.5, color=AVG_COLOR)

    # Each top-3 team: faint per-game points + bold mean line.
    for team in TOP3:
        sub = goals[goals["team"] == team]
        color = TEAM_COLOR[team]
        ax.scatter(sub["goal_number"], sub["time_min"], s=28, color=color,
                   alpha=0.28, zorder=2, edgecolors="none")
        mean = sub.groupby("goal_number")["time_min"].mean().reindex(xs)
        ax.plot(mean.index, mean.values, color=color, lw=2.2,
                marker=TEAM_MARKER[team], ms=8, zorder=4,
                markeredgecolor="white", markeredgewidth=0.8, label=team)

    ax.set_xlabel("Goal number in the match (1st, 2nd, 3rd ...)")
    ax.set_ylabel("Time scored (mm:ss)")
    ax.set_title("When do the top 3 teams score? — World Cup 2022",
                 fontsize=14, fontweight="bold")
    ax.xaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_xlim(0.7, max_n + 0.3)
    ax.set_ylim(0, max(95, goals["time_min"].max() + 5))
    ax.yaxis.set_major_formatter(FuncFormatter(_mmss))
    ax.axhline(45, color="#c3c2b7", lw=0.8, ls=":", zorder=1)
    ax.text(max_n + 0.25, 45, " HT", va="center", ha="left",
            fontsize=8, color="#8a8981")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(frameon=False, loc="upper left", fontsize=10)
    fig.tight_layout()

    if save:
        FIG_DIR.mkdir(parents=True, exist_ok=True)
        out = FIG_DIR / "goal_timing_top3_vs_average.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        print(f"Wrote {out}")
    return fig, ax


def goal_timing_dotplot(goals=None, save=True):
    """Dot plot: each top-3 team vs the average of all *other* teams.

    One row per goal number (1st, 2nd, 3rd ... goal in a match); the x position
    of each dot is the mean clock time (mm:ss) that series scored its Nth goal.
    The reference series is the mean over every team except the top 3.
    """
    if goals is None:
        goals = worldcup.build_goal_events()

    max_n = int(goals[goals["team"].isin(TOP3)]["goal_number"].max())
    xs = list(range(1, max_n + 1))

    others = goals[~goals["team"].isin(TOP3)]
    others_mean = others.groupby("goal_number")["time_min"].mean().reindex(xs)
    others_n = others.groupby("goal_number")["time_min"].count().reindex(xs)

    team_means = {t: goals[goals["team"] == t].groupby("goal_number")["time_min"]
                  .mean().reindex(xs) for t in TOP3}

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.set_axisbelow(True)
    ax.grid(True, axis="x", color="#e6e6e3", linewidth=0.8)

    for n in xs:
        vals = [others_mean[n]] + [team_means[t][n] for t in TOP3]
        vals = [v for v in vals if v == v]  # drop NaN
        if len(vals) > 1:  # connector showing the spread across series
            ax.plot([min(vals), max(vals)], [n, n], color="#d8d8d4",
                    lw=3, solid_capstyle="round", zorder=1)

    # Reference: average of all other teams (neutral).
    ax.scatter(others_mean.values, xs, s=150, color="white",
               edgecolors=AVG_COLOR, linewidths=2.2, zorder=3,
               label="Other teams (avg)")
    # Top-3 teams.
    for t in TOP3:
        ax.scatter(team_means[t].values, xs, s=130, color=TEAM_COLOR[t],
                   marker=TEAM_MARKER[t], edgecolors="white", linewidths=0.9,
                   zorder=4, label=t)

    ax.set_yticks(xs)
    ax.set_yticklabels([f"{n}{'st' if n==1 else 'nd' if n==2 else 'rd' if n==3 else 'th'} goal"
                        for n in xs])
    ax.invert_yaxis()  # 1st goal at top
    ax.set_ylim(max_n + 0.6, 0.4)
    ax.set_xlabel("Mean time scored (mm:ss)")
    ax.set_title("When each goal arrives: top 3 vs. all other teams — World Cup 2022",
                 fontsize=13, fontweight="bold")
    ax.xaxis.set_major_formatter(FuncFormatter(_mmss))
    ax.axvline(45, color="#c3c2b7", lw=0.8, ls=":", zorder=1)
    ax.text(45, max_n + 0.5, "HT", va="bottom", ha="center",
            fontsize=8, color="#8a8981")
    for n in xs:  # sample size for the reference series
        ax.annotate(f"n={int(others_n[n])}", (others_mean[n], n),
                    textcoords="offset points", xytext=(0, 12),
                    ha="center", fontsize=7.5, color=AVG_COLOR)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(frameon=False, loc="lower right", fontsize=10, ncol=2)
    fig.tight_layout()

    if save:
        FIG_DIR.mkdir(parents=True, exist_ok=True)
        out = FIG_DIR / "goal_timing_dotplot.png"
        fig.savefig(out, dpi=150, bbox_inches="tight")
        print(f"Wrote {out}")
    return fig, ax


if __name__ == "__main__":
    goals = worldcup.build_goal_events()
    goal_timing_top3_vs_average(goals=goals)
    goal_timing_dotplot(goals=goals)
