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

    def profile(self, path: str) -> dict:
        """Generate full statistical profile. Returns structured dict."""
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
