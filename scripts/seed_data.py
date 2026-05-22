"""Generate synthetic Parquet test data for PySpark-AI-Agent.

Usage:
    python scripts/seed_data.py [--rows 50000] [--out ./data]

Produces:  data/records.parquet
Schema:    entity_id, entity_name, status, date, segment, category
"""
from __future__ import annotations

import argparse
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

SEGMENTS   = ["Engineering", "Sales", "Marketing", "Operations", "Finance"]
CATEGORIES = ["Full-Time", "Part-Time", "Contractor"]


def _random_date(start: date, end: date) -> str:
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).isoformat()


def generate(n_entities: int, n_rows: int, start: date, end: date) -> pd.DataFrame:
    random.seed(42)
    entity_ids   = [f"E{i:05d}" for i in range(1, n_entities + 1)]
    entity_names = [f"Entity {i}" for i in range(1, n_entities + 1)]
    segments     = {eid: random.choice(SEGMENTS)   for eid in entity_ids}
    categories   = {eid: random.choice(CATEGORIES) for eid in entity_ids}

    rows = []
    for _ in range(n_rows):
        eid = random.choice(entity_ids)
        rows.append({
            "entity_id":   eid,
            "entity_name": entity_names[entity_ids.index(eid)],
            "status":      "active" if random.random() < 0.78 else "inactive",
            "date":        _random_date(start, end),
            "segment":     segments[eid],
            "category":    categories[eid],
        })

    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=50_000)
    parser.add_argument("--out",  default="./data")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    end       = date.today()
    start     = end - timedelta(days=365)
    n_entities = max(100, args.rows // 50)

    print(f"Generating {args.rows:,} rows for {n_entities} entities …")
    df       = generate(n_entities, args.rows, start, end)
    out_path = out_dir / "records.parquet"
    df.to_parquet(out_path, index=False)
    print(f"Saved {len(df):,} rows → {out_path}")
    print("Schema:", list(df.columns))
    print("Status counts:", df["status"].value_counts().to_dict())


if __name__ == "__main__":
    main()
