"""Automated weekly sales reporting. Run from any working directory."""
from pathlib import Path
from html import escape
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data"
ARCHIVE_DIR = BASE_DIR / "Archive"
OUTPUT_DIR = BASE_DIR / "Output"
REQUIRED_COLUMNS = ["order_id", "date", "product", "category", "region", "salesperson", "units", "unit_price"]


def load_and_validate(path, label):
    """Read a sales CSV and reject incomplete or invalid records."""
    data = pd.read_csv(path, dtype={"order_id": "string"})
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError(f"{label}: missing required columns: {missing}")
    if data.empty:
        raise ValueError(f"{label}: the CSV is empty")
    if data[REQUIRED_COLUMNS].isna().any().any():
        raise ValueError(f"{label}: missing values detected")
    if (data["order_id"].str.strip() == "").any():
        raise ValueError(f"{label}: blank order ID")
    if data["order_id"].duplicated().any():
        raise ValueError(f"{label}: duplicate order IDs detected")
    for column in ["product", "category", "region", "salesperson"]:
        if (data[column].astype(str).str.strip() == "").any():
            raise ValueError(f"{label}: blank {column} value")
    for column in ["units", "unit_price"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
        if data[column].isna().any() or (~data[column].map(lambda x: bool(pd.notna(x) and x != float('inf') and x != float('-inf')))).any():
            raise ValueError(f"{label}: invalid numeric values in {column}")
        if (data[column] <= 0).any():
            raise ValueError(f"{label}: {column} must be greater than zero")
    if (data["units"] % 1 != 0).any():
        raise ValueError(f"{label}: units must be whole numbers")
    data["date"] = pd.to_datetime(data["date"], format="%Y-%m-%d", errors="coerce")
    if data["date"].isna().any():
        raise ValueError(f"{label}: invalid dates (use YYYY-MM-DD)")
    data["revenue"] = data["units"] * data["unit_price"]
    return data


def validate_week(data, start, label):
    """All orders must fall within the expected Monday-to-Sunday week."""
    if start.weekday() != 0:
        raise ValueError(f"{label}: reporting week must start on Monday")
    end = start + pd.Timedelta(days=6)
    if not data["date"].between(start, end).all():
        raise ValueError(f"{label}: orders outside {start:%Y-%m-%d} to {end:%Y-%m-%d}")
    return end


def find_previous_week(start):
    """Find exactly one archived CSV whose records belong to the prior week."""
    expected = start - pd.Timedelta(days=7)
    matches = []
    files = sorted(ARCHIVE_DIR.glob("*.csv"))
    print(f"Historical files found: {len(files)}")
    for path in files:
        candidate = load_and_validate(path, path.name)
        # Archive files must each describe a single calendar week.
        candidate_start = candidate["date"].min().normalize()
        if candidate_start.weekday() != 0:
            raise ValueError(f"{path.name}: earliest date must be Monday")
        validate_week(candidate, candidate_start, path.name)
        if candidate_start == expected:
            matches.append((path, candidate))
    if not matches:
        raise FileNotFoundError(f"No archived CSV matches the previous week beginning {expected:%Y-%m-%d}")
    if len(matches) > 1:
        raise ValueError("More than one archived CSV matches the previous reporting week")
    return matches[0]


def money(value):
    return f"€{value:,.2f}"


def make_report(current, previous, current_file, previous_file, start, end):
    total = current["revenue"].sum()
    previous_total = previous["revenue"].sum()
    if previous_total <= 0:
        raise ValueError("Previous week's revenue must be positive")
    change = (total - previous_total) / previous_total * 100
    orders = current["order_id"].nunique()
    units = int(current["units"].sum())
    daily = current.groupby("date")["revenue"].sum().sort_index()
    region = current.groupby("region")["revenue"].sum().sort_values(ascending=False)
    product = current.groupby("product")["revenue"].sum().sort_values(ascending=False)
    category = current.groupby("category")["revenue"].sum().sort_values(ascending=False)
    salesperson = current.groupby("salesperson")["revenue"].sum().sort_values(ascending=False)
    top_day = daily.idxmax()
    top_region, top_product, top_category, top_salesperson = (s.index[0] for s in [region, product, category, salesperson])
    region_share = region.iloc[0] / total * 100
    product_share = product.iloc[0] / total * 100
    category_share = category.iloc[0] / total * 100
    if change > 0:
        trend = f"Revenue increased by {change:.2f}% compared with the previous week."
    elif change < 0:
        trend = f"Revenue decreased by {abs(change):.2f}% compared with the previous week."
    else:
        trend = "Revenue remained unchanged compared with the previous week."
    previous_orders = previous["order_id"].nunique()
    order_change = (orders - previous_orders) / previous_orders * 100
    previous_region = previous.groupby("region")["revenue"].sum()
    region_change = (region.iloc[0] - previous_region.get(top_region, 0))
    insights = [
        trend + f" Order volume changed {order_change:+.1f}% ({previous_orders} to {orders}); review volume and average order value together.",
        (
            f"{top_region} contributed {region_share:.1f}% of revenue ({money(region.iloc[0])}); "
            f"its revenue changed {money(abs(region_change))} {'up' if region_change >= 0 else 'down'} from last week. "
            "Review the region's product mix and sales activity."
        ),
        (
            f"{top_product} generated {product_share:.1f}% of weekly revenue. "
            + ("Concentration risk: monitor stock availability and diversify sales opportunities." if product_share >= 35
               else "Monitor whether demand is concentrated in a small number of products.")
        ),
        (
            f"{top_category} represents {category_share:.1f}% of revenue. "
            "Compare category trends over several weeks before changing inventory or targets."
        ),
    ]
    lines = [
        "WEEKLY SALES PERFORMANCE REPORT",
        f"Source File: {current_file.name}",
        f"Comparison File: {previous_file.name}",
        f"Reporting Period: {start:%d %b %Y} - {end:%d %b %Y}",
        "=" * 31, "",
        f"Total Weekly Revenue: {money(total)}",
        f"Total Orders: {orders}",
        f"Previous Week Orders: {previous_orders}",
        f"Week-over-Week Order Change: {order_change:+.1f}%",
        f"Total Units Sold: {units}",
        f"Average Order Value: {money(total / orders)}",
        f"Previous Week Revenue: {money(previous_total)}",
        f"Week-over-Week Revenue Change: {change:+.2f}%",
        f"Top Sales Day: {top_day:%d %b %Y} ({money(daily.iloc[daily.argmax()])})",
        f"Top Performing Region: {top_region} ({money(region.iloc[0])}, {region_share:.1f}% of total revenue)",
        f"Top Salesperson: {top_salesperson} ({money(salesperson.iloc[0])})",
        f"Top Product: {top_product} ({money(product.iloc[0])}, {product_share:.1f}% of total revenue)",
        f"Top Category: {top_category} ({money(category.iloc[0])}, {category_share:.1f}% of total revenue)",
        "", "BUSINESS INSIGHTS", "=" * 17,
        *[f"- {insight}" for insight in insights], "",
    ]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"weekly_sales_report_{start:%Y-%m-%d}_to_{end:%Y-%m-%d}"
    text_path = OUTPUT_DIR / f"{stem}.txt"
    text_path.write_text("\n".join(lines), encoding="utf-8")

    def bars(series):
        maximum = series.max()
        return "\n".join(
            f'<div class="barrow"><span>{escape(str(name))}</span><div class="track"><div class="fill" style="width:{value / maximum * 100:.1f}%"></div></div><strong>{money(value)}</strong></div>'
            for name, value in series.items()
        )

    html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Weekly Sales Performance</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;background:#f4f6fa;color:#18263d;margin:0}}main{{max-width:980px;margin:36px auto;padding:0 22px}}header{{background:#142b48;color:white;padding:30px;border-radius:15px}}h1{{margin:0 0 10px}}header p{{margin:6px 0;color:#d8e6f7}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px;margin:22px 0}}.card,section{{background:white;padding:22px;border-radius:13px;box-shadow:0 3px 14px #1628440d}}.card small{{display:block;color:#63738a}}.card strong{{display:block;font-size:26px;margin-top:7px}}section{{margin:18px 0}}.barrow{{display:grid;grid-template-columns:120px 1fr 105px;align-items:center;gap:12px;margin:13px 0;font-size:14px}}.track{{background:#e9edf3;border-radius:12px;height:15px;overflow:hidden}}.fill{{height:100%;background:#3077ad;border-radius:12px}}.barrow strong{{text-align:right}}li{{margin:11px 0}}footer{{font-size:12px;color:#687b90;margin:24px 0}}@media(max-width:550px){{.barrow{{grid-template-columns:90px 1fr 85px;font-size:12px}}}}
</style></head><body><main><header><h1>Weekly Sales Performance</h1><p>{start:%d %b %Y} – {end:%d %b %Y}</p><p>Source: {escape(current_file.name)} | Comparison: {escape(previous_file.name)}</p></header>
<div class="cards"><div class="card"><small>Weekly revenue</small><strong>{money(total)}</strong></div><div class="card"><small>Previous week</small><strong>{money(previous_total)}</strong></div><div class="card"><small>Week-over-week change</small><strong>{change:+.2f}%</strong></div><div class="card"><small>Orders / units</small><strong>{orders} / {units}</strong></div><div class="card"><small>Order change</small><strong>{order_change:+.1f}%</strong></div><div class="card"><small>Average order value</small><strong>{money(total / orders)}</strong></div></div>
<section><h2>Business insights</h2><ul>{''.join('<li>'+escape(x)+'</li>' for x in insights)}</ul></section>
<section><h2>Revenue by region</h2>{bars(region)}</section><section><h2>Revenue by category</h2>{bars(category)}</section><section><h2>Revenue by product</h2>{bars(product)}</section><section><h2>Daily revenue</h2>{bars(daily.rename(index=lambda d:d.strftime('%a %d %b')))}</section>
<footer>Synthetic demonstration transactions, not real company sales. Suggested actions are rule-based prompts for investigation, not causal findings or AI-generated advice.</footer></main></body></html>"""
    html_path = OUTPUT_DIR / f"{stem}.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"Previous Week Revenue: {money(previous_total)}")
    print(f"Total Weekly Revenue: {money(total)}")
    print(f"Week-over-Week Revenue Change: {change:+.2f}%")
    print(f"Report successfully generated: {text_path.relative_to(BASE_DIR)}")
    print(f"Dashboard successfully generated: {html_path.relative_to(BASE_DIR)}")
    return text_path, html_path


def main():
    current_files = sorted(DATA_DIR.glob("*.csv"))
    if len(current_files) != 1:
        raise ValueError(f"Expected exactly one current CSV in Data; found {len(current_files)}")
    current_file = current_files[0]
    current = load_and_validate(current_file, "Current sales")
    start = current["date"].min().normalize()
    end = current["date"].max().normalize()
    if start.weekday() != 0 or (end - start).days != 6:
        raise ValueError("Current reporting period must span Monday through Sunday")
    validate_week(current, start, "Current sales")
    print(f"Processing file: {current_file.name}")
    print(f"Looking for historical week starting: {start - pd.Timedelta(days=7):%Y-%m-%d}")
    previous_file, previous = find_previous_week(start)
    print(f"Previous week loaded: {previous_file.name}")
    make_report(current, previous, current_file, previous_file, start, end)


if __name__ == "__main__":
    main()
