"""LLM service: Ollama integration with schema-aware SQL generation."""

import json
import logging
import httpx
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        base_url = settings.OLLAMA_BASE_URL
        if not base_url.startswith(("http://", "https://")):
            base_url = f"http://{base_url}"
        self.base_url = base_url
        self.model = settings.DEFAULT_MODEL
        self.timeout = settings.LLM_TIMEOUT

    def set_model(self, model: str):
        self.model = model

    async def generate_sql(
        self,
        natural_language: str,
        schema: List[Dict],
        conversation_history: Optional[List[Dict]] = None,
        dataset_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate SQL from natural language with schema context."""
        schema_text = self._build_schema_text(schema)
        system_prompt = self._build_system_prompt(schema_text)
        messages = self._build_messages(natural_language, conversation_history, system_prompt)

        response_text = await self._call_ollama(messages)
        sql = self._extract_sql(response_text)
        explanation = self._extract_explanation(response_text)

        return {
            "sql": sql,
            "explanation": explanation,
            "raw_response": response_text,
            "model": self.model,
        }

    async def explain_sql(self, sql: str) -> str:
        """Explain what a SQL query does in plain English."""
        prompt = f"""Explain this SQL query in simple business terms (2-3 sentences, no jargon):

```sql
{sql}
```

Explain what data it retrieves and what business question it answers."""

        messages = [{"role": "user", "content": prompt}]
        return await self._call_ollama(messages)

    async def suggest_questions(self, schema: List[Dict]) -> List[str]:
        """Suggest business questions based on the schema."""
        schema_text = self._build_schema_text(schema)
        prompt = f"""Given these database tables:
{schema_text}

Generate 8 practical business questions a user might ask. Return ONLY a JSON array of question strings.
Example: ["What are the top 10 products by sales?", "Show monthly trends..."]
Return only valid JSON, no other text."""

        messages = [{"role": "user", "content": prompt}]
        response = await self._call_ollama(messages)
        try:
            clean = response.strip().lstrip("```json").rstrip("```").strip()
            questions = json.loads(clean)
            if isinstance(questions, list):
                return questions[:8]
        except Exception:
            pass
        return [
            "Show me all records",
            "What are the top 10 entries?",
            "Show summary statistics",
            "List all unique values",
            "Show recent entries",
            "Show distribution by category",
            "What are the totals by group?",
            "Show trends over time",
        ]

    async def optimize_sql(self, sql: str, schema: List[Dict]) -> str:
        """Suggest SQL optimizations."""
        schema_text = self._build_schema_text(schema)
        prompt = f"""Review and optimize this SQL query for DuckDB:

```sql
{sql}
```

Schema context:
{schema_text}

Return only the optimized SQL, no explanation."""
        messages = [{"role": "user", "content": prompt}]
        response = await self._call_ollama(messages)
        return self._extract_sql(response) or sql

    async def list_models(self) -> List[str]:
        """List available Ollama models."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.warning(f"Could not list Ollama models: {e}")
        return []

    async def _call_ollama(self, messages: List[Dict]) -> str:
        """Call Ollama chat API."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": settings.TEMPERATURE,
                        "num_predict": settings.MAX_TOKENS,
                    },
                }
                resp = await client.post(f"{self.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["message"]["content"]
        except httpx.TimeoutException:
            raise TimeoutError(f"LLM request timed out after {self.timeout}s")
        except httpx.ConnectError:
            raise ConnectionError(f"Cannot connect to Ollama at {self.base_url}. Is Ollama running?")
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise

    def _build_schema_text(self, schema: List[Dict]) -> str:
        """Format schema for LLM prompt."""
        lines = []
        for table in schema:
            lines.append(f"\nTable: {table['table_name']} ({table.get('display_name', '')})")
            lines.append(f"  Rows: {table.get('row_count', 'unknown')}")
            lines.append("  Columns:")
            for col in table.get("columns", []):
                null_info = f"(nullable, {col['null_pct']}% null)" if col["null_count"] > 0 else "(not null)"
                sample = col.get("sample_values", [])[:3]
                sample_str = f" | samples: {sample}" if sample else ""
                lines.append(f"    - {col['name']} {col['dtype']} {null_info}{sample_str}")
        return "\n".join(lines)

    def _build_system_prompt(self, schema_text: str) -> str:
        return f"""You are an expert SQL analyst. Generate DuckDB-compatible SQL queries from natural language.

DATABASE SCHEMA:
{schema_text}

RULES:
1. ONLY generate SELECT, WITH, GROUP BY, ORDER BY, HAVING, LIMIT queries.
2. NEVER use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE.
3. Always use double-quoted identifiers for table names AND column names: "table_name", "column_name".
4. If you create a column alias with AS, always wrap it in double quotes, e.g. AS "Total Events" — never write a multi-word alias without quotes.
5. When referencing a multi-word alias again later in the same query (e.g. in ORDER BY or GROUP BY), you must repeat the double quotes around it, e.g. ORDER BY "Total Events" DESC — never write it unquoted there either.
6. Return results with meaningful column aliases.
7. Default LIMIT to 1000 unless the user specifies otherwise.
8. Use DuckDB syntax (supports STRFTIME, EPOCH, LIST_AGG, etc.)

FORMAT your response as:
SQL:
```sql
<your query here>
```

EXPLANATION:
<1-2 sentence plain English explanation>"""

    def _build_messages(
        self,
        question: str,
        history: Optional[List[Dict]],
        system_prompt: str,
    ) -> List[Dict]:
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for h in history[-6:]:  # Last 3 exchanges
                messages.append({"role": h["role"], "content": h["content"]})
        messages.append({"role": "user", "content": question})
        return messages

    @staticmethod
    def _extract_sql(text: str) -> str:
        """Extract SQL block from LLM response."""
        import re
        patterns = [
            r"```sql\s*(.*?)\s*```",
            r"```\s*(SELECT.*?)\s*```",
            r"SQL:\s*(SELECT.*?)(?:\n\n|EXPLANATION|$)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                sql = match.group(1).strip()
                if sql.upper().startswith("SELECT") or sql.upper().startswith("WITH"):
                    return sql
        # Fallback: find SELECT statement
        select_match = re.search(r"(SELECT\s+.+)", text, re.DOTALL | re.IGNORECASE)
        if select_match:
            return select_match.group(1).strip()
        return ""

    @staticmethod
    def _extract_explanation(text: str) -> str:
        """Extract explanation from LLM response."""
        import re
        match = re.search(r"EXPLANATION[:\s]+(.*?)(?:\n\n|$)", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        lines = [l.strip() for l in text.split("\n") if l.strip() and not l.strip().startswith(("```", "SQL", "SELECT", "WITH"))]
        return lines[-1] if lines else ""
