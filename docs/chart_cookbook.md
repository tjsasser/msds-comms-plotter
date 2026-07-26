# Altair chart cookbook

One recipe per chart type used in this project: what it looks like, and the
core Altair code to build it. The snippets are trimmed to the essential
`mark` + `encode` so the technique is clear — the full themed, interactive
versions live in
[`msds_comms_plotter.altair_charts`](../src/msds_comms_plotter/altair_charts.py)
(call `ac.bar_goals_by_team()`, `ac.line_cumulative_goals()`, …). Every chart
first picks up the shared look with:

```python
import altair as alt
from msds_comms_plotter import chartkit
chartkit.enable_altair_theme()   # JetBrains Mono, shared palette, minimal chrome
```

Data comes from the processed tables and the event builders in
[`worldcup.py`](../src/msds_comms_plotter/worldcup.py); see
[`wc2022_data.md`](wc2022_data.md) for columns.

---

## 1. Bar chart — `mark_bar`

Magnitude across a category. One measure, one categorical axis, single hue;
rank is carried by length and the sort order.

![Bar chart of goals per team](../reports/figures/alt_bar_goals_by_team.png)

```python
# by_team: columns "team", "goals"
alt.Chart(by_team).mark_bar().encode(
    x=alt.X("goals:Q", title="Goals scored"),
    y=alt.Y("team:N", sort="-x", title=None),   # sort teams by the x value
)
```

---

## 2. Line chart — `mark_line`

Change over time. Here goals are summed per match-day and accumulated into a
monotone curve. `point=True` marks each observation.

![Line chart of cumulative goals](../reports/figures/alt_line_cumulative_goals.png)

```python
# daily: columns "match_date" (datetime), "cumulative_goals"
alt.Chart(daily).mark_line(point=True).encode(
    x=alt.X("match_date:T", title="Match date"),
    y=alt.Y("cumulative_goals:Q", title="Cumulative goals"),
)
```

---

## 3. Scatter plot — `mark_point`

Relationship between two continuous measures — one dot per record.

![Scatter of xG vs goals](../reports/figures/alt_scatter_xg_vs_goals.png)

```python
# players: columns "xg", "goals"
alt.Chart(players).mark_point(filled=True, size=70).encode(
    x=alt.X("xg:Q", title="Expected goals (xG)"),
    y=alt.Y("goals:Q", title="Goals scored"),
)
```

Add a `y = x` reference line by layering a second chart:

```python
diag = alt.Chart(alt.Data(values=[{"v": 0}, {"v": 9}])).mark_line(
    strokeDash=[4, 4]).encode(x="v:Q", y="v:Q")
chart = diag + points
```

---

## 4. Histogram — `mark_bar` with `bin`

Distribution of a *continuous* variable: bin it, then count. A histogram is a
bar chart whose x is binned.

![Histogram of goal minutes](../reports/figures/alt_hist_goal_minutes.png)

```python
# goals: one row per goal, column "minute"
alt.Chart(goals).mark_bar().encode(
    x=alt.X("minute:Q", bin=alt.Bin(step=5), title="Match minute"),
    y=alt.Y("count():Q", title="Goals scored"),   # count() aggregates per bin
)
```

---

## 5. Heatmap — `mark_rect`

Two categorical axes with a magnitude in each cell, shaded by a **sequential**
color ramp.

![Heatmap of goals by team and phase](../reports/figures/alt_heatmap_team_phase.png)

```python
# counts: columns "team", "phase", "goals"
alt.Chart(counts).mark_rect(stroke="white", strokeWidth=2).encode(
    x=alt.X("phase:N", title="Match phase"),
    y=alt.Y("team:N", title=None),
    color=alt.Color("goals:Q", scale=alt.Scale(scheme="viridis")),
)
```

---

## 6. Linked brush — `selection_interval` (crossfilter)

Altair's signature interaction: **drag a box** on the scatter and a second
view re-aggregates to only the selected points; the rest fade to grey. One
selection drives both marks.

![Brushable scatter linked to count bars](../reports/figures/alt_brush_position_counts.png)

```python
brush = alt.selection_interval()
color = alt.Color("position:N")

points = alt.Chart(players).mark_point(filled=True).encode(
    x="xg:Q", y="goals:Q",
    # selected points keep their category color; the rest go grey
    color=alt.when(brush).then(color).otherwise(alt.value("lightgray")),
).add_params(brush)

bars = alt.Chart(players).mark_bar().encode(
    y="position:N", x="count():Q", color=color,
).transform_filter(brush)          # only the brushed points are counted

points & bars                      # vertical concatenation
```

The **passing** chart (`ac.linked_scatter_passing`) is the same pattern with a
player-name search box and a live color-scheme dropdown added on top.

---

## 7. Point paths on hover — `mark_trail` + hover selection

Each entity is a trajectory over an ordered dimension. Hovering one traces its
whole path as a tapering trail; the rest stay dim. (Abbreviated — the full
builder adds a match-number slider and a team search box.)

![Team paths through the tournament](../reports/figures/alt_point_paths_hover.png)

```python
hover = alt.selection_point(on="mouseover", fields=["team"], empty=False)

# team_matches: columns "xg", "goals", "team", "match_num"
base = alt.Chart(team_matches).encode(x="xg:Q", y="goals:Q", detail="team:N")

points = base.mark_circle(size=110).add_params(hover)
trail = base.mark_trail().encode(
    order=alt.Order("match_num:Q"),                 # connect in match order
    size=alt.Size("match_num:Q", legend=None),      # taper over time
    opacity=alt.when(hover).then(alt.value(0.4)).otherwise(alt.value(0)),
)
trail + points
```

---

## 8. Horizon graph — layered clipped `mark_area`

Compresses a tall time series into a short band: fold it into N layers, each a
clipped area of the amount spilling past its threshold, so busier values stack
into darker color.

![Horizon graph of shots per minute](../reports/figures/alt_horizon_shots.png)

```python
import math
# per_min: columns "minute", "shots"
bands = 4
band = math.ceil(per_min["shots"].max() / bands)

layers = [
    alt.Chart(per_min)
       .transform_calculate(v=f"clamp(datum.shots - {k * band}, 0, {band})")
       .mark_area(clip=True, interpolate="monotone", opacity=0.5)
       .encode(x=alt.X("minute:Q", title="Match minute"),
               y=alt.Y("v:Q", scale=alt.Scale(domain=[0, band]), axis=None))
    for k in range(bands)
]
alt.layer(*layers)
```

---

## Saving a chart

Any chart is an `alt.Chart`; save it as interactive HTML or a static PNG:

```python
chart.save("chart.html")            # interactive; add inline=True for offline
chart.save("chart.png", ppi=200)    # needs vl-convert-python (the [png] extra)
```

To see them all together with the shared color pickers, run the gallery:

```bash
python examples/show_wc2022_charts.py
```
