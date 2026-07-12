from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user
from app.core.database import get_metadata_connection, get_duckdb_connection
import json

router = APIRouter()


@router.get("/{dataset_id}")
def get_schema(dataset_id: str, user=Depends(get_current_user)):
    conn = get_metadata_connection()
    row = conn.execute("SELECT * FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Dataset not found")
    d = dict(row)
    d["tables_json"] = json.loads(d["tables_json"])
    return d


@router.get("/{dataset_id}/preview/{table_name}")
def preview_table(dataset_id: str, table_name: str, limit: int = 100, user=Depends(get_current_user)):
    conn = get_metadata_connection()
    row = conn.execute("SELECT tables_json FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Dataset not found")

    tables_data = json.loads(row[0])
    valid_tables = [t["table_name"] for t in tables_data.get("tables", [])]
    if table_name not in valid_tables:
        raise HTTPException(404, "Table not found in dataset")

    dconn = get_duckdb_connection()
    try:
        result = dconn.execute(f'SELECT * FROM "{table_name}" LIMIT ?', [min(limit, 1000)]).fetchdf()
        dconn.close()
        return {
            "table_name": table_name,
            "columns": list(result.columns),
            "rows": result.to_dict(orient="records"),
            "row_count": len(result),
        }
    except Exception as e:
        dconn.close()
        raise HTTPException(500, str(e))


@router.get("/{dataset_id}/stats/{table_name}")
def table_stats(dataset_id: str, table_name: str, user=Depends(get_current_user)):
    """Get detailed column statistics."""
    conn = get_metadata_connection()
    row = conn.execute("SELECT tables_json FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Dataset not found")
    tables_data = json.loads(row[0])
    for t in tables_data.get("tables", []):
        if t["table_name"] == table_name:
            return {"table": t}
    raise HTTPException(404, "Table not found")
