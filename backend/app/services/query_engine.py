"""Query execution engine using DuckDB."""

import time
import uuid
import json
import logging
from typing import Dict, Any, List, Optional

from app.core.config import settings
from app.core.database import get_duckdb_connection, get_metadata_connection
from app.services.sql_validator import validate_sql, sanitize_sql, add_limit_if_missing

logger = logging.getLogger(__name__)


class QueryEngine:
    def execute(
        self,
        sql: str,
        dataset_id: Optional[str] = None,
        user_id: Optional[str] = None,
        natural_language: Optional[str] = None,
        save_history: bool = True,
    ) -> Dict[str, Any]:
        """Execute SQL and return results."""
        query_id = str(uuid.uuid4())
        sql = sanitize_sql(sql)

        # Validate
        is_valid, errors = validate_sql(sql)
        if not is_valid:
            return {
                "query_id": query_id,
                "success": False,
                "errors": errors,
                "sql": sql,
                "rows": [],
                "columns": [],
                "row_count": 0,
                "execution_time_ms": 0,
            }

        # Add safety limit
        sql = add_limit_if_missing(sql, settings.MAX_QUERY_ROWS)

        start = time.time()
        try:
            conn = get_duckdb_connection()
            result = conn.execute(sql).fetchdf()
            conn.close()

            execution_ms = int((time.time() - start) * 1000)
            columns = list(result.columns)
            rows = result.to_dict(orient="records")

            # Convert non-serializable types
            rows = self._serialize_rows(rows)

            if save_history and natural_language:
                self._save_history(
                    query_id, user_id, dataset_id, natural_language, sql,
                    True, execution_ms, len(rows), None
                )

            return {
                "query_id": query_id,
                "success": True,
                "sql": sql,
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
                "execution_time_ms": execution_ms,
                "errors": [],
            }
        except Exception as e:
            execution_ms = int((time.time() - start) * 1000)
            error_msg = str(e)
            logger.error(f"Query execution error: {error_msg} | SQL: {sql}")

            if save_history and natural_language:
                self._save_history(
                    query_id, user_id, dataset_id, natural_language, sql,
                    False, execution_ms, 0, error_msg
                )

            return {
                "query_id": query_id,
                "success": False,
                "sql": sql,
                "columns": [],
                "rows": [],
                "row_count": 0,
                "execution_time_ms": execution_ms,
                "errors": [error_msg],
            }

    def _serialize_rows(self, rows: List[Dict]) -> List[Dict]:
        """Make rows JSON-serializable."""
        import math
        serialized = []
        for row in rows:
            clean_row = {}
            for k, v in row.items():
                if v is None:
                    clean_row[k] = None
                elif isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                    clean_row[k] = None
                elif hasattr(v, "isoformat"):
                    clean_row[k] = v.isoformat()
                elif isinstance(v, (int, float, str, bool)):
                    clean_row[k] = v
                else:
                    clean_row[k] = str(v)
            serialized.append(clean_row)
        return serialized

    def _save_history(
        self, query_id, user_id, dataset_id, nl, sql,
        is_valid, exec_ms, row_count, error
    ):
        try:
            conn = get_metadata_connection()
            conn.execute("""
                INSERT INTO query_history
                (id, user_id, dataset_id, natural_language, generated_sql,
                 is_valid, execution_time_ms, row_count, error_message)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (query_id, user_id, dataset_id, nl, sql,
                  1 if is_valid else 0, exec_ms, row_count, error))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Could not save query history: {e}")

    def get_history(self, user_id: Optional[str] = None, limit: int = 50) -> List[Dict]:
        conn = get_metadata_connection()
        if user_id:
            rows = conn.execute(
                "SELECT * FROM query_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                (user_id, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM query_history ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def toggle_favorite(self, query_id: str, user_id: str) -> bool:
        conn = get_metadata_connection()
        row = conn.execute(
            "SELECT is_favorite FROM query_history WHERE id=? AND user_id=?",
            (query_id, user_id)
        ).fetchone()
        if row:
            new_val = 0 if row[0] else 1
            conn.execute(
                "UPDATE query_history SET is_favorite=? WHERE id=?",
                (new_val, query_id)
            )
            conn.commit()
            conn.close()
            return bool(new_val)
        conn.close()
        return False
