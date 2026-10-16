# Automated Business Reporting Pipeline

A portfolio project demonstrating how Python can turn raw weekly sales CSVs into repeatable management reporting. The company and all transactions are **fictional**.

## Business problem

A sales team receives a CSV every week. Manually checking the data, comparing last week's performance, and building a management summary takes time and risks inconsistent reporting. This pipeline performs those steps automatically when run.

## What it delivers

- Validates required fields, missing values, duplicate IDs, numeric quantities and prices, and reporting-week dates.
- Identifies the immediately preceding Monday–Sunday week among multiple archived files, regardless of filenames.
- Calculates revenue, order count, units, average order value, and week-over-week changes.
- Compares performance across regions, categories, products and days.
- Produces a standalone **HTML dashboard** and a plain-text management report.
- Generates **rule-based business observations and investigation prompts**, not AI-generated recommendations.

## Example data

The active dataset is **Week 48 (23–29 November 2026)** in `Data/sales_week_48.csv`; the pipeline compares it with **Week 47** from `Archive/`. Weeks 41–48 are larger, reproducibly generated synthetic datasets (roughly 145–190 transactions/week). Original eight-order Weeks 39 and 40 remain preserved in `Archive/`; Weeks 37 and 38 are earlier synthetic examples. Do not present the generated figures as real business results.

## Run in VS Code on Windows

Open the **inner project folder** (the one containing `Data`, `Archive`, `Src`, `Output` and `tests`) using **File → Open Folder**. Open **Terminal → New Terminal** and run:

```powershell
python -m pip install -r requirements.txt
python Src/main.py
```

Then open the new `.html` file in `Output` with your web browser. Both report formats are generated locally; no network connection or external dashboard service is needed.

## Run tests

```powershell
python -m unittest discover -s tests -v
```

## Input format and weekly workflow

CSV headers: `order_id,date,product,category,region,salesperson,units,unit_price`.

- Keep **one** current-week CSV in `Data/`.
- Keep earlier weekly CSVs in `Archive/`.
- When a new week arrives, move the old current CSV into `Archive/`, add the new CSV to `Data/`, then run the script.
- Dates must use `YYYY-MM-DD`; the demo expects sales on Monday and Sunday so it can infer the full current reporting week.
- Revenue is derived as `units × unit_price`, not stored in the input.

## Technical decisions and limitations

- The project uses **pandas**, the Python standard library and standalone HTML/CSS. No AI or predictive model is involved.
- All archived CSVs are validated during the previous-week search. A malformed unrelated archived file can stop the run; this is a deliberate strictness trade-off.
- The dashboard uses static HTML bars, not interactive charting libraries.
- The reporting week is inferred from the earliest and latest order dates. A week with no transactions on Monday or Sunday needs an explicit reporting-date setting in a future version.
- The code does not schedule itself, send email, or automatically archive the current file.
- Investigation prompts are hypotheses, not proof of causes; managers should check underlying trends before taking action.

## Portfolio value

Demonstrates data quality controls, file automation, historical data matching, business KPIs, repeatable reporting and clear communication of findings. Built to connect business-analysis experience with practical Python automation.
