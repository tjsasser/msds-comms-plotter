# msds-comms-plotter

A small teaching library for the MSDS 610 (Communications for Analytics)
coursework. It bundles a tiny pandas data layer, a World Cup 2022 example
dataset with matplotlib figures, and **`chartkit`** — a styling toolkit that
gives **matplotlib** and **Altair** one shared visual identity.

## General

The package ships three things:

| Module | What it does |
| --- | --- |
| `msds_comms_plotter.altair_charts` | The **Passing: volume vs accuracy** Altair chart — a linked-brush scatter with a player-name search box and a color-scheme dropdown. |
| `msds_comms_plotter.chartkit` | Shared theming for matplotlib **and** Altair. |

### About `chartkit`

matplotlib and Altair are independent renderers: matplotlib draws static
figures in Python, while Altair emits [Vega-Lite](https://vega.github.io/vega-lite/)
JSON that renders in a browser. You can't stack one on the other. What
`chartkit` does instead is give both the **same** visual identity so a static
matplotlib figure and an interactive Altair chart look like siblings:

- **One typeface** — JetBrains Mono, with a monospace fallback stack.
- **One palette** — a calm, colorblind-aware 8-color categorical set, plus a
  sequential (`viridis`) and diverging (`redblue`) scheme for magnitude and
  polarity data.
- **Matching minimal chrome** — left-aligned bold titles, quiet horizontal-only
  gridlines, no top/right spines, tickless axes.

> **Font note:** JetBrains Mono must be installed for matplotlib to use it, and
> available to the browser (e.g. via a webfont) for Altair. Both fall back to a
> generic monospace stack otherwise — nothing breaks, the type just changes.
> Get the font at <https://www.jetbrains.com/lp/mono/>.

## Installation

Requires **Python ≥ 3.9**.

### Install from PyPI

```bash
pip install msds-comms-plotter        # add "[png]" for static PNG export
```

The World Cup data is bundled inside the package, so the chart works with no
extra setup:

```python
from msds_comms_plotter import altair_charts as ac
ac.linked_scatter_passing().save("passing.html")   # or just the chart in a notebook
```

To try it before it's released, install from **TestPyPI** (deps come from real
PyPI):

```bash
pip install --index-url https://test.pypi.org/simple/ \
            --extra-index-url https://pypi.org/simple/ msds-comms-plotter
```

### Install from source (for development)

Work inside a **virtual environment (venv)** — recommended, and on many systems
required: a modern Python (including Homebrew's on macOS) is "externally
managed" and refuses a plain `pip install` with
`error: externally-managed-environment` (PEP 668). A venv sidesteps that by
giving the project its own isolated Python and `pip`.

### 1. Get the code

```bash
git clone https://github.com/tjsasser/msds-comms-plotter.git
cd msds-comms-plotter
```

### 2. Create the venv

Run this once, from the repo root. It makes a `.venv/` folder holding a
private copy of Python (`.venv/` is already covered by `.gitignore`).

```bash
python3 -m venv .venv
```

### 3. Activate it

You must activate the venv in **each new terminal session** before installing
or running anything. Pick the line for your shell:

```bash
# macOS / Linux (bash, zsh)
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (Command Prompt)
.venv\Scripts\activate.bat
```

Once active, your prompt is prefixed with `(.venv)`. Confirm pip now points
inside the venv (not the system Python):

```bash
which pip     # macOS / Linux  -> .../msds-comms-plotter/.venv/bin/pip
where pip     # Windows        -> ...\msds-comms-plotter\.venv\Scripts\pip.exe
```

### 4. Install the package

With the venv active, upgrade pip and install this project in editable mode
(`-e`, so your source edits take effect without reinstalling). Because you're
inside the venv, **no** `--break-system-packages` or `--user` flag is needed:

```bash
python -m pip install --upgrade pip
python -m pip install -e .
```

This pulls in every dependency automatically (see the table below).

### 5. Verify

```bash
python -c "from msds_comms_plotter import chartkit; print('chartkit OK', len(chartkit.PALETTE), 'colors')"
```

Expected output: `chartkit OK 8 colors`.

### 6. When you're done

Leave the venv with:

```bash
deactivate
```

Next time you work on the project, just re-activate (step 3) — you don't need
to recreate the venv or reinstall.

> **Note — do not use `--break-system-packages`.** That flag (or a global
> `pip install` outside a venv) writes into the system/Homebrew Python and can
> corrupt it. The venv above is the safe, standard fix for the
> `externally-managed-environment` error.

### Requirements

Installing the package pulls these in automatically (declared in
`pyproject.toml`):

| Dependency | Used by |
| --- | --- |
| `pandas` | core data helpers |
| `pyarrow` | Parquet I/O |
| `requests` | data fetching |
| `matplotlib` | `chartkit` matplotlib theming |
| `altair` | `chartkit` Altair theming (Altair 5.x; both the ≥5.5 and legacy theme APIs are supported) |

`chartkit` imports matplotlib and Altair **lazily**, inside the functions that
need them — so importing `chartkit` never fails just because one renderer is
missing. Use the matplotlib half without Altair installed, or vice versa.

**Optional — static PNG export.** Altair charts save as interactive `.html` out
of the box. To also write `.png` files, install the extra:

```bash
python -m pip install -e ".[png]"   # adds vl-convert-python
```

To register the JetBrains Mono font without a system-wide install, see
`register_font` in the API below.

## API

Import it from the package:

```python
from msds_comms_plotter import chartkit
```

### Design tokens (module constants)

These are the shared values every function draws from. Read them, or reuse them
directly in your own plotting code.

| Name | Value | Meaning |
| --- | --- | --- |
| `FONT` | `"JetBrains Mono"` | Primary typeface. |
| `FONT_STACK` | `["JetBrains Mono", "DejaVu Sans Mono", "Menlo", "Consolas", "monospace"]` | Fallback chain. |
| `PALETTE` | 8 hex colors | Categorical palette (blue, orange, teal, amber, pink, violet, green, red). |
| `INK` | `"#2c2c2a"` | Primary text / axis domain. |
| `MUTED` | `"#6b6a66"` | Secondary text / tick labels. |
| `GRID` | `"#e1e0d9"` | Gridlines. |
| `SURFACE` | `"#ffffff"` | Chart background. |
| `SEQUENTIAL` | `"viridis"` | Scheme for magnitude scales (heatmaps, choropleths). |
| `DIVERGING` | `"redblue"` | Scheme for polarity scales (deltas vs. a baseline). |
| `SIZE_TITLE`, `SIZE_LABEL`, `SIZE_TICK`, `SIZE_LEGEND` | `15, 12, 10, 11` | Font sizes (pt). |

### matplotlib functions

#### `apply_matplotlib_theme() -> dict`
Applies the chartkit look to matplotlib globally via `rcParams` (font, palette
cycle, figure size/DPI, spines, grid, ticks, legend). Call once, near the top of
your script or notebook. Returns the dict of rcParams it set.

#### `style_axes(ax, title=None, xlabel=None, ylabel=None, ygrid_only=True) -> Axes`
Per-axes finishing touches the global rcParams can't express: left-aligned
title, axis labels, hidden tick marks (labels kept), and horizontal-only grid
when `ygrid_only=True`. Returns the same `ax` for chaining.

#### `ensure_font(name="JetBrains Mono") -> bool`
Returns `True` if the font is available to matplotlib; otherwise emits a
`UserWarning` explaining the fallback and returns `False`. Handy as a
pre-flight check.

#### `register_font(path) -> str`
Registers a `.ttf`/`.otf` with matplotlib at runtime (no system install needed)
and returns the resolved font family name.

### Altair functions

#### `altair_theme() -> dict`
Returns the chartkit Vega-Lite config as a plain dict — useful if you want to
merge or inspect it rather than register it.

#### `enable_altair_theme(name="chartkit") -> str`
Registers **and** enables the theme, transparently handling both the Altair
≥ 5.5 decorator API and the legacy `alt.themes` registry. Returns the theme
name. Call once per session.

#### `alt_line(data, x, y, color=None, title="") -> alt.Chart`
#### `alt_bar(data, x, y, color=None, title="") -> alt.Chart`
#### `alt_scatter(data, x, y, color=None, title="") -> alt.Chart`
Thin styled chart builders. Channel arguments use Altair shorthand
(`"date:T"`, `"price:Q"`, `"symbol:N"`). They return a normal `alt.Chart`, so
you can keep chaining Altair methods (`.properties(...)`, `.interactive()`, …).

## Examples

### matplotlib

```python
import matplotlib.pyplot as plt
from msds_comms_plotter import chartkit

chartkit.ensure_font()            # warns if JetBrains Mono isn't installed
chartkit.apply_matplotlib_theme() # set the global look once

x = range(1, 13)
y = [3, 5, 4, 7, 8, 6, 9, 11, 10, 13, 12, 15]

fig, ax = plt.subplots()
ax.plot(x, y, marker="o")
chartkit.style_axes(ax, title="Monthly revenue", xlabel="Month", ylabel="USD (000s)")
fig.savefig("revenue.png")        # 200 DPI, tight bbox, white background
```

If JetBrains Mono lives in a local file rather than a system install:

```python
family = chartkit.register_font("fonts/JetBrainsMono-Regular.ttf")
chartkit.apply_matplotlib_theme()
```

### Altair

```python
import pandas as pd
from msds_comms_plotter import chartkit

chartkit.enable_altair_theme()    # register + enable once

df = pd.DataFrame({
    "date":   pd.date_range("2024-01-01", periods=6, freq="MS").tolist() * 2,
    "price":  [10, 12, 11, 14, 13, 16, 8, 9, 9, 11, 10, 12],
    "symbol": ["AAA"] * 6 + ["BBB"] * 6,
})

chart = chartkit.alt_line(df, x="date:T", y="price:Q", color="symbol:N",
                          title="Price by symbol")
chart.save("price.html")          # or chart.interactive() in a notebook
```

Both figures now share the same font, palette, and chrome.

### Running the passing chart

The package ships one worked example on real data: **Passing: volume vs
accuracy** — a linked-brush scatter of passes attempted vs pass completion %,
colored by position, with a count-by-position bar chart, a player-name search
box, and a color-scheme dropdown.

**Open it in your browser (recommended).** The example script builds the chart
and opens it:

```bash
python examples/show_wc2022_charts.py
```

It uses the data bundled inside the package (no raw data or network needed) and
writes a **self-contained** `passing_chart.html` to the folder you run it from
(the Vega libraries are embedded, so it stays interactive offline). On a
headless machine it skips the browser and just prints the file path.

**In a notebook**, call the builder to render it inline (uses the bundled data):

```python
from msds_comms_plotter import altair_charts as ac
ac.linked_scatter_passing()   # returns an alt.Chart; renders in Jupyter

# ...or pass your own player-match table:
# ac.linked_scatter_passing(stats=my_df)
```

See [`docs/wc2022_data.md`](docs/wc2022_data.md) for the dataset columns.

## Chart cookbook

The one chart this package ships is **Passing: volume vs accuracy**. Here's the
core Altair code behind it, then the one-call shortcut. First, every chart picks
up the shared look:

```python
import altair as alt
from msds_comms_plotter import chartkit
chartkit.enable_altair_theme()   # JetBrains Mono, shared palette, minimal chrome
```

### Linked brush (`selection_interval`)

Altair's signature interaction. Drag a box on the scatter (passes attempted vs
pass completion %, colored by position) and the count-by-position bars below
recount only the selected players; the rest fade to grey. One selection drives
both marks. The full builder adds a player-name search box and a color-scheme
dropdown on top.

![Passing: volume vs accuracy](https://raw.githubusercontent.com/tjsasser/msds-comms-plotter/plotter-abbreviated/reports/figures/alt_brush_passing.png)

```python
brush = alt.selection_interval()
color = alt.Color("position:N")

points = alt.Chart(players).mark_point(filled=True).encode(
    x="passes:Q", y="completion_pct:Q",
    # selected points keep their category color; the rest go grey
    color=alt.when(brush).then(color).otherwise(alt.value("lightgray")),
).add_params(brush)

bars = alt.Chart(players).mark_bar().encode(
    y="position:N", x="count():Q", color=color,
).transform_filter(brush)          # only the brushed points are counted

points & bars                      # vertical concatenation
```

### Shortcut: just call the library

You don't have to reproduce the code above — the full chart (brush, search box,
color-scheme dropdown, linked bars) is one call, using the bundled data:

```python
from msds_comms_plotter import altair_charts as ac

chart = ac.linked_scatter_passing()   # returns an alt.Chart
chart.save("passing.html")            # or `chart` in a notebook
# pass your own table with: ac.linked_scatter_passing(stats=my_df)
```

Any chart is an `alt.Chart` — save it as interactive HTML or a static PNG:

```python
chart.save("chart.html")            # interactive; add inline=True for offline
chart.save("chart.png", ppi=200)    # needs vl-convert-python (the [png] extra)
```

## Project layout

```
msds-comms-plotter/
├── src/msds_comms_plotter/
│   ├── __init__.py       # exposes chartkit
│   ├── chartkit.py       # matplotlib + Altair theming  ← documented above
│   ├── altair_charts.py  # the Passing: volume vs accuracy chart (run as a module)
│   └── worldcup.py       # dataset loading/paths
├── examples/             # runnable example scripts (write to the current folder)
├── data/                 # example datasets
├── docs/                 # dataset notes (see docs/wc2022_data.md)
├── reports/figures/      # the passing chart, rendered (html + png)
└── pyproject.toml
```

## Contributing

This is a course project, but if you're extending it:

1. Keep the shared design tokens (`PALETTE`, `INK`, `GRID`, …) as the single
   source of truth — style through them rather than hard-coding colors.
2. Keep renderer imports lazy (import matplotlib/altair inside functions) so the
   two halves stay independent.
3. Run a quick import check before committing:
   `python -c "from msds_comms_plotter import chartkit"`.

## License

See [LICENSE](LICENSE).
