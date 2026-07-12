"""SQL Validator: safety checks, injection prevention, DuckDB validation."""

import re
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)

ALLOWED_KEYWORDS = {"SELECT", "WITH", "FROM", "WHERE", "GROUP", "BY", "ORDER", "HAVING",
                     "LIMIT", "OFFSET", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER", "FULL",
                     "CROSS", "UNION", "ALL", "DISTINCT", "AS", "ON", "AND", "OR", "NOT",
                     "IN", "LIKE", "BETWEEN", "IS", "NULL", "CASE", "WHEN", "THEN", "ELSE",
                     "END", "COUNT", "SUM", "AVG", "MIN", "MAX", "ROUND", "COALESCE",
                     "NULLIF", "CAST", "EPOCH", "STRFTIME", "DATE_TRUNC", "INTERVAL",
                     "OVER", "PARTITION", "ROW_NUMBER", "RANK", "DENSE_RANK", "LAG", "LEAD",
                     "FIRST_VALUE", "LAST_VALUE", "NTILE", "PERCENT_RANK", "CUME_DIST",
                     "LIST_AGG", "STRING_AGG", "ARRAY_AGG", "PERCENTILE_CONT",
                     "PERCENTILE_DISC", "FILTER", "WITHIN", "ASC", "DESC", "NULLS",
                     "FIRST", "LAST", "TRUE", "FALSE", "EXTRACT", "YEAR", "MONTH", "DAY",
                     "HOUR", "MINUTE", "SECOND", "CURRENT_DATE", "CURRENT_TIMESTAMP",
                     "NOW", "TODAY", "GREATEST", "LEAST", "IIF", "IF", "IFNULL",
                     "CONCAT", "LENGTH", "UPPER", "LOWER", "TRIM", "LTRIM", "RTRIM",
                     "SUBSTRING", "SUBSTR", "REPLACE", "REGEXP_MATCHES", "CONTAINS",
                     "STARTS_WITH", "ENDS_WITH", "SPLIT_PART", "STRING_SPLIT", "PRINTF",
                     "FORMAT", "FLOOR", "CEIL", "CEILING", "ABS", "POWER", "SQRT", "LN",
                     "LOG", "MOD", "RANDOM", "GENERATE_SERIES", "UNNEST"}

FORBIDDEN_PATTERNS = [
    r"\bDELETE\b", r"\bUPDATE\b", r"\bINSERT\b", r"\bDROP\b",
    r"\bALTER\b", r"\bMERGE\b", r"\bTRUNCATE\b", r"\bEXECUTE\b",
    r"\bEXEC\b", r"\bCREATE\b", r"\bGRANT\b", r"\bREVOKE\b",
    r"\bCOPY\b", r"\bATTACH\b", r"\bDETACH\b", r"\bPRAGMA\b",
    r"--[^\n]*",  # SQL comments (potential injection)
    r"/\*.*?\*/",  # Block comments
    r";\s*\w",  # Multiple statements
    r"\bxp_\w+\b",  # SQL Server extended procs
    r"\bsys\.\w+\b",  # System tables
    r"0x[0-9a-fA-F]+",  # Hex literals (potential injection)
    r"\bSLEEP\b", r"\bWAITFOR\b", r"\bBENCHMARK\b",  # Time-based injection
    r"UNION\s+SELECT\s+NULL",  # Union injection
    r"'\s*OR\s+'",  # OR injection
    r"'\s*AND\s+'",  # AND injection
]


def validate_sql(sql: str) -> Tuple[bool, List[str]]:
    """
    Validate SQL for safety and correctness.
    Returns (is_valid, list_of_errors)
    """
    errors = []

    if not sql or not sql.strip():
        return False, ["Empty SQL query"]

    sql_upper = sql.upper().strip()

    # Must start with SELECT or WITH
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        errors.append("Query must start with SELECT or WITH")

    # Check forbidden patterns
    for pattern in FORBIDDEN_PATTERNS:
        if re.search(pattern, sql, re.IGNORECASE | re.DOTALL):
            errors.append(f"Forbidden SQL pattern detected: {pattern}")

    # Check balanced parentheses
    if sql.count("(") != sql.count(")"):
        errors.append("Unbalanced parentheses")

    # Check balanced quotes
    single_quotes = sql.count("'") - sql.count("\\'")
    if single_quotes % 2 != 0:
        errors.append("Unbalanced single quotes")

    # Check for null bytes
    if "\x00" in sql:
        errors.append("Null bytes detected in query")

    # Length limit
    if len(sql) > 50000:
        errors.append("Query too long (max 50,000 characters)")

    return len(errors) == 0, errors


def fix_unquoted_alias_references(sql: str) -> str:
    """
    Small LLMs often declare a multi-word alias correctly (AS "Total Events")
    but then forget to quote it when referencing it again later in the same
    query (e.g. ORDER BY Total Events), which DuckDB can't parse. Since we
    can't rely on prompt instructions alone to fix this, detect declared
    multi-word aliases and auto-quote any later bare reference to them.
    """
    aliases = re.findall(r'AS\s+"([^"]+)"', sql, flags=re.IGNORECASE)
    for alias in aliases:
        if " " not in alias:
            continue
        pattern = re.compile(r'(?<!")\b' + re.escape(alias) + r'\b(?!")', re.IGNORECASE)
        sql = pattern.sub(lambda m, a=alias: f'"{a}"', sql)
    return sql


def sanitize_sql(sql: str) -> str:
    """Basic SQL sanitization."""
    # Remove null bytes
    sql = sql.replace("\x00", "")
    # Normalize whitespace
    sql = re.sub(r"\s+", " ", sql).strip()
    sql = fix_unquoted_alias_references(sql)
    return sql


def add_limit_if_missing(sql: str, limit: int = 1000) -> str:
    """Add LIMIT if not present to prevent runaway queries."""
    sql_upper = sql.upper()
    if "LIMIT" not in sql_upper:
        # Don't add limit if it's a CTE returning aggregated results
        if sql_upper.count("SELECT") == 1:
            return f"{sql.rstrip().rstrip(';')} LIMIT {limit}"
    return sql
