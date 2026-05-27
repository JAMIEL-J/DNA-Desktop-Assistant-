# skills/data_engine/profiler.py
import logging
import os
from pathlib import Path
import numpy as np
import pandas as pd
import duckdb
from scipy import stats

from config import DATA_ENGINE_SAMPLE_SIZE, DATA_ENGINE_LARGE_THRESHOLD

logger = logging.getLogger('dna.data_engine.profiler')


class DataProfiler:
    """Size-adaptive statistical profiler. DuckDB for I/O, Pandas for stats."""

    LARGE_THRESHOLD = DATA_ENGINE_LARGE_THRESHOLD
    SAMPLE_SIZE = DATA_ENGINE_SAMPLE_SIZE

    def __init__(self):
        self.last_sample_df = None
        self._cached_excel_df = None  # Cache to avoid loading Excel twice
        self.query_log = []

    def profile(self, path: str) -> dict:
        """Generate full statistical profile. Returns structured dict."""
        self.query_log = []
        con = duckdb.connect()
        try:
            # Check if file is Excel
            is_excel = path.lower().endswith(('.xlsx', '.xls'))
            
            # Escape path single quotes for DuckDB
            escaped_path = path.replace("'", "''")
            
            if is_excel:
                logger.info('Excel file detected. Pre-loading with Pandas.')
                df_excel = pd.read_excel(path)
                self._cached_excel_df = df_excel  # Cache for reuse in _load_full/_load_sample
                con.register('data_table', df_excel)
                table_ref = 'data_table'
                row_count = len(df_excel)
            else:
                table_ref = f"read_csv_auto('{escaped_path}')"
                row_count = self._count_rows(con, table_ref)

            logger.info('Profile: %s - Row count: %d', Path(path).name, row_count)
            schema = self._get_schema(con, table_ref, row_count)

            # Determine size strategy
            if row_count <= self.LARGE_THRESHOLD:
                strategy = 'FULL_PANDAS'
                df = self._load_full(con, path, is_excel)
            else:
                if row_count <= 1_000_000:
                    strategy = 'DUCKDB_PRIMARY'
                else:
                    strategy = 'DUCKDB_ONLY'
                df = self._load_sample(con, path, is_excel)

            self.last_sample_df = df

            # Quality metrics
            distinct_count = self._count_distinct_rows(con, table_ref)
            duplicate_count = max(0, row_count - distinct_count)
            duplicate_pct = (duplicate_count / row_count * 100.0) if row_count > 0 else 0.0

            quality_score = self._compute_quality_score(schema, row_count, duplicate_pct)

            numeric_stats = self._numeric_stats(df)
            categorical_stats = self._categorical_stats(df)
            correlations = self._correlations(df)
            null_summary = self._null_summary(con, table_ref, schema)

            profile_data = {
                'file_path': path,
                'row_count': row_count,
                'column_count': len(schema),
                'schema': schema,
                'numeric_stats': numeric_stats,
                'categorical_stats': categorical_stats,
                'correlations': correlations,
                'null_summary': null_summary,
                'quality_score': quality_score,
                'size_strategy': strategy,
            }

            # Run target breakdowns if target column exists
            target_col = self._find_target_column(schema)
            if target_col:
                logger.info('Detected target column for breakdowns: %s', target_col)
                profile_data['target_breakdowns'] = self._run_target_breakdowns(
                    con, table_ref, target_col, schema, row_count
                )
            else:
                profile_data['target_breakdowns'] = None

            return profile_data

        except Exception as e:
            logger.error('Profiling failed: %s', e, exc_info=True)
            # Safe fallback
            return {
                'file_path': path,
                'row_count': 0,
                'column_count': 0,
                'schema': [],
                'numeric_stats': {},
                'categorical_stats': {},
                'correlations': {},
                'null_summary': {},
                'quality_score': 0.0,
                'size_strategy': 'ERROR_FALLBACK',
            }
        finally:
            self._cached_excel_df = None  # Free cached Excel memory
            con.close()

    def _count_rows(self, con, table_ref: str) -> int:
        """DuckDB COUNT — always fast, streams from disk."""
        res = con.execute(f"SELECT COUNT(*) FROM {table_ref}").fetchone()
        return int(res[0]) if res else 0

    def _count_distinct_rows(self, con, table_ref: str) -> int:
        """Count unique rows using standard SQL subquery."""
        try:
            res = con.execute(f"SELECT COUNT(*) FROM (SELECT DISTINCT * FROM {table_ref})").fetchone()
            return int(res[0]) if res else 0
        except Exception:
            return 0

    def _get_schema(self, con, table_ref: str, row_count: int) -> list[dict]:
        """DuckDB DESCRIBE + null counts + unique counts per column."""
        describe_df = con.execute(f"DESCRIBE SELECT * FROM {table_ref} LIMIT 1").fetchdf()
        schema_info = []

        for _, row in describe_df.iterrows():
            col_name = row['column_name']
            col_type = row['column_type']
            quoted_col = f'"{col_name}"'

            try:
                stats_res = con.execute(
                    f"SELECT COUNT({quoted_col}), COUNT(DISTINCT {quoted_col}) FROM {table_ref}"
                ).fetchone()
                non_null_count = stats_res[0] if stats_res else 0
                unique_count = stats_res[1] if stats_res else 0
                null_count = max(0, row_count - non_null_count)
            except Exception as e:
                logger.warning('Failed to fetch stats for column %s: %s', col_name, e)
                null_count = 0
                unique_count = 0

            null_pct = (null_count / row_count * 100.0) if row_count > 0 else 0.0

            schema_info.append({
                'name': col_name,
                'type': col_type,
                'nulls': null_count,
                'null_pct': null_pct,
                'uniques': unique_count
            })

        return schema_info

    def _load_full(self, con, path: str, is_excel: bool) -> pd.DataFrame:
        """Load entire file into Pandas (small files only)."""
        if is_excel:
            if self._cached_excel_df is not None:
                return self._cached_excel_df
            return pd.read_excel(path)
        else:
            return pd.read_csv(path)

    def _load_sample(self, con, path: str, is_excel: bool) -> pd.DataFrame:
        """Sample data using DuckDB or Pandas."""
        if is_excel:
            df = self._cached_excel_df if self._cached_excel_df is not None else pd.read_excel(path)
            return df.sample(n=min(len(df), self.SAMPLE_SIZE), random_state=42)
        else:
            escaped_path = path.replace("'", "''")
            table_ref = f"read_csv_auto('{escaped_path}')"
            return con.execute(f"SELECT * FROM {table_ref} USING SAMPLE {self.SAMPLE_SIZE}").fetchdf()

    def _numeric_stats(self, df: pd.DataFrame) -> dict:
        """mean, median, std, min, max, q1, q3, skewness, kurtosis per numeric col."""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        stats_dict = {}

        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) == 0:
                continue

            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            mean = float(series.mean())
            median = float(series.median())
            std = float(series.std()) if len(series) > 1 else 0.0
            minimum = float(series.min())
            maximum = float(series.max())

            # scipy stats skew and kurtosis
            skewness = float(stats.skew(series)) if len(series) > 2 and std > 0 else 0.0
            kurt = float(stats.kurtosis(series)) if len(series) > 3 and std > 0 else 0.0

            stats_dict[col] = {
                'mean': mean,
                'median': median,
                'std': std,
                'min': minimum,
                'max': maximum,
                'q1': q1,
                'q3': q3,
                'skew': skewness,
                'kurt': kurt
            }

        return stats_dict

    def _categorical_stats(self, df: pd.DataFrame) -> dict:
        """Categorical value counts and cardinality per categorical column."""
        cat_cols = df.select_dtypes(exclude=[np.number]).columns
        stats_dict = {}

        for col in cat_cols:
            series = df[col].dropna()
            cardinality = len(series.unique())
            top_counts = series.value_counts().head(10)
            top_values = {str(k): int(v) for k, v in top_counts.items()}

            stats_dict[col] = {
                'top_values': top_values,
                'cardinality': cardinality
            }

        return stats_dict

    def _correlations(self, df: pd.DataFrame) -> dict:
        """Correlation matrix for numeric columns."""
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.empty or len(numeric_df.columns) < 2:
            return {}
        corr_df = numeric_df.corr().fillna(0.0)
        return corr_df.to_dict()

    def _null_summary(self, con, table_ref: str, schema: list[dict]) -> dict:
        """Summarize null counts from the schema."""
        summary = {}
        for col in schema:
            if col['nulls'] > 0:
                summary[col['name']] = {
                    'null_count': col['nulls'],
                    'null_pct': col['null_pct']
                }
        return summary

    def _compute_quality_score(self, schema: list[dict], row_count: int, duplicate_pct: float) -> float:
        """0-100 score based on nulls and duplicates."""
        if not schema or row_count == 0:
            return 100.0

        total_null_pct = sum(col['null_pct'] for col in schema)
        avg_null_pct = total_null_pct / len(schema)

        # Basic linear penalty: 70% weight to nulls, 30% to duplicates
        score = 100.0 - (0.7 * avg_null_pct) - (0.3 * duplicate_pct)
        return float(max(0.0, min(100.0, score)))

    def _find_target_column(self, schema: list) -> str | None:
        """Find the binary target column from the schema, if any."""
        common_targets = {
            'churn', 'target', 'label', 'class', 'clicked', 'purchased', 'default', 
            'survived', 'status', 'attrition', 'delay', 'delayed', 'late', 'refunded', 
            'returned', 'cancelled', 'inactive', 'fraud', 'terminated', 'left', 
            'churned', 'sold', 'converted', 'subscribed', 'opted_in', 'response', 
            'responded', 'promoted', 'failed', 'failure', 'success', 'high_risk'
        }
        
        # 1. Check 2-unique columns with name match first
        for col in schema:
            name_lower = col['name'].lower()
            if col.get('uniques') == 2:
                if any(t in name_lower for t in common_targets):
                    return col['name']
                    
        # 2. Check any column with exact name match to target keywords
        for col in schema:
            name_lower = col['name'].lower()
            if name_lower in common_targets:
                return col['name']
                
        # 3. Fallback 1: Any column with exactly 2 unique values
        for col in schema:
            if col.get('uniques') == 2:
                return col['name']
                
        # 4. Fallback 2: Any column with 3 unique values
        for col in schema:
            if col.get('uniques') == 3:
                return col['name']
                
        # 5. Fallback 3: Return the last column in the schema
        if schema:
            return schema[-1]['name']
            
        return None

    def _determine_positive_class(self, con, table_ref: str, target_col: str) -> str:
        """Find the value representing the positive outcome (e.g. Yes, True, 1)."""
        try:
            q = f"SELECT DISTINCT \"{target_col}\" FROM {table_ref} WHERE \"{target_col}\" IS NOT NULL LIMIT 10"
            self.query_log.append(("Determine positive class for target", q))
            res = con.execute(q).fetchall()
            values = [str(r[0]) for r in res]
            
            # Look for common positive values
            positive_indicators = {'yes', 'true', '1', 'default', 'churned', 'attrition', 'survived', 'success', 'delay', 'delayed', 'high', 'above_average'}
            for val in values:
                if val.lower() in positive_indicators:
                    return val
            
            # Fallback to the first value that is not 'no', 'false', '0', 'none', 'null', 'low'
            negative_indicators = {'no', 'false', '0', 'none', 'null', 'low'}
            for val in values:
                if val.lower() not in negative_indicators:
                    return val
                    
            # Absolute fallback
            return values[0] if values else "Yes"
        except Exception as e:
            logger.error('Failed to determine positive class: %s', e)
            return "Yes"

    def _run_target_breakdowns(self, con, table_ref: str, target_col: str, schema: list, row_count: int) -> dict:
        """Run DuckDB cross-tabulations and numerical cohort summaries against target."""
        # Check target column uniqueness
        target_uniques = 2
        for col in schema:
            if col['name'] == target_col:
                target_uniques = col.get('uniques', 2)
                break

        active_table = table_ref
        active_target = target_col

        # If target column is not binary (uniques > 2), construct a virtual binarized view!
        if target_uniques > 2:
            is_numeric = False
            for col in schema:
                if col['name'] == target_col:
                    col_type = col['type'].lower()
                    is_numeric = any(t in col_type for t in ['int', 'double', 'float', 'decimal', 'real', 'numeric', 'bigint'])
                    break

            active_target = f"{target_col}_binarized"
            if is_numeric:
                try:
                    mean_res = con.execute(f'SELECT AVG("{target_col}") FROM {table_ref}').fetchone()
                    mean_val = mean_res[0] if mean_res and mean_res[0] is not None else 0.0
                    q_view = f"""
                        CREATE OR REPLACE TEMPORARY VIEW data_table_binarized AS 
                        SELECT *, 
                        CASE WHEN "{target_col}" >= {mean_val} THEN 'High' ELSE 'Low' END AS "{active_target}" 
                        FROM {table_ref}
                    """
                    con.execute(q_view)
                    active_table = "data_table_binarized"
                    logger.info("Binarized numeric target %s around mean %s", target_col, mean_val)
                except Exception as e:
                    logger.error("Failed to binarize numeric target: %s", e)
            else:
                try:
                    freq_res = con.execute(f'SELECT "{target_col}", COUNT(*) as c FROM {table_ref} GROUP BY "{target_col}" ORDER BY c DESC LIMIT 1').fetchone()
                    most_freq = freq_res[0] if freq_res else 'Other'
                    escaped_freq = str(most_freq).replace("'", "''")
                    q_view = f"""
                        CREATE OR REPLACE TEMPORARY VIEW data_table_binarized AS 
                        SELECT *, 
                        CASE WHEN "{target_col}" = '{escaped_freq}' THEN '{escaped_freq}' ELSE 'Other' END AS "{active_target}" 
                        FROM {table_ref}
                    """
                    con.execute(q_view)
                    active_table = "data_table_binarized"
                    logger.info("Binarized categorical target %s using frequent value %s", target_col, most_freq)
                except Exception as e:
                    logger.error("Failed to binarize categorical target: %s", e)

        breakdowns = {
            'target_column': active_target,
            'positive_class': None,
            'baseline_rate': 0.0,
            'categorical': {},
            'numeric': {}
        }
        
        try:
            # 1. Determine positive class
            pos_val = self._determine_positive_class(con, active_table, active_target)
            breakdowns['positive_class'] = pos_val
            
            # 2. Baseline target count and percentage
            escaped_pos_val = pos_val.replace("'", "''")
            q_baseline = f"SELECT COUNT(*), SUM(CASE WHEN \"{active_target}\" = '{escaped_pos_val}' THEN 1 ELSE 0 END) FROM {active_table}"
            self.query_log.append(("Calculate baseline target event rate", q_baseline))
            baseline_res = con.execute(q_baseline).fetchone()
            
            total_rows = baseline_res[0] if baseline_res else row_count
            total_events = baseline_res[1] if baseline_res else 0
            if total_rows > 0:
                breakdowns['baseline_rate'] = (total_events / total_rows) * 100.0
            
            # 3. Categorical cross-tabulations
            for col in schema:
                col_name = col['name']
                if col_name == target_col or col_name == active_target:
                    continue
                
                # Only check columns with low cardinality (between 2 and 12 unique values)
                if 2 <= col['uniques'] <= 12:
                    try:
                        query = f"""
                            SELECT 
                                "{col_name}" AS category,
                                COUNT(*) AS total_count,
                                SUM(CASE WHEN "{active_target}" = '{escaped_pos_val}' THEN 1 ELSE 0 END) AS event_count,
                                (AVG(CASE WHEN "{active_target}" = '{escaped_pos_val}' THEN 1.0 ELSE 0.0 END) * 100) AS event_pct
                            FROM {active_table}
                            GROUP BY "{col_name}"
                            ORDER BY total_count DESC
                        """
                        clean_q = " ".join([line.strip() for line in query.strip().splitlines()])
                        self.query_log.append((f"Cross-tabulation for category '{col_name}' vs target '{active_target}'", clean_q))
                        res_df = con.execute(query).fetchdf()
                        
                        # Add percentage of total events and percentage of total dataset
                        res_df['pct_of_dataset'] = (res_df['total_count'] / total_rows * 100.0) if total_rows > 0 else 0.0
                        res_df['pct_of_total_events'] = (res_df['event_count'] / total_events * 100.0) if total_events > 0 else 0.0
                        
                        breakdowns['categorical'][col_name] = res_df.to_dict(orient='records')
                    except Exception as e:
                        logger.warning('Failed cross-tab for column %s: %s', col_name, e)
            
            # 4. Numeric cohort means
            for col in schema:
                col_name = col['name']
                if col_name == target_col or col_name == active_target:
                    continue
                # If column type is numeric (e.g. contains int, double, float, decimal)
                col_type = col['type'].lower()
                is_num = any(t in col_type for t in ['int', 'double', 'float', 'decimal', 'real', 'numeric'])
                if is_num:
                    try:
                        query = f"""
                            SELECT 
                                "{active_target}" AS target_status,
                                AVG("{col_name}") AS mean_val,
                                COUNT("{col_name}") AS non_null_count
                            FROM {active_table}
                            GROUP BY "{active_target}"
                        """
                        clean_q = " ".join([line.strip() for line in query.strip().splitlines()])
                        self.query_log.append((f"Cohort averages for numeric '{col_name}' vs target '{active_target}'", clean_q))
                        res_df = con.execute(query).fetchdf()
                        breakdowns['numeric'][col_name] = res_df.to_dict(orient='records')
                    except Exception as e:
                        logger.warning('Failed numeric group for column %s: %s', col_name, e)
                        
        except Exception as e:
            logger.error('Error running target breakdowns: %s', e)
            
        return breakdowns
