import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from typing import List
from app.core.config import settings
from app.core.security import get_current_user
from app.services.file_processor import FileProcessor

router = APIRouter()

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".csv"}

@router.post("")
async def upload_files(
    files: List[UploadFile] = File(...),
    user=Depends(get_current_user)
):
    results = []
    processor = FileProcessor()
    for file in files:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"File type {ext} not supported. Use: {ALLOWED_EXTENSIONS}")

        size = 0
        tmp_path = os.path.join(settings.UPLOAD_DIR, f"{uuid.uuid4().hex}{ext}")
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        with open(tmp_path, "wb") as f:
            chunk = await file.read(1024 * 1024)
            while chunk:
                size += len(chunk)
                if size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
                    os.remove(tmp_path)
                    raise HTTPException(413, f"File too large (max {settings.MAX_FILE_SIZE_MB}MB)")
                f.write(chunk)
                chunk = await file.read(1024 * 1024)

        try:
            result = processor.process_file(tmp_path, file.filename, user["username"])
            results.append(result)
        except Exception as e:
            os.remove(tmp_path)
            raise HTTPException(500, f"Error processing {file.filename}: {str(e)}")

    return {"uploaded": len(results), "datasets": results}


@router.get("/datasets")
def list_datasets(user=Depends(get_current_user)):
    from app.core.database import get_metadata_connection
    import json
    conn = get_metadata_connection()
    rows = conn.execute(
        "SELECT id, name, original_filename, file_type, row_count, size_bytes, created_at FROM datasets ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/datasets/{dataset_id}")
def get_dataset(dataset_id: str, user=Depends(get_current_user)):
    from app.core.database import get_metadata_connection
    import json
    conn = get_metadata_connection()
    row = conn.execute("SELECT * FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Dataset not found")
    d = dict(row)
    d["tables_json"] = json.loads(d["tables_json"])
    return d


@router.delete("/datasets/{dataset_id}")
def delete_dataset(dataset_id: str, user=Depends(get_current_user)):
    from app.core.database import get_metadata_connection, get_duckdb_connection
    import json
    conn = get_metadata_connection()
    row = conn.execute("SELECT * FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    if not row:
        raise HTTPException(404, "Dataset not found")
    tables_data = json.loads(row["tables_json"])
    dconn = get_duckdb_connection()
    for table in tables_data.get("tables", []):
        try:
            dconn.execute(f'DROP TABLE IF EXISTS "{table["table_name"]}"')
        except Exception:
            pass
    dconn.close()
    conn.execute("DELETE FROM datasets WHERE id=?", (dataset_id,))
    conn.commit()
    conn.close()
    return {"deleted": dataset_id}
