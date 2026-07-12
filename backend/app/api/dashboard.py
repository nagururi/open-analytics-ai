from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import uuid
import json
from datetime import datetime
from app.core.security import get_current_user
from app.core.database import get_metadata_connection

router = APIRouter()


class DashboardCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    config_json: dict
    is_public: bool = False


@router.post("")
def create_dashboard(req: DashboardCreate, user=Depends(get_current_user)):
    conn = get_metadata_connection()
    did = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO dashboards (id, name, description, config_json, created_by, is_public) VALUES (?,?,?,?,?,?)",
        (did, req.name, req.description, json.dumps(req.config_json), user["username"], int(req.is_public))
    )
    conn.commit()
    conn.close()
    return {"id": did, "name": req.name}


@router.get("")
def list_dashboards(user=Depends(get_current_user)):
    conn = get_metadata_connection()
    rows = conn.execute(
        "SELECT id, name, description, is_public, created_by, created_at FROM dashboards ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


@router.get("/{dashboard_id}")
def get_dashboard(dashboard_id: str, user=Depends(get_current_user)):
    conn = get_metadata_connection()
    row = conn.execute("SELECT * FROM dashboards WHERE id=?", (dashboard_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Dashboard not found")
    d = dict(row)
    d["config_json"] = json.loads(d["config_json"])
    return d


@router.delete("/{dashboard_id}")
def delete_dashboard(dashboard_id: str, user=Depends(get_current_user)):
    conn = get_metadata_connection()
    conn.execute("DELETE FROM dashboards WHERE id=? AND created_by=?", (dashboard_id, user["username"]))
    conn.commit()
    conn.close()
    return {"deleted": dashboard_id}
