"""Query execution service"""
import logging
import time
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.core.database import get_new_connection
from app.core.sql_validator import validate_sql
from app.core.config import settings

logger = logging.getLogger(__name__)


class QueryService:
    """Executes SQL queries safely against DuckDB"""

    def execute_query(
        self,
        sql: str,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Execute a validated SQL query and return results"""
        # Validate SQL safety
        is_safe, error_msg = validate_sql(sql)
        if not is_safe:
            return {"error": f"Query blocked: {error_msg}", "data": [], "columns": []}

        # Add limit if not present
        sql_with_limit = self._add_limit(sql, limit or settings.MAX_ROWS)

        conn = get_new_connection()
        start_time = time.time()

        try:
            result = conn.execute(sql_with_limit)
            columns = [desc[0] for desc in result.description]

            rows = result.fetchall()
            execution_time = round((time.time() - start_time) * 1000, 2)

            # Serialize rows (handle non-JSON types)
            data = []
            for row in rows:
                row_dict = {}
                for col, val in zip(columns, row):
                    row_dict[col] = self._serialize_value(val)
                data.append(row_dict)

            # Get total count for pagination
            total_count = len(data)

            return {
                "data": data,
                "columns": columns,
                "row_count": len(data),
                "total_count": total_count,
                "execution_time_ms": execution_time,
                "sql": sql,
            }

        except Exception as e:
            logger.error(f"Query execution error: {e}")
            return {
                "error": str(e),
                "data": [],
                "columns": [],
                "sql": sql,
            }
        finally:
            conn.close()

    def get_schema_context(self, tables: Optional[List[str]] = None) -> str:
        """Get schema context string for LLM"""
        conn = get_new_connection()
        try:
            # Get all table names
            all_tables = conn.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'main' AND table_name NOT LIKE '\\_\\_%' ESCAPE '\\'
            """).fetchall()

            schema_parts = []
            for (table_name,) in all_tables:
                if tables and table_name not in tables:
                    continue

                # Get columns
                cols = conn.execute(f"""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = ? AND table_schema = 'main'
                    ORDER BY ordinal_position
                """, [table_name]).fetchall()

                if not cols:
                    continue

                # Get sample data
                try:
                    sample = conn.execute(f'SELECT * FROM "{table_name}" LIMIT 3').fetchall()
                    sample_rows = [dict(zip([c[0] for c in cols], row)) for row in sample]
                except Exception:
                    sample_rows = []

                col_str = ", ".join([f"{c[0]} ({c[1]})" for c in cols])
                schema_parts.append(
                    f"Table: {table_name}\n"
                    f"Columns: {col_str}\n"
                    f"Sample data: {json.dumps(sample_rows[:2], default=str)}"
                )

            return "\n\n".join(schema_parts) if schema_parts else "No tables available."

        except Exception as e:
            logger.error(f"Schema context error: {e}")
            return "Schema not available."
        finally:
            conn.close()

    def get_column_stats(self, table_name: str, column_name: str) -> Dict[str, Any]:
        """Get statistics for a specific column"""
        conn = get_new_connection()
        try:
            result = conn.execute(f"""
                SELECT 
                    COUNT(*) as total,
                    COUNT("{column_name}") as non_null,
                    COUNT(*) - COUNT("{column_name}") as null_count,
                    COUNT(DISTINCT "{column_name}") as unique_count
                FROM "{table_name}"
            """).fetchone()

            stats = {
                "total": result[0],
                "non_null": result[1],
                "null_count": result[2],
                "unique_count": result[3],
            }

            # Try numeric stats
            try:
                num_result = conn.execute(f"""
                    SELECT 
                        MIN("{column_name}"),
                        MAX("{column_name}"),
                        AVG(TRY_CAST("{column_name}" AS DOUBLE)),
                        STDDEV(TRY_CAST("{column_name}" AS DOUBLE))
                    FROM "{table_name}"
                """).fetchone()

                stats.update({
                    "min": self._serialize_value(num_result[0]),
                    "max": self._serialize_value(num_result[1]),
                    "mean": round(num_result[2], 4) if num_result[2] else None,
                    "std": round(num_result[3], 4) if num_result[3] else None,
                })
            except Exception:
                pass

            return stats
        except Exception as e:
            return {"error": str(e)}
        finally:
            conn.close()

    def _add_limit(self, sql: str, limit: int) -> str:
        """Add LIMIT clause if not present"""
        sql_upper = sql.upper().strip().rstrip(";")
        if "LIMIT" not in sql_upper:
            return f"{sql.rstrip(';')} LIMIT {limit}"
        return sql

    def _serialize_value(self, val):
        """Serialize Python value for JSON"""
        if val is None:
            return None
        if isinstance(val, (int, float, str, bool)):
            return val
        if isinstance(val, datetime):
            return val.isoformat()
        try:
            import math
            if isinstance(val, float) and math.isnan(val):
                return None
        except Exception:
            pass
        return str(val)


query_service = QueryService()
