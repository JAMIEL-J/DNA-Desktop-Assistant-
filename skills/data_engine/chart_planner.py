# skills/data_engine/chart_planner.py
import logging
from typing import Dict, List, Any, Optional
import duckdb
import pandas as pd

logger = logging.getLogger('dna.data_engine.chart_planner')


class DomainChartPlanner:
    """Generates uncapped, dynamically scaled SQL chart aggregations tailored to business domain."""

    def plan_and_execute(
        self,
        con: Optional[duckdb.DuckDBPyConnection],
        table_ref: str,
        schema: List[Dict[str, Any]],
        semantics: Dict[str, Any],
        domain_info: Dict[str, Any],
        sample_df: Optional[pd.DataFrame] = None
    ) -> List[Dict[str, Any]]:
        """Plan and run SQL aggregation queries based on semantic roles & domain."""
        charts = []
        domain = domain_info.get('domain', 'general')

        owned_con = None
        try:
            con_valid = False
            if con is not None:
                try:
                    con.execute("SELECT 1")
                    con_valid = True
                except Exception:
                    con_valid = False

            if not con_valid:
                owned_con = duckdb.connect()
                con = owned_con
                if sample_df is not None:
                    con.register('data_table', sample_df)
                    table_ref = 'data_table'
                else:
                    logger.warning("No sample_df provided and DuckDB connection was closed/invalid.")
                    return []

            pri_metric = semantics.get('primary_metric')
            sec_metrics = semantics.get('secondary_metrics', [])
            sec_metric = sec_metrics[0] if sec_metrics else None

            pri_dim = semantics.get('primary_dimension')
            sec_dims = semantics.get('secondary_dimensions', [])
            sec_dim = sec_dims[0] if sec_dims else None

            temporal_col = semantics.get('temporal_dimension')
            target_col = semantics.get('target_label')

            # Determine target chart count dynamically based on schema length
            col_count = len(schema)
            if col_count <= 5:
                max_charts = 6
            elif col_count <= 12:
                max_charts = 10
            else:
                max_charts = 16

            logger.info(
                "Planning charts for domain '%s' (Columns: %d, Max Target Charts: %d)",
                domain, col_count, max_charts
            )

            chart_idx = 0

            def _try_execute(title: str, chart_type: str, sql: str, takeaway: str) -> Optional[Dict[str, Any]]:
                nonlocal chart_idx
                if len(charts) >= max_charts:
                    return None
                try:
                    clean_sql = " ".join(line.strip() for line in sql.strip().splitlines())
                    res_df = con.execute(clean_sql).fetchdf()
                    if res_df.empty or len(res_df) == 0:
                        return None
                    chart_idx += 1
                    chart_obj = {
                        'chart_id': f"chart_{chart_idx}",
                        'title': title,
                        'chart_type': chart_type,
                        'domain': domain,
                        'sql': clean_sql,
                        'data': res_df.to_dict(orient='records'),
                        'default_takeaway': takeaway
                    }
                    charts.append(chart_obj)
                    return chart_obj
                except Exception as e:
                    logger.warning("Chart query failed for '%s': %s | SQL: %s", title, e, sql)
                    return None

            # -------------------------------------------------------------
            # 1. SPECIALIZED CHURN / RETENTION DOMAIN CHARTS
            # -------------------------------------------------------------
            if domain == 'churn' or target_col:
                t_col = target_col or 'churn'
                has_target = any(c['name'].lower() == t_col.lower() for c in schema)
                if has_target:
                    if pri_dim:
                        _try_execute(
                            f"Churn Event Rate by {pri_dim}",
                            "bar",
                            f"""
                            SELECT "{pri_dim}" AS category,
                                   COUNT(*) AS total_customers,
                                   SUM(CASE WHEN LOWER(CAST("{t_col}" AS VARCHAR)) IN ('yes', '1', 'true', 'churned') THEN 1 ELSE 0 END) AS churned_count,
                                   (AVG(CASE WHEN LOWER(CAST("{t_col}" AS VARCHAR)) IN ('yes', '1', 'true', 'churned') THEN 1.0 ELSE 0.0 END) * 100.0) AS churn_rate
                            FROM {table_ref}
                            WHERE "{pri_dim}" IS NOT NULL
                            GROUP BY 1
                            ORDER BY churn_rate DESC
                            LIMIT 12
                            """,
                            f"{pri_dim} shows significant variance in customer attrition rate."
                        )

                    if sec_metric and 'tenure' in sec_metric.lower():
                        _try_execute(
                            "Churn Rate by Customer Tenure Cohort",
                            "line",
                            f"""
                            SELECT CAST("{sec_metric}" AS INT) AS tenure_months,
                                   COUNT(*) AS cohort_size,
                                   (AVG(CASE WHEN LOWER(CAST("{t_col}" AS VARCHAR)) IN ('yes', '1', 'true', 'churned') THEN 1.0 ELSE 0.0 END) * 100.0) AS churn_rate
                            FROM {table_ref}
                            WHERE "{sec_metric}" IS NOT NULL
                            GROUP BY 1
                            ORDER BY 1
                            LIMIT 72
                            """,
                            "Early tenure months represent the peak volatility period for churn risk."
                        )

                    if pri_metric:
                        _try_execute(
                            f"Monthly Revenue at Risk by {t_col} Status",
                            "bar",
                            f"""
                            SELECT CAST("{t_col}" AS VARCHAR) AS churn_status,
                                   SUM("{pri_metric}") AS total_revenue_at_risk,
                                   AVG("{pri_metric}") AS avg_ticket
                            FROM {table_ref}
                            WHERE "{pri_metric}" IS NOT NULL
                            GROUP BY 1
                            """,
                            f"Revenue contribution split comparing churned vs retained customers."
                        )

            # -------------------------------------------------------------
            # 2. SPECIALIZED SALES & E-COMMERCE DOMAIN CHARTS
            # -------------------------------------------------------------
            if pri_metric and pri_dim:
                _try_execute(
                    f"Total {pri_metric} by {pri_dim}",
                    "bar",
                    f"""
                    SELECT "{pri_dim}" AS category,
                           SUM("{pri_metric}") AS total_value,
                           AVG("{pri_metric}") AS avg_value,
                           COUNT(*) AS order_volume
                    FROM {table_ref}
                    WHERE "{pri_dim}" IS NOT NULL
                    GROUP BY 1
                    ORDER BY total_value DESC
                    LIMIT 15
                    """,
                    f"{pri_dim} category breakdown highlighting top revenue contribution."
                )

            if pri_metric and sec_metric and pri_dim:
                _try_execute(
                    f"Stacked {pri_metric} & {sec_metric} by {pri_dim}",
                    "stacked_bar",
                    f"""
                    SELECT "{pri_dim}" AS category,
                           SUM("{pri_metric}") AS Total_{pri_metric},
                           SUM("{sec_metric}") AS Total_{sec_metric}
                    FROM {table_ref}
                    WHERE "{pri_dim}" IS NOT NULL AND "{sec_metric}" IS NOT NULL
                    GROUP BY 1
                    ORDER BY Total_{pri_metric} DESC
                    LIMIT 12
                    """,
                    f"Multi-metric stacked breakdown comparing total {pri_metric} and {sec_metric}."
                )

                _try_execute(
                    f"Average {sec_metric} & Total {pri_metric} by {pri_dim}",
                    "bar",
                    f"""
                    SELECT "{pri_dim}" AS category,
                           SUM("{pri_metric}") AS total_primary,
                           AVG("{sec_metric}") AS avg_secondary
                    FROM {table_ref}
                    WHERE "{pri_dim}" IS NOT NULL AND "{sec_metric}" IS NOT NULL
                    GROUP BY 1
                    ORDER BY total_primary DESC
                    LIMIT 12
                    """,
                    f"Comparing primary volume against {sec_metric} profitability margin."
                )


            # -------------------------------------------------------------
            # 3. TEMPORAL TREND & MOMENTUM (Line Chart)
            # -------------------------------------------------------------
            if temporal_col and pri_metric:
                trend_sql = f"""
                SELECT COALESCE(
                           STRFTIME(
                               COALESCE(
                                   TRY_STRPTIME(CAST("{temporal_col}" AS VARCHAR), '%m/%d/%Y'),
                                   TRY_STRPTIME(CAST("{temporal_col}" AS VARCHAR), '%d/%m/%Y'),
                                   TRY_STRPTIME(CAST("{temporal_col}" AS VARCHAR), '%Y-%m-%d'),
                                   TRY_CAST("{temporal_col}" AS TIMESTAMP)
                               ),
                               '%b %Y'
                           ),
                           CAST("{temporal_col}" AS VARCHAR)
                       ) AS date_period,
                       SUM("{pri_metric}") AS metric_sum,
                       AVG("{pri_metric}") AS metric_avg
                FROM {table_ref}
                WHERE "{temporal_col}" IS NOT NULL
                GROUP BY 1, DATE_TRUNC('month', COALESCE(
                    TRY_STRPTIME(CAST("{temporal_col}" AS VARCHAR), '%m/%d/%Y'),
                    TRY_STRPTIME(CAST("{temporal_col}" AS VARCHAR), '%d/%m/%Y'),
                    TRY_STRPTIME(CAST("{temporal_col}" AS VARCHAR), '%Y-%m-%d'),
                    TRY_CAST("{temporal_col}" AS TIMESTAMP)
                ))
                ORDER BY DATE_TRUNC('month', COALESCE(
                    TRY_STRPTIME(CAST("{temporal_col}" AS VARCHAR), '%m/%d/%Y'),
                    TRY_STRPTIME(CAST("{temporal_col}" AS VARCHAR), '%d/%m/%Y'),
                    TRY_STRPTIME(CAST("{temporal_col}" AS VARCHAR), '%Y-%m-%d'),
                    TRY_CAST("{temporal_col}" AS TIMESTAMP)
                )) ASC NULLS LAST
                LIMIT 60
                """
                res = _try_execute(
                    f"{pri_metric} Monthly Trend",
                    "line",
                    trend_sql,
                    f"Monthly trend trajectory showing overall momentum and performance patterns over time."
                )
                if not res:
                    # Fallback simple line query if date parsing fails
                    _try_execute(
                        f"{pri_metric} Over Time",
                        "line",
                        f"""
                        SELECT CAST("{temporal_col}" AS VARCHAR) AS date_period,
                               SUM("{pri_metric}") AS metric_sum,
                               AVG("{pri_metric}") AS metric_avg
                        FROM {table_ref}
                        WHERE "{temporal_col}" IS NOT NULL
                        GROUP BY 1
                        ORDER BY 1
                        LIMIT 60
                        """,
                        f"Temporal trend showing volume momentum over time."
                    )

            # -------------------------------------------------------------
            # 4. SUB-SEGMENT COMPOSITION (Stacked / Donut)
            # -------------------------------------------------------------
            if pri_metric and sec_dim:
                if sec_metric:
                    _try_execute(
                        f"Stacked {pri_metric} & {sec_metric} by {sec_dim}",
                        "stacked_bar",
                        f"""
                        SELECT "{sec_dim}" AS sub_category,
                               SUM("{pri_metric}") AS Total_{pri_metric},
                               SUM("{sec_metric}") AS Total_{sec_metric}
                        FROM {table_ref}
                        WHERE "{sec_dim}" IS NOT NULL AND "{sec_metric}" IS NOT NULL
                        GROUP BY 1
                        ORDER BY Total_{pri_metric} DESC
                        LIMIT 12
                        """,
                        f"Stacked multi-metric comparison across sub-segment {sec_dim}."
                    )

                _try_execute(
                    f"{pri_metric} Breakdown by {sec_dim}",
                    "pie",
                    f"""
                    SELECT "{sec_dim}" AS sub_category,
                           SUM("{pri_metric}") AS total_value,
                           COUNT(*) AS record_count
                    FROM {table_ref}
                    WHERE "{sec_dim}" IS NOT NULL
                    GROUP BY 1
                    ORDER BY total_value DESC
                    LIMIT 10
                    """,
                    f"Sub-segment contribution distribution across {sec_dim}."
                )


            # -------------------------------------------------------------
            # 5. OUTLIER & VALUE DISTRIBUTION SCATTER
            # -------------------------------------------------------------
            if pri_metric and sec_metric:
                _try_execute(
                    f"Distribution Scatter: {pri_metric} vs {sec_metric}",
                    "scatter",
                    f"""
                    SELECT "{pri_metric}" AS x,
                           "{sec_metric}" AS y
                    FROM {table_ref}
                    WHERE "{pri_metric}" IS NOT NULL AND "{sec_metric}" IS NOT NULL
                    LIMIT 250
                    """,
                    f"Scatter plot detailing value correlation and outlier boundary points."
                )

            # -------------------------------------------------------------
            # 6. PARETO 80/20 CUMULATIVE CONCENTRATION
            # -------------------------------------------------------------
            if pri_metric and pri_dim:
                _try_execute(
                    f"Pareto Concentration: {pri_metric} by {pri_dim}",
                    "bar",
                    f"""
                    SELECT "{pri_dim}" AS category,
                           SUM("{pri_metric}") AS category_sum
                    FROM {table_ref}
                    WHERE "{pri_dim}" IS NOT NULL
                    GROUP BY 1
                    ORDER BY category_sum DESC
                    LIMIT 20
                    """,
                    f"Pareto volume ranking identifying top-tier category concentration."
                )

            # -------------------------------------------------------------
            # 7. ADDITIONAL CATEGORICAL & METRIC DENSITY COMBINATIONS
            # -------------------------------------------------------------
            for col in schema:
                if len(charts) >= max_charts:
                    break
                c_name = col['name']
                if c_name in [pri_dim, sec_dim, temporal_col, target_col]:
                    continue
                uniques = col.get('uniques', 0)
                if 2 <= uniques <= 12 and pri_metric:
                    _try_execute(
                        f"{pri_metric} by {c_name}",
                        "bar",
                        f"""
                        SELECT "{c_name}" AS category,
                               SUM("{pri_metric}") AS total_val,
                               COUNT(*) AS count
                        FROM {table_ref}
                        WHERE "{c_name}" IS NOT NULL
                        GROUP BY 1
                        ORDER BY total_val DESC
                        LIMIT 12
                        """,
                        f"Secondary dimension breakdown across {c_name}."
                    )

            logger.info("DomainChartPlanner generated %d active domain charts.", len(charts))
            return charts
        finally:
            if owned_con is not None:
                owned_con.close()
