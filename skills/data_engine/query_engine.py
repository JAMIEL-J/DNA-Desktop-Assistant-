# skills/data_engine/query_engine.py
import logging
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd

from .llm_utils import _call_llm_for_code

logger = logging.getLogger('dna.data_engine.query_engine')


def _format_profile_for_llm(profile: dict) -> str:
    """Format the profile metadata into a compact string representation with categorical samples."""
    schema_parts = []
    cat_stats = profile.get('categorical_stats', {})
    for col in profile.get('schema', []):
        cname = col['name']
        ctype = col['type']
        if cname in cat_stats and 'top_values' in cat_stats[cname]:
            samples = list(cat_stats[cname]['top_values'].keys())[:5]
            samples_str = f" [sample values: {', '.join(map(str, samples))}]"
            schema_parts.append(f"{cname} ({ctype}){samples_str}")
        else:
            schema_parts.append(f"{cname} ({ctype})")
    schema_str = "\n  - ".join(schema_parts)

    null_parts = []
    for col, stats in profile.get('null_summary', {}).items():
        if stats.get('null_count', 0) > 0:
            null_parts.append(f"{col}: {stats['null_count']} nulls")
    null_str = ", ".join(null_parts) if null_parts else "No nulls"

    return (
        f"Rows: {profile.get('row_count')}\n"
        f"Schema Columns:\n  - {schema_str}\n"
        f"Null Summary: {null_str}\n"
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
                try:
                    con.execute(f"CREATE TEMPORARY VIEW data_table AS SELECT * FROM read_csv_auto('{path_escaped}')")
                except Exception as ex_duck:
                    logger.warning('Standard DuckDB CSV read failed (%s), attempting with ignore_errors and latin1 encoding.', ex_duck)
                    try:
                        con.execute(f"CREATE TEMPORARY VIEW data_table AS SELECT * FROM read_csv_auto('{path_escaped}', ignore_errors=true, encoding='latin1')")
                    except Exception:
                        df_latin = pd.read_csv(path, encoding='latin1', on_bad_lines='skip')
                        con.register("data_table", df_latin)
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
        """Generate SQL query via LLM with multi-turn history context."""
        profile_str = _format_profile_for_llm(profile)
        
        history_ctx = ""
        try:
            from skills.chat_skill import get_history_context
            h = get_history_context(limit=4)
            if h:
                history_ctx = f"Recent Conversation History (Use for resolving follow-up references):\n{h}\n\n"
        except Exception:
            pass

        prompt = (
            f"You are an expert SQL analyst. Generate ONLY a single valid DuckDB SQL query.\n\n"
            f"RULES & DATA TYPE CASTING GUIDELINES:\n"
            f"- Return ONLY raw SQL. No markdown. No backticks. No explanation.\n"
            f"- The table name is always: data_table\n"
            f"- Always quote column names with double quotes to prevent syntax errors (e.g. \"SeniorCitizen\", \"Sales\").\n"
            f"- For text comparisons, use ILIKE for case-insensitive matching.\n"
            f"- If the question is a follow-up, use the conversation history to infer missing target metrics or entities.\n\n"
            f"CRITICAL CASTING RULES FOR ALL DOMAIN DATASETS:\n"
            f"1. BINARY COHORT INDICATORS (0/1 flags like 'SeniorCitizen', 'IsActive', 'HasCrCard', 'Converted', 'Is_*', 'Flag_*'):\n"
            f"   - Count of positive cohort ('count', 'how many', 'total'): Use SUM(CAST(\"col\" AS INTEGER)) OR COUNT(CASE WHEN CAST(\"col\" AS INTEGER) = 1 THEN 1 END).\n"
            f"   - Cohort penetration rate ('percentage', 'rate', 'share'): Use (AVG(CAST(\"col\" AS DOUBLE)) * 100.0).\n"
            f"   - NEVER calculate average when asked for raw count or total count of a binary cohort!\n"
            f"2. NUMERIC COLUMNS STORED AS CURRENCY/STRINGS (e.g. '$1,234.56', '12%'):\n"
            f"   - Strip symbols and cast: TRY_CAST(REGEXP_REPLACE(REGEXP_REPLACE(CAST(\"col\" AS VARCHAR), '[$,%]', ''), ',', '') AS DOUBLE).\n"
            f"3. DATES & YEARS STORED AS STRINGS (e.g. '6/9/2014', '11/8/2016', '2022-05-15'):\n"
            f"   - ALWAYS parse date strings using try_strptime(CAST(\"col\" AS VARCHAR), ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%y'])\n"
            f"   - To extract year: YEAR(try_strptime(CAST(\"col\" AS VARCHAR), ['%m/%d/%Y', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%y'])).\n"
            f"   - NEVER use plain TRY_CAST(\"col\" AS DATE) on 'M/D/YYYY' formatted strings because ISO cast returns NULL for slashed dates!\n"
            f"4. FINANCIAL & BUSINESS METRIC FORMULAS (DATA ANALYST MANDATES):\n"
            f"   - NEVER average pre-computed row margins (e.g. NEVER AVG(Profit/Sales)) or naively divide without zero-guarding!\n"
            f"   - Profit Margin (%) = (SUM(\"Profit\") / NULLIF(SUM(\"Sales\"), 0)) * 100.0\n"
            f"   - Gross Margin (%) = ((SUM(\"Sales\") - SUM(\"COGS\")) / NULLIF(SUM(\"Sales\"), 0)) * 100.0 (or Cost of Goods Sold if present)\n"
            f"   - Average Order Value (AOV) = SUM(\"Sales\") / NULLIF(COUNT(DISTINCT \"Order ID\"), 0)\n"
            f"   - Weighted Discount Rate (%) = (SUM(\"Sales\" * \"Discount\") / NULLIF(SUM(\"Sales\"), 0)) * 100.0\n"
            f"   - Churn Rate (%) = (SUM(CASE WHEN \"Churn\" ILIKE 'True' OR \"Churn\" = '1' THEN 1 ELSE 0 END) * 100.0) / NULLIF(COUNT(*), 0)\n\n"
            f"5. BUSINESS DIAGNOSTIC & ANALYSIS QUESTION GUIDELINES:\n"
            f"   - TREND / FLAT / TRAJECTORY QUESTIONS ('is revenue flat', 'why is sales flat', 'how is revenue growing over time'):\n"
            f"     Extract the date column, group by Year or Year-Month (e.g. YEAR(parsed_date)), calculate Total Revenue/Sales, Total Profit, and Order Count. ORDER BY year/date ASC so temporal trend can be evaluated.\n"
            f"   - CATEGORY & SEGMENT PERFORMANCE ('is the category performing well', 'which category is best/worst'):\n"
            f"     Group by Category or Segment column, calculate SUM(Sales) AS total_sales, SUM(Profit) AS total_profit, Profit Margin %, and COUNT(*) AS order_count. ORDER BY total_sales DESC.\n"
            f"   - ROOT-CAUSE & 'WHY' QUESTIONS ('why did revenue drop', 'what is driving profit'):\n"
            f"     Aggregate primary metrics (Sales, Profit, Margin %) across key breakdown dimensions (Category, Region, Segment) to reveal positive drivers vs negative drag.\n\n"
            f"Data Profile:\n{profile_str}\n\n"
            f"{history_ctx}"
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
            f"- Use TRY_CAST for type conversions.\n"
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
                    try:
                        df = pd.read_csv(path)
                    except Exception:
                        df = pd.read_csv(path, encoding='latin1', on_bad_lines='skip')
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
