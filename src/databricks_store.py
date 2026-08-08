from __future__ import annotations

import logging
import os

import sqlglot
from sqlglot import exp

logger = logging.getLogger(__name__)

_FORBIDDEN = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create,
    exp.Alter, exp.TruncateTable, exp.Merge, exp.Command,
)


def _assert_select_only(sql: str) -> None:
    """Defense-in-depth guard around any `spark.sql(...)` text the generated
    code constructs. The executor's authorized-imports allowlist is the
    primary sandbox boundary; this catches SELECT-only violations even if
    a code attempt slips SQL past that boundary."""
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


class DatabricksDataStore:
    """Thin wrapper around a Databricks Connect Spark session.

    Unlike the old SparkDataStore, this holds no fixed analytics methods —
    the CodeAgent writes its own PySpark/SQL per task. This class provides
    two things the agent needs: (1) live catalog introspection to ground the
    agent in real table/column names instead of RAG, and (2) a guarded query
    escape hatch that keeps the sqlglot SELECT-only check available as
    defense-in-depth around any `spark.sql(...)` the generated code issues.
    """

    def __init__(self) -> None:
        self._catalog = os.environ.get("DATABRICKS_CATALOG", "")
        self._schema = os.environ.get("DATABRICKS_SCHEMA", "default")
        self._spark = self._build_session()

    def _build_session(self):
        from databricks.connect import DatabricksSession

        host = os.environ.get("DATABRICKS_HOST")
        token = os.environ.get("DATABRICKS_TOKEN")
        builder = DatabricksSession.builder

        if host and token:
            builder = builder.host(host).token(token)
        # Free Edition / free-tier workspaces expose serverless compute with
        # no cluster_id required — this is what keeps each self-repair
        # attempt a fast remote call rather than a new job submission.
        return builder.serverless(True).getOrCreate()

    @property
    def spark(self):
        return self._spark

    def _use_catalog_schema(self) -> None:
        if self._catalog:
            self._spark.catalog.setCurrentCatalog(self._catalog)
        self._spark.catalog.setCurrentDatabase(self._schema)

    def query(self, sql: str):
        """Run a guarded, read-only SELECT and return a pandas DataFrame."""
        _assert_select_only(sql)
        return self._spark.sql(sql).toPandas()

    def get_table_names(self) -> list[str]:
        self._use_catalog_schema()
        return [row.tableName for row in self._spark.catalog.listTables()]

    def get_schema_for_table(self, table_name: str) -> list[dict]:
        self._use_catalog_schema()
        return [
            {"name": c.name, "dataType": c.dataType}
            for c in self._spark.catalog.listColumns(table_name)
        ]

    def get_catalog_context(self) -> str:
        """Human-readable table/column summary used to ground the coding
        agent instead of RAG — always accurate since it's read live from the
        Unity Catalog, not a stale vector index."""
        try:
            tables = self.get_table_names()
        except Exception as e:
            logger.warning("Could not list tables: %s", e)
            return "No catalog information available (could not reach Databricks)."

        if not tables:
            return "No tables are registered in the configured catalog/schema."

        lines = []
        for table in tables:
            try:
                columns = self.get_schema_for_table(table)
            except Exception as e:
                logger.warning("Could not introspect columns for %s: %s", table, e)
                continue
            col_desc = ", ".join(f"{c['name']} ({c['dataType']})" for c in columns)
            lines.append(f"- {table}: {col_desc}")
        return "\n".join(lines) if lines else "No tables are registered."

    def ping(self) -> bool:
        try:
            self._spark.sql("SELECT 1").collect()
            return True
        except Exception:
            return False

    def close(self) -> None:
        self._spark.stop()
