"""One-time seed script: uploads sample data to a Unity Catalog table so the
PySpark coding agent has something to query.

Databricks Free Edition serverless compute has no access to the dev
machine's local filesystem, so `spark.read.csv("./data/...")` no longer
works — this script runs the write from a Databricks Connect session
instead, which *does* have access to Unity Catalog volumes/tables.

Usage:
    export DATABRICKS_HOST=https://<workspace>.cloud.databricks.com
    export DATABRICKS_TOKEN=<personal access token>
    export DATABRICKS_CATALOG=<catalog, e.g. workspace or main>
    export DATABRICKS_SCHEMA=default
    python scripts/seed_databricks.py [--rows 5000] [--table sample_sales]

This is a one-time/occasional operation, not something the agent does per
request — sample data lives in the catalog once seeded.
"""
from __future__ import annotations

import argparse
import os
import random
from datetime import date, timedelta

REGIONS = ["North", "South", "East", "West", "Central"]
PRODUCTS = ["Widget", "Gadget", "Doohickey", "Gizmo", "Thingamajig"]


def _generate_rows(n: int) -> list[dict]:
    random.seed(42)
    start = date.today() - timedelta(days=365)
    rows = []
    for i in range(n):
        order_date = start + timedelta(days=random.randint(0, 365))
        rows.append({
            "order_id": i + 1,
            "order_date": order_date.isoformat(),
            "region": random.choice(REGIONS),
            "product": random.choice(PRODUCTS),
            "quantity": random.randint(1, 20),
            "unit_price": round(random.uniform(5.0, 250.0), 2),
        })
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rows", type=int, default=5_000)
    parser.add_argument("--table", default=os.environ.get("SEED_TABLE", "sample_sales"))
    args = parser.parse_args()

    catalog = os.environ.get("DATABRICKS_CATALOG", "")
    schema = os.environ.get("DATABRICKS_SCHEMA", "default")
    if not os.environ.get("DATABRICKS_HOST") or not os.environ.get("DATABRICKS_TOKEN"):
        raise SystemExit(
            "DATABRICKS_HOST and DATABRICKS_TOKEN must be set in the environment "
            "(see the docstring at the top of this script)."
        )

    from databricks.connect import DatabricksSession

    spark = (
        DatabricksSession.builder
        .host(os.environ["DATABRICKS_HOST"])
        .token(os.environ["DATABRICKS_TOKEN"])
        .serverless(True)
        .getOrCreate()
    )

    if catalog:
        spark.sql(f"USE CATALOG `{catalog}`")
    spark.sql(f"CREATE SCHEMA IF NOT EXISTS `{schema}`")
    spark.sql(f"USE SCHEMA `{schema}`")

    print(f"Generating {args.rows:,} sample rows …")
    rows = _generate_rows(args.rows)
    df = spark.createDataFrame(rows)

    full_name = f"`{catalog}`.`{schema}`.`{args.table}`" if catalog else f"`{schema}`.`{args.table}`"
    df.write.mode("overwrite").saveAsTable(full_name)
    print(f"Wrote {args.rows:,} rows → table {full_name}")

    print("Tables now visible in the catalog:")
    for row in spark.catalog.listTables():
        print(f"  - {row.tableName}")


if __name__ == "__main__":
    main()
