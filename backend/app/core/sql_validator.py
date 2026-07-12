"""SQL Security Validator - blocks dangerous statements"""
import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

ALLOWED_STATEMENTS = {"SELECT", "WITH"}

BLOCKED_KEYWORDS = [
    "DELETE", "UPDATE", "INSERT", "DROP", "ALTER", "MERGE",
    "TRUNCATE", "EXECUTE", "EXEC", "CREATE", "REPLACE",
    "ATTACH", "DETACH", "COPY", "EXPORT", "IMPORT",
    "CALL", "PRAGMA", "VACUUM", "CHECKPOINT",
]

INJECTION_PATTERNS = [
    r";\s*(DELETE|UPDATE|INSERT|DROP|ALTER|MERGE|TRUNCATE)",
    r"--\s*$",
    r"/\*.*?\*/",
    r"UNION\s+ALL\s+SELECT.*FROM\s+information_schema",
    r"xp_cmdshell",
    r"OPENROWSET",
    r"BULK\s+INSERT",
]


def validate_sql(sql: str) -> Tuple[bool, str]:
    """
    Validate SQL query for safety.
    Returns (is_safe, error_message)
    """
    if not sql or not sql.strip():
        return False, "Empty query"

    sql_clean = sql.strip()

    # Remove string literals temporarily for keyword checking
    sql_no_strings = re.sub(r"'[^']*'", "''", sql_clean)
    sql_no_strings = re.sub(r'"[^"]*"', '""', sql_no_strings)

    sql_upper = sql_no_strings.upper()

    # Check it starts with an allowed statement
    first_token = sql_upper.split()[0] if sql_upper.split() else ""
    if first_token not in ALLOWED_STATEMENTS:
        return False, f"Only SELECT queries are allowed. Got: {first_token}"

    # Check for blocked keywords
    for keyword in BLOCKED_KEYWORDS:
        # Match whole word
        pattern = r'\b' + keyword + r'\b'
        if re.search(pattern, sql_upper):
            return False, f"Forbidden keyword detected: {keyword}"

    # Check for injection patterns
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, sql_upper, re.IGNORECASE | re.DOTALL):
            return False, f"Potential SQL injection detected"

    # Check for multiple statements
    statements = [s.strip() for s in sql_clean.split(";") if s.strip()]
    if len(statements) > 1:
        return False, "Multiple statements are not allowed"

    return True, ""


def sanitize_table_name(name: str) -> str:
    """Sanitize a table name to prevent injection"""
    # Allow only alphanumeric and underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    # Ensure it doesn't start with a digit
    if sanitized and sanitized[0].isdigit():
        sanitized = 't_' + sanitized
    return sanitized[:63]  # DuckDB max identifier length


def sanitize_column_name(name: str) -> str:
    """Sanitize a column name"""
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', str(name))
    if sanitized and sanitized[0].isdigit():
        sanitized = 'col_' + sanitized
    return sanitized[:63]
