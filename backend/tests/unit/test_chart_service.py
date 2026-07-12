import pytest, sys
sys.path.insert(0, '/home/claude/open-analytics-ai/backend')
from app.services.chart_service import ChartService

svc = ChartService()

def _make_rows(n=20):
    import random
    categories = ['Alpha', 'Beta', 'Gamma', 'Delta']
    return [
        {'category': categories[i % 4], 'value': float(i * 1.5), 'count': i, 'date': f'2024-{(i%12)+1:02d}-01'}
        for i in range(1, n+1)
    ]

def test_auto_generate_returns_list():
    rows = _make_rows()
    cols = ['category', 'value', 'count', 'date']
    charts = svc.auto_generate_charts(rows, cols)
    assert isinstance(charts, list)

def test_empty_data_returns_empty():
    charts = svc.auto_generate_charts([], [])
    assert charts == []

def test_kpi_chart_present():
    rows = _make_rows()
    cols = ['category', 'value', 'count', 'date']
    charts = svc.auto_generate_charts(rows, cols)
    types = [c['type'] for c in charts]
    assert 'kpi' in types

def test_bar_chart_for_category():
    rows = _make_rows()
    cols = ['category', 'value', 'count', 'date']
    charts = svc.auto_generate_charts(rows, cols)
    types = [c['type'] for c in charts]
    assert 'bar' in types
