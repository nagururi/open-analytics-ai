"""File upload and data ingestion service"""
import os
import pandas as pd
import duckdb
import logging
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
import json
from datetime import datetime

from app.core.config import settings
from app.core.database import get_new_connection
from app.core.sql_validator import sanitize_table_name, sanitize_column_name

logger = logging.getLogger(__name__)


class DataIngestionService:
    """Handles file uploads and data ingestion into DuckDB"""

    def __init__(self):
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def process_file(self, file_path: str, original_filename: str) -> Dict[str, Any]:
        """Process uploaded file and load into DuckDB"""
        ext = Path(original_filename).suffix.lower()
        tables_created = []

        if ext in [".xlsx", ".xls"]:
            tables_created = self._process_excel(file_path, original_filename)
        elif ext == ".csv":
            tables_created = self._process_csv(file_path, original_filename)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        return {
            "filename": original_filename,
            "tables": tables_created,
            "status": "success",
        }

    def _process_excel(self, file_path: str, original_filename: str) -> List[Dict]:
        """Process Excel file with potentially multiple sheets"""
        xl = pd.ExcelFile(file_path)
        tables = []
        base_name = Path(original_filename).stem

        for sheet_name in xl.sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                if df.empty:
                    continue
                table_name = sanitize_table_name(f"{base_name}_{sheet_name}")
                result = self._load_dataframe(df, table_name, original_filename, sheet_name)
                tables.append(result)
            except Exception as e:
                logger.error(f"Error processing sheet {sheet_name}: {e}")

        return tables

    def _process_csv(self, file_path: str, original_filename: str) -> List[Dict]:
        """Process CSV file"""
        base_name = Path(original_filename).stem
        table_name = sanitize_table_name(base_name)

        # Try different encodings
        df = None
        for encoding in ["utf-8", "latin-1", "cp1252"]:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                break
            except Exception:
                continue

        if df is None or df.empty:
            raise ValueError("Could not read CSV file")

        result = self._load_dataframe(df, table_name, original_filename, None)
        return [result]

    def _load_dataframe(self, df: pd.DataFrame, table_name: str,
                        source_file: str, sheet_name: Optional[str]) -> Dict:
        """Load a DataFrame into DuckDB"""
        # Clean column names
        df.columns = [sanitize_column_name(col) for col in df.columns]

        # Remove completely empty rows
        df = df.dropna(how='all')

        # Profile the data
        profile = self._profile_dataframe(df)

        conn = get_new_connection()
        try:
            # Drop if exists and recreate
            conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            conn.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM df')

            # Store metadata
            conn.execute("""
                CREATE TABLE IF NOT EXISTS _table_metadata (
                    table_name VARCHAR PRIMARY KEY,
                    source_file VARCHAR,
                    sheet_name VARCHAR,
                    row_count INTEGER,
                    column_count INTEGER,
                    columns_info JSON,
                    profile_info JSON,
                    created_at TIMESTAMP
                )
            """)

            columns_info = []
            for col in df.columns:
                dtype = str(df[col].dtype)
                columns_info.append({
                    "name": col,
                    "dtype": dtype,
                    "sample": str(df[col].dropna().head(3).tolist()),
                })

            conn.execute("""
                INSERT OR REPLACE INTO _table_metadata
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                table_name, source_file, sheet_name,
                len(df), len(df.columns),
                json.dumps(columns_info),
                json.dumps(profile),
                datetime.utcnow().isoformat(),
            ])

        finally:
            conn.close()

        return {
            "table_name": table_name,
            "sheet_name": sheet_name,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": list(df.columns),
            "profile": profile,
        }

    def _profile_dataframe(self, df: pd.DataFrame) -> Dict:
        """Generate data profile"""
        total_rows = len(df)
        profile = {
            "total_rows": total_rows,
            "total_columns": len(df.columns),
            "missing_cells": int(df.isnull().sum().sum()),
            "missing_pct": round(df.isnull().sum().sum() / max(total_rows * len(df.columns), 1) * 100, 2),
            "duplicate_rows": int(df.duplicated().sum()),
            "columns": {}
        }

        for col in df.columns:
            series = df[col]
            col_profile = {
                "dtype": str(series.dtype),
                "null_count": int(series.isnull().sum()),
                "null_pct": round(series.isnull().sum() / max(total_rows, 1) * 100, 2),
                "unique_count": int(series.nunique()),
                "unique_pct": round(series.nunique() / max(total_rows, 1) * 100, 2),
            }

            if pd.api.types.is_numeric_dtype(series):
                col_profile.update({
                    "min": float(series.min()) if not series.empty else None,
                    "max": float(series.max()) if not series.empty else None,
                    "mean": float(series.mean()) if not series.empty else None,
                    "std": float(series.std()) if not series.empty else None,
                    "type": "numeric",
                })
            elif pd.api.types.is_datetime64_any_dtype(series):
                col_profile["type"] = "datetime"
            else:
                col_profile["type"] = "categorical"
                top_vals = series.value_counts().head(5)
                col_profile["top_values"] = {str(k): int(v) for k, v in top_vals.items()}

            profile["columns"][col] = col_profile

        # Data quality score (0-100)
        completeness = max(0, 100 - profile["missing_pct"])
        uniqueness = min(100, (1 - profile["duplicate_rows"] / max(total_rows, 1)) * 100)
        profile["quality_score"] = round((completeness * 0.6 + uniqueness * 0.4), 1)

        return profile

    def get_all_tables(self) -> List[Dict]:
        """Get all tables with metadata"""
        conn = get_new_connection()
        try:
            try:
                result = conn.execute("""
                    SELECT table_name, source_file, sheet_name, row_count, 
                           column_count, columns_info, profile_info, created_at
                    FROM _table_metadata
                    ORDER BY created_at DESC
                """).fetchall()

                tables = []
                for row in result:
                    tables.append({
                        "table_name": row[0],
                        "source_file": row[1],
                        "sheet_name": row[2],
                        "row_count": row[3],
                        "column_count": row[4],
                        "columns": json.loads(row[5]) if row[5] else [],
                        "profile": json.loads(row[6]) if row[6] else {},
                        "created_at": row[7],
                    })
                return tables
            except Exception:
                return []
        finally:
            conn.close()

    def delete_table(self, table_name: str) -> bool:
        """Delete a table"""
        safe_name = sanitize_table_name(table_name)
        conn = get_new_connection()
        try:
            conn.execute(f'DROP TABLE IF EXISTS "{safe_name}"')
            conn.execute("DELETE FROM _table_metadata WHERE table_name = ?", [safe_name])
            return True
        except Exception as e:
            logger.error(f"Error deleting table {safe_name}: {e}")
            return False
        finally:
            conn.close()


ingestion_service = DataIngestionService()
