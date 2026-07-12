import pytest, sys
sys.path.insert(0, '/home/claude/open-analytics-ai/backend')
from app.services.sql_validator import validate_sql, sanitize_sql, add_limit_if_missing

def test_valid_select():
    ok, errors = validate_sql("SELECT * FROM my_table LIMIT 100")
    assert ok and errors == []

def test_valid_cte():
    ok, _ = validate_sql("WITH t AS (SELECT 1 AS n) SELECT * FROM t")
    assert ok

def test_rejects_delete():
    ok, errors = validate_sql("DELETE FROM users WHERE id=1")
    assert not ok and any("Forbidden" in e for e in errors)

def test_rejects_drop():
    ok, _ = validate_sql("DROP TABLE users")
    assert not ok

def test_rejects_insert():
    ok, _ = validate_sql("INSERT INTO t VALUES (1)")
    assert not ok

def test_rejects_update():
    ok, _ = validate_sql("UPDATE t SET x=1")
    assert not ok

def test_rejects_empty():
    ok, errors = validate_sql("")
    assert not ok and "Empty" in errors[0]

def test_rejects_null_bytes():
    ok, _ = validate_sql("SELECT \x00 FROM t")
    assert not ok

def test_rejects_multiple_statements():
    ok, _ = validate_sql("SELECT 1; DROP TABLE users")
    assert not ok

def test_unbalanced_parens():
    ok, _ = validate_sql("SELECT COUNT( FROM t")
    assert not ok

def test_add_limit():
    sql = add_limit_if_missing("SELECT * FROM t", 500)
    assert "LIMIT 500" in sql

def test_no_double_limit():
    result = add_limit_if_missing("SELECT * FROM t LIMIT 100", 500)
    assert result.count("LIMIT") == 1

def test_sanitize():
    result = sanitize_sql("SELECT \x00 FROM t")
    assert "\x00" not in result
