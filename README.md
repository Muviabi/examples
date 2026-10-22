<p align="center">
  <a href="https://muviabi.com/en">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="assets/muvia-logo-dark.svg">
      <img alt="Muvia" src="assets/muvia-logo.svg" width="280">
    </picture>
  </a>
</p>

<p align="center">
  <b>From data to decisions. On a single platform.</b><br>
  BI, AI and machine learning for company data, and industrial IoT for the field.
</p>

<p align="center">
  <a href="https://github.com/Muviabi/examples/actions/workflows/test.yml"><img alt="Tests" src="https://github.com/Muviabi/examples/actions/workflows/test.yml/badge.svg"></a>
  <a href="LICENSE"><img alt="MIT licence" src="https://img.shields.io/badge/licence-MIT-0EA5AE"></a>
  <img alt="Python 3.14" src="https://img.shields.io/badge/python-3.14-0EA5AE">
  <img alt="13 functions" src="https://img.shields.io/badge/functions-13-0EA5AE">
</p>

<p align="center">
  <a href="https://muviabi.com/en">Website</a> ·
  <a href="https://app-demo.muviabi.com/try">Try it yourself</a> ·
  <a href="https://developers.muviabi.com">Developer API</a> ·
  <a href="README.it.md">Leggi in italiano</a>
</p>

---

## Muvia, in a minute

Muvia brings your ERP, CRM, databases, files and machines into one place, and answers where you
already work: in a dashboard, in Monday's report, in an alarm, or in the AI assistant you use every
day. Every answer shows the query that produced it.

- **Connect.** Upload a file or connect a database, an application or a machine. Muvia copies only
  the new rows and your systems stay as they are.
- **Model.** Every number lives in a dataset with stable fields, and the lineage shows where it
  comes from, source to report.
- **Analyse.** In SQL, in notebooks, in Python, with predictors, or by asking Athena, Muvia's
  assistant.
- **Act.** Dashboards, PDF reports on a schedule, alarms with an owner, a REST API and signed
  webhooks.

## Where these functions fit

When SQL isn't enough, you write a Python function. It takes a table and gives back a table, and a
flow runs it on a schedule on the project's data. With Muvia Industrial the same function also runs
on the edge node next to the machine, before the data leaves the plant.

This repository holds thirteen ready ones, from receivables aging to OEE, each with its contract and
a test that runs on your machine. Import them into a project, use them as they are in a flow, or
start from one to write your own.

| Theme | Function | What it does |
| --- | --- | --- |
| Business | [`receivables_aging`](functions/business/receivables_aging.py) | Each customer's open receivables by days past due: not due, 1-30, 31-60, 61-90, over 90 |
| Business | [`rfm_segments`](functions/business/rfm_segments.py) | Recency, frequency and monetary value of each customer, scored 1-5, and their segment |
| Business | [`weighted_pipeline`](functions/business/weighted_pipeline.py) | Open deals by closing month and stage, weighted by their probability |
| Business | [`demand_forecast`](functions/business/demand_forecast.py) | Each product's quantity in the coming weeks, with an approximate 95% band |
| Industrial | [`oee`](functions/industrial/oee.py) | Availability, performance, quality and OEE of each shift, day or order |
| Industrial | [`signal_anomalies`](functions/industrial/signal_anomalies.py) | Each reading's z-score against the readings before it, and whether it is an anomaly |
| Industrial | [`stop_events`](functions/industrial/stop_events.py) | A machine's stops, one row each, from its running signal |
| Industrial | [`energy_per_piece`](functions/industrial/energy_per_piece.py) | Watt-hours per piece and their drift from the usual; energy used with nothing made |
| Data quality | [`column_profile`](functions/data_quality/column_profile.py) | Missing values, distinct values and range of every column of any table |
| Data quality | [`duplicate_rows`](functions/data_quality/duplicate_rows.py) | The rows whose key appears more than once, grouped |
| Data quality | [`range_checks`](functions/data_quality/range_checks.py) | The rows whose value is missing or outside the range you set |
| Markets | [`price_indicators`](functions/markets/price_indicators.py) | Change, moving averages, trend, volatility and RSI of each price series |
| Markets | [`price_vs_average`](functions/markets/price_vs_average.py) | Each seller's price against the day's average for the same product, and its rank |

## Use one in Muvia

Each function is two files with the same name: `<key>.py`, its code, and `<key>.json`, its name,
description and contract.

1. In your project, open **Lab → Functions** and choose **Import**.
2. Pick both files of each function you want (several functions at once are fine).
3. Add the function to a flow and connect its input to a source whose columns match the contract
   (the `.json` lists them), or rename the columns in the source's query.

A function whose key the project already uses is offered under another key. Once imported, it is
yours: change the code and the contract in the editor and try it on your own rows.

## How a function is written

```python
def transform(inputs, params, ctx):
    rows = inputs["rows"].copy()          # each table input is a pandas DataFrame
    rows["total"] = rows["price"] * rows["quantity"]
    return {"rows": rows}                 # a dict with exactly the contract's outputs
```

- `inputs` holds each input by name: a table as a DataFrame, any other input as its value.
- `params` holds the node's parameters, as the contract's `form_config` declares them. Read them
  with `params.get("name", default)`.
- `ctx.window.start` and `ctx.window.end` are the period the run covers (`start` is `None` on a
  flow's first run, `end` is excluded); `ctx.logger` writes to the run's log; `ctx.preview` is true
  in a trial.
- The function returns a dict whose keys are exactly the contract's outputs. Write each `return`
  as a dict with literal keys, so the editor can read the outputs off the code.
- Functions run without network access. The libraries available are Python's standard library,
  NumPy, pandas, PyArrow, SciPy, scikit-learn, statsmodels, LightGBM, joblib, Matplotlib, openpyxl,
  PyWavelets and ONNX Runtime.

The contract (`contract` in the `.json`) says what the function takes and gives: each port's
columns and their kind (`time`, `string`, `integer`, `float`, `boolean`, `any`), whether an output
is a new table (`"shape": "fixed"`) or its input with columns added (`"shape": "derived"`), its
parameters, its time limit and where it may run (`"targets": ["cloud", "edge"]`). Muvia checks the
rows against it before and after every call.

## Run the tests

You need [uv](https://docs.astral.sh/uv/). It installs Python 3.14 and the same library versions
Muvia's functions run with:

```sh
uv sync
uv run pytest
```

`muvia_local.run` calls a function as Muvia does and checks both sides against its contract:

```python
from muvia_local import run

outputs = run("functions/industrial/oee", {"production": my_dataframe})
```

It is a test bench, not Muvia: it does not limit time or memory, nor cut the network, and the
`ctx` handles that need a capability (notifications, assets, documents, the AI model) are not on
it.

## Contribute

Ideas and fixes are welcome. A new example is a pair in `functions/<theme>/` and a test in
`tests/test_<theme>.py` with rows small enough to check by hand; `uv run pytest` must pass.

## Try Muvia

Muvia itself is not open source; these examples are. To see them at work on your own data,
[try it yourself](https://app-demo.muviabi.com/try) or [book a demo](https://muviabi.com/en/contact).

## License

[MIT](LICENSE).
