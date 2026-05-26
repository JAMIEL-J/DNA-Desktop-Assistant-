# skills/data_engine/query_engine.py
import logging
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd

from .llm_utils import _call_llm_for_code

logger = logging.getLogger('dna.data_engine.query_engine')


def _format_profile_for_llm(profile: dict) -> str:
    """Format the profile metadata into a compact string representation."""
    schema_parts = []
    for col in profile.get('schema', []):
        schema_parts.append(f"{col['name']} ({col['type']})")
    schema_str = ", ".join(schema_parts)

    null_parts = []
    for col, stats in profile.get('null_summary', {}).items():
        if stats['null_count'] > 0:
            null_parts.append(f"{col}: {stats['null_count']} nulls")
    null_str = ", ".join(null_parts) if null_parts else "No nulls"

    return (
        f"Rows: {profile.get('row_count')}\n"
        f"Schema: {schema_str}\n"
        f"Nulls: {null_str}\n"
    )


class QueryEngine:
    """NL2SQL (DuckDB) + NL2Py (Pandas) with error recovery loop."""
    MAX_RETRIES = 2

    def __init__(self):
        self._last_error = ""

    def execute(self, path: str, question: str, profile: dict) -> dict:
        """Returns {result_df, sql_used, method: 'duckdb'|'pandas'}."""
        con = duckdb.connect()
        try:
            path_escaped = path.replace("'", "''")
            ext = Path(path).suffix.lower()

            # Register temporary view so NL2SQL queries are format-agnostic
            if ext == '.csv':
                con.execute(f"CREATE TEMPORARY VIEW data_table AS SELECT * FROM read_csv_auto('{path_escaped}')")
            else:
                df_temp = pd.read_excel(path)
                con.register("data_table", df_temp)

            # Attempt 1: Generate SQL -> Execute
            sql = self._generate_sql(question, profile)
            result = self._try_duckdb(con, sql)
            if result is not None:
                return {'result_df': result, 'sql': sql, 'method': 'duckdb'}

            # Attempt 2: Error recovery loop
            for retry in range(self.MAX_RETRIES):
                error_msg = self._last_error
                logger.info('SQL retry %d: feeding back error: %s', retry + 1, error_msg)
                sql = self._regenerate_sql(question, profile, sql, error_msg)
                result = self._try_duckdb(con, sql)
                if result is not None:
                    return {'result_df': result, 'sql': sql, 'method': 'duckdb'}
        except Exception as e:
            logger.error('DuckDB setup/execution failed: %s', e)
            self._last_error = str(e)
        finally:
            con.close()

        # Fallback: Pandas NL2Py
        return self._try_pandas(path, question, profile)

    def _try_duckdb(self, con, sql: str) -> pd.DataFrame | None:
        """Try running a DuckDB SQL statement."""
        if not sql:
            return None
        try:
            logger.info('Running DuckDB SQL:\n%s', sql)
            result_df = con.execute(sql).fetchdf()
            logger.info('DuckDB SQL executed successfully.')
            return result_df
        except Exception as e:
            logger.warning('DuckDB SQL failed: %s', e)
            self._last_error = str(e)
            return None

    def _generate_sql(self, question: str, profile: dict) -> str:
        """Generate SQL query via LLM."""
        profile_str = _format_profile_for_llm(profile)
        prompt = (
            f"You are an expert SQL analyst. Generate ONLY a single valid DuckDB SQL query.\n"
            f"Rules:\n"
            f"- Return ONLY raw SQL. No markdown. No backticks. No explanation.\n"
            f"- The table is always: data_table\n"
            f"- Always quote column names with double quotes to prevent syntax errors.\n"
            f"- For text comparisons, use ILIKE for case-insensitive matching.\n\n"
            f"Data Profile:\n{profile_str}\n\n"
            f"Question: {question}"
        )
        return _call_llm_for_code(prompt)

    def _regenerate_sql(self, question: str, profile: dict, failed_sql: str, error_msg: str) -> str:
        """Regenerate SQL query by incorporating the error feedback."""
        profile_str = _format_profile_for_llm(profile)
        prompt = (
            f"You are an expert SQL analyst. I tried to run the following SQL query and it failed:\n"
            f"Failed SQL: {failed_sql}\n"
            f"Error message: {error_msg}\n\n"
            f"Please generate a corrected valid DuckDB SQL query to answer this question: {question}\n"
            f"Rules:\n"
            f"- Return ONLY raw SQL. No markdown. No backticks. No explanation.\n"
            f"- The table is always: data_table\n"
            f"- Always quote column names with double quotes.\n"
            f"- For text comparisons, use ILIKE.\n\n"
            f"Data Profile:\n{profile_str}"
        )
        return _call_llm_for_code(prompt)

    def _try_pandas(self, path: str, question: str, profile: dict) -> dict:
        """Fallback to Pandas NL2Py if SQL execution fails."""
        logger.info('DuckDB SQL failed or fell back. Attempting Pandas NL2Py.')
        try:
            ext = Path(path).suffix.lower()
            row_count = profile.get('row_count', 0)

            # Size-adaptive Pandas loading
            if row_count <= 100000:
                if ext == '.csv':
                    df = pd.read_csv(path)
                else:
                    df = pd.read_excel(path)
            else:
                logger.warning('Large file detected (%d rows) for Pandas fallback, loading sample.', row_count)
                con = duckdb.connect()
                try:
                    path_escaped = path.replace("'", "''")
                    if ext == '.csv':
                        df = con.execute(f"SELECT * FROM read_csv_auto('{path_escaped}') USING SAMPLE 10000").fetchdf()
                    else:
                        df_full = pd.read_excel(path)
                        df = df_full.sample(n=min(10000, len(df_full)))
                finally:
                    con.close()

            profile_str = _format_profile_for_llm(profile)
            prompt = (
                f"You are an expert Python data analyst. Generate ONLY executable Python code.\n"
                f"Rules:\n"
                f"- The dataframe is already loaded as `df`.\n"
                f"- Store the final result in a variable named `result` (can be a DataFrame, Series, or scalar).\n"
                f"- Do NOT use print(). Do NOT use markdown. Do NOT use backticks.\n"
                f"- Do NOT use multi-line string literals. Use string concatenation or f-strings only.\n"
                f"- Return ONLY raw Python code, nothing else.\n\n"
                f"Data Profile:\n{profile_str}\n\n"
                f"Question: {question}"
            )

            code = _call_llm_for_code(prompt)
            if not code:
                raise ValueError("LLM generated empty Python code")

            logger.info('Generated Python:\n%s', code)

            # Safety gate — block dangerous operations
            BLOCKED_SUBSTRINGS = ['os.', 'subprocess', 'open(', '__', 'eval(', 'exec(']
            if any(b in code for b in BLOCKED_SUBSTRINGS):
                logger.warning('NL2Py Safety: Blocked unsafe code (substring match).')
                raise ValueError("Unsafe python code detected")
            # Block import statements at line level (avoids false positives on column names)
            for line in code.strip().splitlines():
                stripped = line.strip()
                if stripped.startswith('import ') or stripped.startswith('from '):
                    logger.warning('NL2Py Safety: Blocked unsafe import statement.')
                    raise ValueError("Unsafe import detected")

            namespace = {'df': df, 'pd': pd, 'np': np}
            exec(code, namespace, namespace)

            if 'result' in namespace:
                res = namespace['result']
                if isinstance(res, pd.DataFrame):
                    result_df = res
                elif isinstance(res, pd.Series):
                    result_df = res.to_frame()
                else:
                    result_df = pd.DataFrame({'answer': [res]})
                return {'result_df': result_df, 'sql': '', 'method': 'pandas'}
            else:
                raise ValueError("Python code executed but 'result' variable not found")
        except Exception as e:
            logger.error('Pandas analysis failed: %s', e)
            return {'result_df': pd.DataFrame(), 'sql': '', 'method': 'pandas'}
