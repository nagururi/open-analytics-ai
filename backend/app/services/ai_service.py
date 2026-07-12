"""AI Service - Natural Language to SQL via Ollama"""
import httpx
import json
import logging
import re
from typing import Dict, List, Any, Optional, AsyncGenerator
from app.core.config import settings

logger = logging.getLogger(__name__)


class AIService:
    """Handles communication with Ollama LLM for SQL generation"""

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.DEFAULT_MODEL

    def set_model(self, model: str):
        if model in settings.AVAILABLE_MODELS:
            self.model = model

    async def generate_sql(
        self,
        question: str,
        schema_context: str,
        conversation_history: Optional[List[Dict]] = None,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate SQL from natural language question"""
        active_model = model or self.model

        system_prompt = self._build_system_prompt(schema_context)
        user_prompt = self._build_user_prompt(question, conversation_history)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": active_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "stream": False,
                        "options": {
                            "temperature": 0.1,
                            "top_p": 0.9,
                            "num_predict": 1024,
                        }
                    }
                )
                response.raise_for_status()
                data = response.json()
                content = data.get("message", {}).get("content", "")
                return self._parse_llm_response(content, question)

        except httpx.ConnectError:
            return self._fallback_sql(question, schema_context)
        except Exception as e:
            logger.error(f"LLM error: {e}")
            return {"error": str(e), "sql": None, "explanation": None}

    async def stream_response(
        self,
        question: str,
        schema_context: str,
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream SQL generation response"""
        active_model = model or self.model
        system_prompt = self._build_system_prompt(schema_context)
        user_prompt = self._build_user_prompt(question)

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={
                        "model": active_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "stream": True,
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                chunk = json.loads(line)
                                content = chunk.get("message", {}).get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            yield f"Error: {str(e)}"

    async def explain_sql(self, sql: str, model: Optional[str] = None) -> str:
        """Explain what an SQL query does in plain English"""
        active_model = model or self.model

        prompt = f"""Explain the following SQL query in plain English, suitable for a business user.
Be concise and clear. Focus on what data it retrieves and any filters/aggregations applied.

SQL:
{sql}

Explanation:"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": active_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.3, "num_predict": 300}
                    }
                )
                response.raise_for_status()
                return response.json().get("response", "").strip()
        except Exception as e:
            return f"This query retrieves data based on your question. ({str(e)})"

    async def suggest_questions(self, schema_context: str, model: Optional[str] = None) -> List[str]:
        """Generate suggested questions based on the schema"""
        active_model = model or self.model

        prompt = f"""Given the following database schema, generate 8 insightful business questions 
a user might want to ask. Return ONLY a JSON array of question strings, nothing else.

Schema:
{schema_context[:2000]}

Questions (JSON array):"""

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": active_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.7, "num_predict": 500}
                    }
                )
                response.raise_for_status()
                text = response.json().get("response", "").strip()
                # Extract JSON array
                match = re.search(r'\[.*?\]', text, re.DOTALL)
                if match:
                    return json.loads(match.group())
        except Exception:
            pass

        # Fallback suggestions
        return [
            "Show me the total count of all records",
            "What are the top 10 entries by count?",
            "Show me a summary by category",
            "What is the distribution across different groups?",
            "Show me records from the last year",
            "What are the unique values in each category?",
            "Show me the average values by group",
            "Identify any missing or null values",
        ]

    async def check_ollama_status(self) -> Dict[str, Any]:
        """Check if Ollama is running and get available models"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [m["name"].split(":")[0] for m in data.get("models", [])]
                    return {"status": "connected", "models": models}
        except Exception as e:
            return {"status": "disconnected", "error": str(e), "models": []}

    def _build_system_prompt(self, schema_context: str) -> str:
        return f"""You are an expert SQL analyst. Your job is to convert natural language questions into valid DuckDB SQL queries.

DATABASE SCHEMA:
{schema_context}

RULES:
1. Generate ONLY SELECT queries. Never use DELETE, UPDATE, INSERT, DROP, ALTER, TRUNCATE, or CREATE.
2. Always use table names exactly as shown in the schema (they are case-sensitive).
3. Always use column names exactly as shown in the schema.
4. Use DuckDB-compatible SQL syntax.
5. Include appropriate GROUP BY when using aggregate functions.
6. Add ORDER BY and LIMIT clauses when showing rankings or top/bottom results.
7. Use meaningful aliases for calculated columns.
8. Handle NULL values appropriately using COALESCE or IS NULL/IS NOT NULL.
9. For date operations, use DuckDB date functions.

RESPONSE FORMAT:
Return a JSON object with exactly these fields:
{{
  "sql": "SELECT ...",
  "explanation": "Brief explanation of what this query does",
  "chart_type": "bar|line|pie|scatter|table",
  "chart_config": {{
    "x_axis": "column_name",
    "y_axis": "column_name",
    "title": "Chart title"
  }}
}}

Return ONLY the JSON object, no markdown, no backticks, no additional text."""

    def _build_user_prompt(self, question: str, history: Optional[List[Dict]] = None) -> str:
        context = ""
        if history:
            recent = history[-3:]  # Last 3 exchanges
            context = "\nPrevious questions for context:\n"
            for h in recent:
                context += f"Q: {h.get('question', '')}\n"

        return f"{context}\nQuestion: {question}\n\nGenerate the SQL query:"

    def _parse_llm_response(self, content: str, question: str) -> Dict[str, Any]:
        """Parse LLM response to extract SQL and metadata"""
        # Try to parse as JSON
        try:
            # Remove markdown code blocks if present
            cleaned = re.sub(r'```(?:json)?\s*', '', content).strip()
            cleaned = re.sub(r'```\s*$', '', cleaned).strip()

            # Find JSON object
            match = re.search(r'\{.*\}', cleaned, re.DOTALL)
            if match:
                data = json.loads(match.group())
                sql = data.get("sql", "").strip()
                if sql:
                    return {
                        "sql": sql,
                        "explanation": data.get("explanation", ""),
                        "chart_type": data.get("chart_type", "table"),
                        "chart_config": data.get("chart_config", {}),
                    }
        except Exception:
            pass

        # Fallback: extract SQL from code block or raw text
        sql_match = re.search(r'```sql\s*(.*?)\s*```', content, re.DOTALL | re.IGNORECASE)
        if sql_match:
            sql = sql_match.group(1).strip()
        else:
            # Try to find SELECT statement
            select_match = re.search(r'(SELECT\s+.*?)(?:;|$)', content, re.DOTALL | re.IGNORECASE)
            sql = select_match.group(1).strip() if select_match else None

        return {
            "sql": sql,
            "explanation": "Generated from your question.",
            "chart_type": "table",
            "chart_config": {},
        }

    def _fallback_sql(self, question: str, schema_context: str) -> Dict[str, Any]:
        """Generate a simple fallback SQL when Ollama is not available"""
        # Extract first table name from schema context
        table_match = re.search(r'Table: (\w+)', schema_context)
        table_name = table_match.group(1) if table_match else "data"

        return {
            "sql": f'SELECT * FROM "{table_name}" LIMIT 100',
            "explanation": "Ollama is not connected. Showing first 100 rows as fallback. Please ensure Ollama is running.",
            "chart_type": "table",
            "chart_config": {},
            "warning": "LLM not available - using fallback query",
        }


ai_service = AIService()
