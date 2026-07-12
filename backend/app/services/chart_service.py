"""Auto-chart generation from query results."""

import logging
from typing import List, Dict, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class ChartService:
    def auto_generate_charts(self, rows: List[Dict], columns: List[str]) -> List[Dict]:
        """Automatically determine best chart types and config from data."""
        if not rows or not columns:
            return []

        df = pd.DataFrame(rows, columns=columns)
        charts = []

        numeric_cols = df.select_dtypes(include="number").columns.tolist()
        date_cols = [c for c in columns if any(kw in c.lower() for kw in ["date", "time", "year", "month", "day"])]
        cat_cols = [c for c in columns if c not in numeric_cols and c not in date_cols]

        # Line chart: date + numeric
        if date_cols and numeric_cols:
            charts.append(self._line_chart(df, date_cols[0], numeric_cols[:3]))

        # Bar chart: category + numeric
        if cat_cols and numeric_cols:
            cat_col = cat_cols[0]
            if df[cat_col].nunique() <= 20:
                charts.append(self._bar_chart(df, cat_col, numeric_cols[0]))

        # Pie chart: 2-8 unique categories
        if cat_cols and numeric_cols:
            cat_col = cat_cols[0]
            if 2 <= df[cat_col].nunique() <= 8:
                charts.append(self._pie_chart(df, cat_col, numeric_cols[0]))

        # Scatter: 2+ numeric columns
        if len(numeric_cols) >= 2:
            charts.append(self._scatter_chart(df, numeric_cols[0], numeric_cols[1]))

        # Heatmap / correlation: 3+ numeric
        if len(numeric_cols) >= 3:
            charts.append(self._heatmap_chart(df, numeric_cols[:5]))

        # KPI cards
        charts.append(self._kpi_cards(df, numeric_cols[:4]))

        return [c for c in charts if c]

    def _line_chart(self, df: pd.DataFrame, x_col: str, y_cols: List[str]) -> Dict:
        try:
            series = []
            for y_col in y_cols[:3]:
                agg = df.groupby(x_col)[y_col].sum().reset_index()
                series.append({
                    "name": y_col,
                    "type": "line",
                    "data": agg[y_col].tolist(),
                    "smooth": True,
                })
            x_data = df[x_col].astype(str).unique().tolist()[:100]
            return {
                "type": "line",
                "title": f"{', '.join(y_cols[:2])} over {x_col}",
                "config": {
                    "xAxis": {"type": "category", "data": x_data},
                    "yAxis": {"type": "value"},
                    "series": series,
                    "tooltip": {"trigger": "axis"},
                    "legend": {"data": y_cols[:3]},
                    "grid": {"containLabel": True},
                },
            }
        except Exception as e:
            logger.warning(f"Line chart error: {e}")
            return None

    def _bar_chart(self, df: pd.DataFrame, x_col: str, y_col: str) -> Dict:
        try:
            agg = df.groupby(x_col)[y_col].sum().sort_values(ascending=False).head(15).reset_index()
            return {
                "type": "bar",
                "title": f"{y_col} by {x_col}",
                "config": {
                    "xAxis": {"type": "category", "data": agg[x_col].astype(str).tolist()},
                    "yAxis": {"type": "value"},
                    "series": [{"type": "bar", "data": agg[y_col].tolist(), "name": y_col}],
                    "tooltip": {"trigger": "axis"},
                    "grid": {"containLabel": True},
                },
            }
        except Exception as e:
            logger.warning(f"Bar chart error: {e}")
            return None

    def _pie_chart(self, df: pd.DataFrame, cat_col: str, val_col: str) -> Dict:
        try:
            agg = df.groupby(cat_col)[val_col].sum().reset_index()
            data = [{"name": str(r[cat_col]), "value": float(r[val_col])} for _, r in agg.iterrows()]
            return {
                "type": "pie",
                "title": f"{val_col} distribution by {cat_col}",
                "config": {
                    "series": [{
                        "type": "pie",
                        "radius": "60%",
                        "data": data,
                        "label": {"show": True, "formatter": "{b}: {d}%"},
                    }],
                    "tooltip": {"trigger": "item"},
                    "legend": {"orient": "vertical", "left": "left"},
                },
            }
        except Exception as e:
            logger.warning(f"Pie chart error: {e}")
            return None

    def _scatter_chart(self, df: pd.DataFrame, x_col: str, y_col: str) -> Dict:
        try:
            sample = df[[x_col, y_col]].dropna().head(500)
            data = [[float(r[x_col]), float(r[y_col])] for _, r in sample.iterrows()]
            return {
                "type": "scatter",
                "title": f"{y_col} vs {x_col}",
                "config": {
                    "xAxis": {"type": "value", "name": x_col},
                    "yAxis": {"type": "value", "name": y_col},
                    "series": [{"type": "scatter", "data": data, "symbolSize": 6}],
                    "tooltip": {"trigger": "item"},
                    "grid": {"containLabel": True},
                },
            }
        except Exception as e:
            logger.warning(f"Scatter chart error: {e}")
            return None

    def _heatmap_chart(self, df: pd.DataFrame, num_cols: List[str]) -> Dict:
        try:
            corr = df[num_cols].corr().round(2)
            cols = list(corr.columns)
            data = []
            for i, c1 in enumerate(cols):
                for j, c2 in enumerate(cols):
                    data.append([i, j, float(corr.loc[c1, c2])])
            return {
                "type": "heatmap",
                "title": "Correlation Heatmap",
                "config": {
                    "xAxis": {"type": "category", "data": cols},
                    "yAxis": {"type": "category", "data": cols},
                    "series": [{
                        "type": "heatmap",
                        "data": data,
                        "label": {"show": True},
                    }],
                    "visualMap": {"min": -1, "max": 1, "calculable": True,
                                   "inRange": {"color": ["#1E3A5F", "#fff", "#b71c1c"]}},
                    "tooltip": {"position": "top"},
                },
            }
        except Exception as e:
            logger.warning(f"Heatmap chart error: {e}")
            return None

    def _kpi_cards(self, df: pd.DataFrame, num_cols: List[str]) -> Dict:
        try:
            kpis = []
            for col in num_cols[:4]:
                kpis.append({
                    "label": col.replace("_", " ").title(),
                    "value": float(df[col].sum()),
                    "avg": float(df[col].mean()),
                    "count": int(df[col].count()),
                })
            return {"type": "kpi", "title": "Key Metrics", "kpis": kpis}
        except Exception as e:
            logger.warning(f"KPI cards error: {e}")
            return None
