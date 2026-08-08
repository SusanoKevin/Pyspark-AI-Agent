from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.databricks_store import _assert_select_only


class TestSelectOnlyGuard:
    """The sqlglot SELECT-only guard is defense-in-depth around any
    `spark.sql(...)` text the CodeAgent's generated code might construct —
    kept from the old spark_store.py unchanged, now living in
    databricks_store.py."""

    def test_plain_select_is_allowed(self):
        _assert_select_only("SELECT * FROM sample_sales LIMIT 10")

    def test_select_with_join_and_where_is_allowed(self):
        _assert_select_only(
            "SELECT a.region, b.total FROM sample_sales a "
            "JOIN totals b ON a.region = b.region WHERE a.quantity > 5"
        )

    def test_insert_is_blocked(self):
        with pytest.raises(PermissionError):
            _assert_select_only("INSERT INTO sample_sales VALUES (1, '2024-01-01', 'North', 'Widget', 1, 9.99)")

    def test_update_is_blocked(self):
        with pytest.raises(PermissionError):
            _assert_select_only("UPDATE sample_sales SET quantity = 0 WHERE region = 'North'")

    def test_delete_is_blocked(self):
        with pytest.raises(PermissionError):
            _assert_select_only("DELETE FROM sample_sales WHERE region = 'North'")

    def test_drop_table_is_blocked(self):
        with pytest.raises(PermissionError):
            _assert_select_only("DROP TABLE sample_sales")

    def test_create_table_is_blocked(self):
        with pytest.raises(PermissionError):
            _assert_select_only("CREATE TABLE evil (id INT)")

    def test_alter_table_is_blocked(self):
        with pytest.raises(PermissionError):
            _assert_select_only("ALTER TABLE sample_sales ADD COLUMN evil STRING")

    def test_stacked_statements_are_blocked(self):
        with pytest.raises(PermissionError):
            _assert_select_only("SELECT * FROM sample_sales; DROP TABLE sample_sales;")

    def test_empty_sql_raises_value_error(self):
        with pytest.raises(ValueError):
            _assert_select_only("")

    def test_unparseable_sql_raises_value_error(self):
        with pytest.raises(ValueError):
            _assert_select_only("SELEKT * FORM nowhere !!!")
