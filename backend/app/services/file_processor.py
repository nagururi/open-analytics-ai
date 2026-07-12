"""File processing: Excel, CSV → DuckDB tables with schema detection."""

import pandas as pd
import duckdb
import numpy as np
import uuid
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple

from app.core.config import settings
from app.core.database import get_duckdb_connection, get_metadata_connection

logger = logging.getLogger(__name__)


class FileProcessor:
    def __init__(self):
        self.duckdb = get_duckdb_connection()

    def process_file(self, file_path: str, original_name: str, user_id: str) -> Dict[str, Any]:
        """Main entry: process any uploaded file."""
        path = Path(file_path)
        ext = path.suffix.lower()
        dataset_id = str(uuid.uuid4())

        if ext in [".xlsx", ".xls", ".xlsm"]:
            tables = self._process_excel(file_path, dataset_id)
        elif ext == ".csv":
            tables = self._process_csv(file_path, dataset_id, path.stem)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

        total_rows = sum(t["row_count"] for t in tables)
        file_size = path.stat().st_size
        schema_info = self._detect_relationships(tables)

        # Save metadata
        conn = get_metadata_connection()
        conn.execute("""
            INSERT INTO datasets (id, name, original_filename, file_type, tables_json, row_count, size_bytes, uploaded_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dataset_id,
            path.stem,
            original_name,
            ext,
            json.dumps({"tables": tables, "relationships": schema_info}),
            total_rows,
            file_size,
            user_id,
        ))
        conn.commit()
        conn.close()

        return {
            "dataset_id": dataset_id,
            "name": path.stem,
            "tables": tables,
            "relationships": schema_info,
            "total_rows": total_rows,
            "file_size_bytes": file_size,
        }

    def _process_excel(self, file_path: str, dataset_id: str) -> List[Dict]:
        """Process all sheets in an Excel file."""
        xl = pd.ExcelFile(file_path)
        tables = []
        for sheet_name in xl.sheet_names:
            try:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                if df.empty or len(df.columns) == 0:
                    continue
                df = self._clean_dataframe(df)
                table_name = self._safe_table_name(f"{dataset_id}_{sheet_name}")
                table_info = self._load_to_duckdb(df, table_name, sheet_name)
                tables.append(table_info)
            except Exception as e:
                logger.error(f"Error processing sheet {sheet_name}: {e}")
        return tables

    def _process_csv(self, file_path: str, dataset_id: str, stem: str) -> List[Dict]:
        """Process a CSV file."""
        df = pd.read_csv(file_path, low_memory=False)
        df = self._clean_dataframe(df)
        table_name = self._safe_table_name(f"{dataset_id}_{stem}")
        table_info = self._load_to_duckdb(df, table_name, stem)
        return [table_info]

    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean column names and handle common issues."""
        df.columns = [
            str(c).strip().lower()
            .replace(" ", "_").replace("-", "_").replace(".", "_")
            .replace("(", "").replace(")", "").replace("/", "_")
            .replace("\\", "_").replace(":", "_")
            for c in df.columns
        ]
        # Remove completely empty rows/cols
        df = df.dropna(how="all").dropna(axis=1, how="all")
        # Deduplicate column names
        seen = {}
        new_cols = []
        for col in df.columns:
            if col in seen:
                seen[col] += 1
                new_cols.append(f"{col}_{seen[col]}")
            else:
                seen[col] = 0
                new_cols.append(col)
        df.columns = new_cols
        return df

    def _load_to_duckdb(self, df: pd.DataFrame, table_name: str, display_name: str) -> Dict:
        """Load DataFrame into DuckDB and return schema info."""
        conn = get_duckdb_connection()
        conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
        conn.register("__temp_df", df)
        conn.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM "__temp_df"')

        columns = self._get_column_info(conn, table_name, df)
        profile = self._profile_dataframe(df)

        conn.close()

        return {
            "table_name": table_name,
            "display_name": display_name,
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": columns,
            "profile": profile,
        }

    def _get_column_info(self, conn, table_name: str, df: pd.DataFrame) -> List[Dict]:
        """Extract column metadata."""
        columns = []
        for col in df.columns:
            dtype = str(df[col].dtype)
            null_count = int(df[col].isnull().sum())
            unique_count = int(df[col].nunique())
            sample = df[col].dropna().head(5).tolist()
            sample = [str(s) if not isinstance(s, (int, float, bool)) else s for s in sample]

            col_info = {
                "name": col,
                "dtype": dtype,
                "null_count": null_count,
                "null_pct": round(null_count / max(len(df), 1) * 100, 2),
                "unique_count": unique_count,
                "sample_values": sample,
                "is_numeric": pd.api.types.is_numeric_dtype(df[col]),
                "is_datetime": pd.api.types.is_datetime64_any_dtype(df[col]),
                "is_categorical": unique_count < 50 and unique_count < len(df) * 0.5,
            }

            if col_info["is_numeric"]:
                col_info["min"] = float(df[col].min()) if not df[col].empty else None
                col_info["max"] = float(df[col].max()) if not df[col].empty else None
                col_info["mean"] = float(df[col].mean()) if not df[col].empty else None
                col_info["std"] = float(df[col].std()) if not df[col].empty else None

            columns.append(col_info)
        return columns

    def _profile_dataframe(self, df: pd.DataFrame) -> Dict:
        """Generate data quality profile."""
        total_cells = df.shape[0] * df.shape[1]
        null_cells = int(df.isnull().sum().sum())
        dup_rows = int(df.duplicated().sum())
        quality_score = round((1 - (null_cells + dup_rows) / max(total_cells, 1)) * 100, 1)

        return {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "null_cells": null_cells,
            "null_pct": round(null_cells / max(total_cells, 1) * 100, 2),
            "duplicate_rows": dup_rows,
            "duplicate_pct": round(dup_rows / max(len(df), 1) * 100, 2),
            "quality_score": quality_score,
            "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
        }

    def _detect_relationships(self, tables: List[Dict]) -> List[Dict]:
        """Auto-detect potential FK relationships between tables."""
        relationships = []
        if len(tables) < 2:
            return relationships

        for i, t1 in enumerate(tables):
            for j, t2 in enumerate(tables):
                if i >= j:
                    continue
                cols1 = {c["name"] for c in t1["columns"]}
                cols2 = {c["name"] for c in t2["columns"]}
                common = cols1 & cols2
                for col in common:
                    if col not in ["id", "index", "row_number"]:
                        relationships.append({
                            "from_table": t1["table_name"],
                            "to_table": t2["table_name"],
                            "column": col,
                            "confidence": "high" if col.endswith("_id") else "medium",
                        })
        return relationships

    @staticmethod
    def _safe_table_name(name: str) -> str:
        import re
        import hashlib
        cleaned = re.sub(r"[^a-z0-9_]", "_", name.lower())
        if len(cleaned) <= 61:
            result = cleaned
        else:
            # Too long to safely keep in full: use a short deterministic hash
            # suffix instead of blind truncation, so the name is always
            # fixed-length and never silently drifts if input length varies.
            digest = hashlib.sha1(cleaned.encode()).hexdigest()[:8]
            result = f"{cleaned[:52]}_{digest}"
        # Table names must never start with a digit: unquoted SQL identifiers
        # starting with a digit are invalid, and a small LLM won't always
        # remember to quote them. Prefixing with a letter makes this
        # impossible by construction rather than relying on the model.
        return f"t_{result}"
