# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Visualizations

- Use **matplotlib** only for visualizations. Do not use other plotting
  libraries (e.g. seaborn, plotly, bokeh, altair) for generating plots.

## Data

- Use only **pandas**, not polars.
- Raw data is stored in the `data/` directory structure as appropriate.
- Never commit a `.csv` file.

## Tests

- Run tests with `pytest -q`.

## Deletions

- Do not delete anything unless asked. Verify before you do any deletion.

## Workflow

- Take all actions necessary to merge changes into main.
