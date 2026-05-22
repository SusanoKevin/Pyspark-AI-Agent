from __future__ import annotations

import logging
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import sqlglot
from pyspark.sql import SparkSession
from sqlglot import exp

logger = logging.getLogger(__name__)

_FORBIDDEN = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
    exp.Alter, exp.TruncateTable, exp.Merge, exp.Command,
)


def _assert_select_only(sql: str) -> None:
    try:
        trees = [t for t in sqlglot.parse(sql, dialect="spark") if t is not None]
    except Exception as e:
        raise ValueError(f"Could not parse SQL: {e}") from e
    if not trees:
        raise ValueError("Empty SQL statement.")
    if len(trees) > 1:
        raise PermissionError("Read-only store: only a single SELECT statement is permitted.")
    if not isinstance(trees[0], exp.Select):
        raise PermissionError("Read-only store: only SELECT statements are permitted.")
    for node in trees[0].walk():
        if isinstance(node, _FORBIDDEN):
            raise PermissionError(f"Read-only store: {type(node).__name__} statements are not permitted.")


class _TTLCache:
    def __init__(self, ttl: int = 300, maxsize: int = 0) -> None:
        self._store: dict = {}
        self._ttl = ttl
        self._maxsize = maxsize

    def get(self, key: str):
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires = entry
        if time.monotonic() > expires:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value) -> None:
        if self._maxsize > 0 and len(self._store) >= self._maxsize and key not in self._store:
            oldest = min(self._store, key=lambda k: self._store[k][1])
            del self._store[oldest]
        self._store[key] = (value, time.monotonic() + self._ttl)


class SparkDataStore:
    def __init__(self) -> None:
        self._table           = os.environ.get("PRIMARY_TABLE",      "")
        self._metric_col      = os.environ.get("METRIC_COLUMN",      "status")
        self._positive_val    = os.environ.get("POSITIVE_VALUE",     "active")
        self._date_col        = os.environ.get("DATE_COLUMN",        "date")
        self._entity_col      = os.environ.get("ENTITY_COLUMN",      "entity_id")
        self._entity_name_col = os.environ.get("ENTITY_NAME_COLUMN", "entity_name")
        self._group_cols: list[str] = [
            c.strip()
            for c in os.environ.get("GROUP_COLUMNS", "").split(",")
            if c.strip()
        ]

        master   = os.environ.get("SPARK_MASTER",   "local[*]")
        app_name = os.environ.get("SPARK_APP_NAME", "pyspark-ai-agent")
        self._spark = (
            SparkSession.builder
            .master(master)
            .appName(app_name)
            .config("spark.sql.adaptive.enabled", "true")
            .config("spark.sql.shuffle.partitions", "8")
            .getOrCreate()
        )
        self._spark.sparkContext.setLogLevel("WARN")

        data_path = os.environ.get("DATA_PATH", "./data")
        self._load_data(data_path)
        self._group_expr = self._build_group_expr()
        self._cache = _TTLCache(ttl=300)

    def _load_data(self, data_path: str) -> None:
        path = Path(data_path)
        if not path.exists():
            logger.warning("DATA_PATH %s does not exist — no tables registered", data_path)
            return

        for parquet_path in sorted(path.rglob("*.parquet")):
            name = parquet_path.stem
            self._spark.read.parquet(str(parquet_path)).createOrReplaceTempView(name)
            logger.info("Registered Parquet view: %s", name)

        for csv_path in sorted(path.rglob("*.csv")):
            name = csv_path.stem
            (
                self._spark.read
                .option("header", "true")
                .option("inferSchema", "true")
                .csv(str(csv_path))
                .createOrReplaceTempView(name)
            )
            logger.info("Registered CSV view: %s", name)

    def _build_group_expr(self) -> dict[str, tuple[str, str]]:
        dc      = self._date_col
        dc_cast = f"CAST({dc} AS DATE)"
        dow     = f"(dayofweek({dc_cast}) + 5) % 7"
        expr: dict[str, tuple[str, str]] = {}
        for col in self._group_cols:
            expr[col] = (col, col)
        expr[self._entity_col] = (f"CAST({self._entity_col} AS STRING)", self._entity_col)
        expr["week"] = (
            f"CONCAT("
            f"date_format(date_sub({dc_cast}, {dow}), 'yyyy-MM-dd'),"
            f"'/',"
            f"date_format(date_add(date_sub({dc_cast}, {dow}), 6), 'yyyy-MM-dd')"
            f")",
            "week",
        )
        expr["month"]       = (f"date_format({dc_cast}, 'yyyy-MM')", "month")
        expr["day_of_week"] = (f"date_format({dc_cast}, 'EEEE')",   "day_of_week")
        return expr

    @property
    def primary_db(self) -> str:
        return ""

    def _require_table(self) -> str:
        if not self._table:
            raise RuntimeError("PRIMARY_TABLE is not configured. Set PRIMARY_TABLE in your .env file.")
        return self._table

    def _query(self, sql: str, database: str | None = None) -> pd.DataFrame:
        _assert_select_only(sql)
        return self._spark.sql(sql).toPandas()

    def get_table_names(self) -> list[str]:
        return [row.tableName for row in self._spark.catalog.listTables()]

    def get_schema_for_table(self, table_name: str) -> list[dict]:
        return [
            {"name": c.name, "dataType": c.dataType}
            for c in self._spark.catalog.listColumns(table_name)
        ]

    def ping(self) -> bool:
        try:
            self._spark.sql("SELECT 1").collect()
            return True
        except Exception:
            return False

    def close(self) -> None:
        self._spark.stop()

    def summary(self) -> dict:
        self._require_table()
        cached = self._cache.get("summary:all")
        if cached is not None:
            return cached

        t, mc, pv = self._table, self._metric_col, self._positive_val
        dc, ec    = self._date_col, self._entity_col
        dc_cast   = f"CAST({dc} AS DATE)"

        df = self._query(f"""
        SELECT
            COUNT(*)                                                                    AS total_records,
            COUNT(DISTINCT {ec})                                                        AS entity_count,
            date_format(MIN({dc_cast}), 'yyyy-MM-dd')                                  AS date_from,
            date_format(MAX({dc_cast}), 'yyyy-MM-dd')                                  AS date_to,
            ROUND(100.0 * SUM(CASE WHEN {mc} = '{pv}' THEN 1 ELSE 0 END)
                / NULLIF(COUNT(*), 0), 1)                                               AS metric_rate,
            SUM(CASE WHEN {mc} <> '{pv}' THEN 1 ELSE 0 END)                           AS below_threshold_count
        FROM {t}
        """)

        if df.empty or int(df["total_records"].iloc[0]) == 0:
            return {"status": "no_data"}

        first_dim = self._group_cols[0] if self._group_cols else None
        dims_df   = self._query(
            f"SELECT DISTINCT {first_dim} FROM {t} WHERE {first_dim} IS NOT NULL ORDER BY {first_dim}"
        ) if first_dim else pd.DataFrame()

        row    = df.iloc[0]
        result = {
            "total_records":         int(row["total_records"]),
            "entity_count":          int(row["entity_count"]),
            "date_range":            {"from": str(row["date_from"]), "to": str(row["date_to"])},
            "metric_rate":           float(row["metric_rate"]),
            "below_threshold_count": int(row["below_threshold_count"]),
            "dimensions":            dims_df[first_dim].tolist() if first_dim and not dims_df.empty else [],
        }
        self._cache.set("summary:all", result)
        return result

    def compute_stats(
        self,
        group_by:  str = "",
        period:    str = "all",
        segments:  list[str] | None = None,
        date_from: str | None = None,
        date_to:   str | None = None,
    ) -> pd.DataFrame:
        self._require_table()
        group_by  = group_by or (self._group_cols[0] if self._group_cols else self._entity_col)
        cache_key = f"stats:{group_by}:{period}:{','.join(sorted(segments or []))}:{date_from or ''}:{date_to or ''}"
        cached    = self._cache.get(cache_key)
        if cached is not None:
            return cached

        if group_by not in self._group_expr:
            raise ValueError(f"Invalid group_by '{group_by}'. Valid: {', '.join(self._group_expr)}")
        col_expr, col_alias = self._group_expr[group_by]
        t, mc, pv, dc = self._table, self._metric_col, self._positive_val, self._date_col
        dc_cast = f"CAST({dc} AS DATE)"

        if date_from or date_to:
            clauses = []
            if date_from:
                clauses.append(f"AND {dc} >= '{date_from}'")
            if date_to:
                clauses.append(f"AND {dc} <= '{date_to}'")
            period_clause = " ".join(clauses)
        elif period == "last_7_days":
            period_clause = f"AND {dc_cast} >= date_sub((SELECT MAX({dc_cast}) FROM {t}), 7)"
        elif period == "last_30_days":
            period_clause = f"AND {dc_cast} >= date_sub((SELECT MAX({dc_cast}) FROM {t}), 30)"
        elif period == "prior_30_days":
            period_clause = (
                f"AND {dc_cast} >= date_sub((SELECT MAX({dc_cast}) FROM {t}), 60) "
                f"AND {dc_cast} <  date_sub((SELECT MAX({dc_cast}) FROM {t}), 30)"
            )
        else:
            period_clause = ""

        segment_clause = ""
        if segments and self._group_cols:
            values         = ", ".join(f"'{s}'" for s in segments)
            segment_clause = f"AND {self._group_cols[0]} IN ({values})"

        result = self._query(f"""
        SELECT
            {col_expr}  AS `{col_alias}`,
            COUNT(*)                                                                    AS total,
            SUM(CASE WHEN {mc} = '{pv}' THEN 1 ELSE 0 END)                            AS positive_count,
            ROUND(100.0 * SUM(CASE WHEN {mc} = '{pv}' THEN 1 ELSE 0 END)
                / NULLIF(COUNT(*), 0), 1)                                               AS metric_rate
        FROM {t}
        WHERE 1=1
        {period_clause}
        {segment_clause}
        GROUP BY {col_expr}
        """)
        self._cache.set(cache_key, result)
        return result

    def get_threshold_alerts(
        self,
        threshold: float = 75.0,
        segments:  list[str] | None = None,
        date_from: str | None = None,
        date_to:   str | None = None,
    ) -> pd.DataFrame:
        self._require_table()
        cache_key = f"alerts:{threshold}:{','.join(sorted(segments or []))}:{date_from or ''}:{date_to or ''}"
        cached    = self._cache.get(cache_key)
        if cached is not None:
            return cached

        t, mc, pv, dc = self._table, self._metric_col, self._positive_val, self._date_col
        ec, enc        = self._entity_col, self._entity_name_col
        grp0           = self._group_cols[0] if self._group_cols else None

        segment_clause = ""
        if segments and grp0:
            values         = ", ".join(f"'{s}'" for s in segments)
            segment_clause = f"AND {grp0} IN ({values})"

        date_clause = ""
        if date_from:
            date_clause += f"AND {dc} >= '{date_from}' "
        if date_to:
            date_clause += f"AND {dc} <= '{date_to}' "

        group_name_expr = f"MAX({grp0})" if grp0 else "NULL"

        result = self._query(f"""
        SELECT
            {ec}                                                                        AS entity_id,
            MAX({enc})                                                                  AS label,
            {group_name_expr}                                                           AS group_name,
            COUNT(*)                                                                    AS total,
            SUM(CASE WHEN {mc} = '{pv}' THEN 1 ELSE 0 END)                            AS positive_count,
            ROUND(100.0 * SUM(CASE WHEN {mc} = '{pv}' THEN 1 ELSE 0 END)
                / NULLIF(COUNT(*), 0), 1)                                               AS metric_rate
        FROM {t}
        WHERE 1=1
        {segment_clause}
        {date_clause}
        GROUP BY {ec}
        HAVING ROUND(100.0 * SUM(CASE WHEN {mc} = '{pv}' THEN 1 ELSE 0 END)
            / NULLIF(COUNT(*), 0), 1) < {threshold}
        ORDER BY metric_rate ASC
        """)
        self._cache.set(cache_key, result)
        return result

    def entity_weekly_rates(self, entity_ids: list, weeks: int = 6) -> dict:
        if not entity_ids:
            return {}
        self._require_table()
        cache_key = f"weekly:{','.join(str(e) for e in sorted(entity_ids))}:{weeks}"
        cached    = self._cache.get(cache_key)
        if cached is not None:
            return cached

        t, mc, pv, dc, ec = self._table, self._metric_col, self._positive_val, self._date_col, self._entity_col
        ids_expr  = ", ".join(f"'{e}'" for e in entity_ids)
        dc_cast   = f"CAST({dc} AS DATE)"
        dow       = f"(dayofweek({dc_cast}) + 5) % 7"
        week_expr = (
            f"CONCAT("
            f"date_format(date_sub({dc_cast}, {dow}), 'yyyy-MM-dd'),"
            f"'/',"
            f"date_format(date_add(date_sub({dc_cast}, {dow}), 6), 'yyyy-MM-dd')"
            f")"
        )

        df = self._query(f"""
        SELECT
            {ec}                                                                        AS entity_id,
            {week_expr}                                                                 AS week,
            COUNT(*)                                                                    AS total,
            SUM(CASE WHEN {mc} = '{pv}' THEN 1 ELSE 0 END)                            AS positive_count
        FROM {t}
        WHERE {ec} IN ({ids_expr})
        GROUP BY {ec}, {week_expr}
        ORDER BY week ASC
        """)

        if df.empty:
            return {}

        all_weeks = sorted(df["week"].unique())[-weeks:]
        df        = df[df["week"].isin(all_weeks)].copy()
        df["rate"] = (df["positive_count"] / df["total"] * 100).round(1)
        pivot = (
            df.pivot(index="entity_id", columns="week", values="rate")
            .reindex(columns=all_weeks)
        )
        result = {
            eid: [None if pd.isna(v) else float(v) for v in pivot.loc[eid]]
            if eid in pivot.index else [None] * len(all_weeks)
            for eid in entity_ids
        }
        self._cache.set(cache_key, result)
        return result

    def compute_statistical_summary(
        self,
        group_by:  str = "",
        period:    str = "all",
        segments:  list[str] | None = None,
        date_from: str | None = None,
        date_to:   str | None = None,
    ) -> dict:
        df = self.compute_stats(group_by, period, segments, date_from, date_to)
        if df.empty or "metric_rate" not in df.columns:
            return {"error": "No data available."}
        return df["metric_rate"].describe().round(1).to_dict()

    def detect_anomalies(
        self,
        group_by:  str   = "",
        sigma:     float = 2.0,
        period:    str   = "all",
        segments:  list[str] | None = None,
        date_from: str | None = None,
        date_to:   str | None = None,
    ) -> pd.DataFrame:
        df = self.compute_stats(group_by, period, segments, date_from, date_to).copy()
        if df.empty or "metric_rate" not in df.columns:
            return pd.DataFrame()
        mean = df["metric_rate"].mean()
        std  = df["metric_rate"].std()
        if std == 0:
            return pd.DataFrame()
        df["z_score"] = ((df["metric_rate"] - mean) / std).round(2)
        return df[df["z_score"].abs() > sigma].sort_values("z_score").reset_index(drop=True)

    def get_top_n(
        self,
        group_by:  str  = "",
        n:         int  = 10,
        ascending: bool = True,
        period:    str  = "all",
        segments:  list[str] | None = None,
        date_from: str | None = None,
        date_to:   str | None = None,
    ) -> pd.DataFrame:
        df = self.compute_stats(group_by, period, segments, date_from, date_to)
        if df.empty or "metric_rate" not in df.columns:
            return pd.DataFrame()
        return (
            df.nsmallest(n, "metric_rate") if ascending
            else df.nlargest(n, "metric_rate")
        ).reset_index(drop=True)

    def analyze_weekly_trend(
        self,
        segments:  list[str] | None = None,
        date_from: str | None = None,
        date_to:   str | None = None,
    ) -> dict:
        cache_key = f"trend:{','.join(sorted(segments or []))}:{date_from or ''}:{date_to or ''}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached

        df = self.compute_stats("week", "all", segments, date_from, date_to)
        if df.empty or "metric_rate" not in df.columns or len(df) < 2:
            return {"direction": "unknown", "slope_per_week": 0.0, "weeks": []}
        df    = df.sort_values("week").reset_index(drop=True)
        rates = df["metric_rate"].values.astype(float)
        slope = float(np.polyfit(range(len(rates)), rates, 1)[0])
        if   slope >  0.1: direction = "improving"
        elif slope < -0.1: direction = "declining"
        else:              direction = "stable"
        result = {
            "direction":      direction,
            "slope_per_week": round(slope, 2),
            "weeks":          df.to_dict(orient="records"),
        }
        self._cache.set(cache_key, result)
        return result
