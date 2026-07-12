from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
from app.core.security import get_current_user
from app.core.config import settings
from app.services.export_service import ExportService

router = APIRouter()
exporter = ExportService()


class ExportRequest(BaseModel):
    rows: List[Dict[str, Any]]
    columns: List[str]
    format: str  # csv, excel, pdf, html, pptx
    title: Optional[str] = "Query Results"
    sql: Optional[str] = ""


@router.post("")
def export_data(req: ExportRequest, user=Depends(get_current_user)):
    allowed_formats = {"csv", "excel", "pdf", "html", "pptx"}
    if req.format not in allowed_formats:
        raise HTTPException(400, f"Invalid format. Choose: {allowed_formats}")

    filename = exporter.export(req.rows, req.columns, req.format, req.title, req.sql)
    return {"filename": filename, "download_url": f"/exports/{filename}"}


@router.get("/download/{filename}")
def download_file(filename: str, user=Depends(get_current_user)):
    # Sanitize filename to prevent path traversal
    import re
    if not re.match(r"^[a-zA-Z0-9_\-.]+$", filename):
        raise HTTPException(400, "Invalid filename")
    path = os.path.join(settings.EXPORT_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(404, "File not found")
    return FileResponse(path, filename=filename)
