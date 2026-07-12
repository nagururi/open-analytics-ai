from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.core.security import get_current_user
from app.services.llm_service import LLMService
from app.services.query_engine import QueryEngine
from app.services.chart_service import ChartService
from app.core.database import get_metadata_connection
import json

router = APIRouter()
llm = LLMService()
engine = QueryEngine()
charts = ChartService()


class NLQueryRequest(BaseModel):
    question: str
    dataset_id: str
    model: Optional[str] = None
    conversation_history: Optional[List[dict]] = []


class SQLExecuteRequest(BaseModel):
    sql: str
    dataset_id: Optional[str] = None


@router.post("/nl")
async def nl_to_sql(req: NLQueryRequest, user=Depends(get_current_user)):
    """Convert natural language to SQL and execute."""
    # Load schema
    conn = get_metadata_connection()
    row = conn.execute("SELECT tables_json FROM datasets WHERE id=?", (req.dataset_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Dataset not found")

    tables_data = json.loads(row[0])
    schema = tables_data.get("tables", [])

    if req.model:
        llm.set_model(req.model)

    # Generate SQL
    gen = await llm.generate_sql(
        req.question, schema, req.conversation_history, req.dataset_id
    )

    if not gen["sql"]:
        raise HTTPException(422, "Could not generate valid SQL from that question. Try rephrasing.")

    # Execute
    result = engine.execute(
        gen["sql"],
        dataset_id=req.dataset_id,
        user_id=user["username"],
        natural_language=req.question,
    )

    # Auto charts
    chart_configs = []
    if result["success"] and result["rows"]:
        chart_configs = charts.auto_generate_charts(result["rows"], result["columns"])

    return {
        **result,
        "generated_sql": gen["sql"],
        "explanation": gen.get("explanation", ""),
        "model": gen.get("model", ""),
        "charts": chart_configs,
    }


@router.post("/execute")
def execute_sql(req: SQLExecuteRequest, user=Depends(get_current_user)):
    """Execute raw SQL directly."""
    result = engine.execute(
        req.sql,
        dataset_id=req.dataset_id,
        user_id=user["username"],
    )
    chart_configs = []
    if result["success"] and result["rows"]:
        chart_configs = charts.auto_generate_charts(result["rows"], result["columns"])
    return {**result, "charts": chart_configs}


@router.post("/explain")
async def explain(req: SQLExecuteRequest, user=Depends(get_current_user)):
    """Explain a SQL query in plain English."""
    explanation = await llm.explain_sql(req.sql)
    return {"explanation": explanation}


@router.get("/history")
def get_history(user=Depends(get_current_user)):
    return engine.get_history(user["username"])


@router.post("/history/{query_id}/favorite")
def toggle_favorite(query_id: str, user=Depends(get_current_user)):
    is_fav = engine.toggle_favorite(query_id, user["username"])
    return {"query_id": query_id, "is_favorite": is_fav}


@router.get("/suggestions/{dataset_id}")
async def get_suggestions(dataset_id: str, user=Depends(get_current_user)):
    conn = get_metadata_connection()
    row = conn.execute("SELECT tables_json FROM datasets WHERE id=?", (dataset_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Dataset not found")
    tables_data = json.loads(row[0])
    schema = tables_data.get("tables", [])
    questions = await llm.suggest_questions(schema)
    return {"suggestions": questions}
