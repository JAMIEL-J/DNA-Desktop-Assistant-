# skills/data_skill.py
# ──────────────────────────────────────────────────────────────────────
# Data Skill — DuckDB + pandas data router (v2)
# Routes >100K row CSVs to DuckDB. Uses NL2SQL and NL2Py.
# ──────────────────────────────────────────────────────────────────────

import logging
import os
import re
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import requests

try:
    import matplotlib.pyplot as plt
except ImportError:
    plt = None

from config import DUCK_PATH, OLLAMA_MODEL, OLLAMA_URL, OLLAMA_TIMEOUT, GOOGLE_API_KEY, CLOUD_LLM_MODEL
from core.session import update as session_update

logger = logging.getLogger('dna.skill.data')


def _extract_code_from_response(raw: str) -> str:
    """Strip LLM reasoning/thinking text and extract only executable code.

    Gemini (and some Ollama models) may prefix the actual code with
    chain-of-thought reasoning (bullet points, analysis, etc.).
    This function strips all of that and returns only the code.
    """
    if not raw:
        return ''

    text = raw.strip()

    # 1. Strip markdown fences (```sql ... ``` or ```python ... ```)
    if text.startswith('```'):
        lines = text.split('\n')
        # Remove opening fence line
        lines = lines[1:]
        # Remove closing fence if present
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines).strip()

    # 2. If there are still markdown fences embedded in the middle, extract them
    fence_match = re.search(r'```(?:sql|python|py)?\s*\n(.*?)```', text, re.DOTALL | re.IGNORECASE)
    if fence_match:
        text = fence_match.group(1).strip()

    # 3. Strip reasoning/thinking lines.
    #    Reasoning lines typically start with: *, -, bullet indentation, or
    #    look like natural-language sentences (contain ":" followed by explanation).
    #    Actual code lines start with SQL keywords or Python variable assignments.
    lines = text.split('\n')
    code_lines = []
    in_code_block = False

    for line in lines:
        stripped = line.strip()

        # Skip empty lines (preserve them only if we're already in code)
        if not stripped:
            if in_code_block:
                code_lines.append(line)
            continue

        # Reasoning indicators: lines starting with *, -, or indented bullets
        if stripped.startswith('*') or stripped.startswith('- '):
            in_code_block = False
            continue

        # Backtick-wrapped inline code at end of reasoning (e.g., `SELECT ...`)
        backtick_match = re.match(r'^`([^`]+)`$', stripped)
        if backtick_match:
            # This is likely the actual code wrapped in backticks
            code_lines = [backtick_match.group(1)]
            in_code_block = True
            continue

        # If line looks like code (starts with SQL keyword, Python assignment,
        # or function call), keep it
        is_code = (
            # SQL patterns
            re.match(r'^(SELECT|INSERT|UPDATE|DELETE|WITH|CREATE|DROP|ALTER|EXPLAIN)\b', stripped, re.IGNORECASE)
            or re.match(r'^(FROM|WHERE|GROUP|ORDER|HAVING|LIMIT|JOIN|UNION|SET)\b', stripped, re.IGNORECASE)
            # Python patterns
            or re.match(r'^[a-zA-Z_]\w*\s*=', stripped)  # variable assignment
            or re.match(r'^(if|for|while|def|class|try|except|return|elif|else:)', stripped)
            or re.match(r'^(result|df|avg|count|num|total|max|min|sum|len)\b', stripped)
            or re.match(r'^[a-zA-Z_]\w*\(', stripped)  # function call
            or re.match(r'^[a-zA-Z_]\w*\[', stripped)  # indexing
        )

        if is_code:
            in_code_block = True
            code_lines.append(line)
        elif in_code_block:
            # If we're in a code block and line doesn't look like reasoning, keep it
            # (could be a continuation line, string, etc.)
            if not (stripped.startswith('*') or stripped.startswith('- ')):
                code_lines.append(line)
        # else: skip reasoning line

    # Deduplicate consecutive identical lines (LLM sometimes echoes the same
    # code both in backtick-wrapped and bare form)
    deduped = []
    for line in code_lines:
        if not deduped or line.strip() != deduped[-1].strip():
            deduped.append(line)
    code_lines = deduped

    result = '\n'.join(code_lines).strip()

    # 4. If extraction produced nothing, fall back to the last non-empty line
    #    (the LLM often puts the final answer at the end)
    if not result:
        for line in reversed(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('*') and not stripped.startswith('-'):
                # Remove surrounding backticks if present
                result = stripped.strip('`').strip()
                break

    return result


def _call_llm_for_code(prompt: str) -> str:
    """Call Google API or Ollama to generate raw SQL or Python code."""
    try:
        # Cloud path
        if GOOGLE_API_KEY:
            import google.generativeai as genai
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel(CLOUD_LLM_MODEL)
            response = model.generate_content(prompt)
            content = response.text.strip()
        else:
            # Local Ollama path
            response = requests.post(
                OLLAMA_URL,
                json={
                    'model': OLLAMA_MODEL,
                    'messages': [{'role': 'user', 'content': prompt}],
                    'stream': False,
                    'options': {'temperature': 0.0},
                },
                timeout=OLLAMA_TIMEOUT,
            )
            response.raise_for_status()
            content = str(response.json().get('message', {}).get('content', '')).strip()

        # Extract only the executable code, stripping any reasoning text
        return _extract_code_from_response(content)
    except Exception as e:
        logger.error('NL2Code generation failed: %s', e)
        return ''


def _get_data_profile(path: str) -> str:
    """Generate a data profile string for LLM context: schema, nulls, sample rows."""
    con = duckdb.connect()
    try:
        # Schema
        schema_df = con.execute(f"DESCRIBE SELECT * FROM read_csv_auto('{path}')").fetchdf()
        columns = list(schema_df['column_name'])
        types = list(schema_df['column_type'])
        schema_str = ", ".join([f"{c} ({t})" for c, t in zip(columns, types)])

        # Row count
        count = con.execute(f"SELECT COUNT(*) FROM read_csv_auto('{path}')").fetchone()[0]

        # Null counts per column
        null_parts = []
        for col in columns:
            nulls = con.execute(
                f"SELECT COUNT(*) FROM read_csv_auto('{path}') WHERE \"{col}\" IS NULL"
            ).fetchone()[0]
            if nulls > 0:
                null_parts.append(f"{col}: {nulls} nulls")
        null_str = ", ".join(null_parts) if null_parts else "No nulls found"

        # Sample rows
        sample_df = con.execute(f"SELECT * FROM read_csv_auto('{path}') LIMIT 3").fetchdf()
        sample_str = sample_df.to_string(index=False)

        profile = (
            f"Rows: {count}\n"
            f"Schema: {schema_str}\n"
            f"Nulls: {null_str}\n"
            f"Sample:\n{sample_str}"
        )
        return profile, count, columns
    finally:
        con.close()


def _summarize_for_voice(question: str, result_df) -> str:
    """Pass a query result through the LLM to get a voice-friendly summary."""
    try:
        table_str = result_df.head(20).to_string(index=False)
        prompt = (
            f"You are a friendly voice assistant. Convert this data result into a short, "
            f"natural-sounding sentence suitable for speaking aloud.\n"
            f"Rules:\n"
            f"- Return ONLY the spoken sentence. No markdown. No backticks. No explanation.\n"
            f"- Keep it short (1-3 sentences max).\n"
            f"- Round numbers to 1 decimal place where appropriate.\n"
            f"- Use natural phrasing like 'about', 'around', 'roughly' for approximate numbers.\n"
            f"- Do NOT read out column headers or raw table formatting.\n\n"
            f"Original question: {question}\n\n"
            f"Data result ({len(result_df)} rows):\n{table_str}"
        )
        summary = _call_llm_for_code(prompt)
        if summary:
            # Clean up any remaining artifacts
            summary = summary.strip().strip('`').strip('"').strip("'")
            logger.info('Voice summary: %s', summary)
            return summary
    except Exception as e:
        logger.warning('Voice summarization failed: %s', e)

    # Fallback: return raw table if summarization fails
    display_res = result_df.head(10).to_string(index=False)
    return f'Here is the result: {display_res}'


def _duckdb_analysis(path: str, question: str, profile: str, columns: list) -> str:
    """Analyze data using DuckDB NL2SQL (priority path)."""
    logger.info('DuckDB NL2SQL analysis: %s', path)
    con = duckdb.connect(str(DUCK_PATH))
    try:
        prompt = (
            f"You are an expert SQL analyst. Generate ONLY a single valid DuckDB SQL query.\n"
            f"Rules:\n"
            f"- Return ONLY raw SQL. No markdown. No backticks. No explanation.\n"
            f"- The table is: read_csv_auto('{path}')\n"
            f"- Always quote column names with double quotes.\n"
            f"- For text comparisons use ILIKE for case-insensitive matching.\n\n"
            f"Data Profile:\n{profile}\n\n"
            f"Question: {question}"
        )

        sql = _call_llm_for_code(prompt)
        if not sql:
            return None  # Signal fallback to pandas

        logger.info('Generated SQL: %s', sql)

        result_df = con.execute(sql).fetchdf()
        session_update('last_df', result_df)

        if result_df.empty:
            return 'The query ran fine but returned no matching data.'

        # Single scalar result — speak directly
        if len(result_df) == 1 and len(result_df.columns) == 1:
            val = result_df.iloc[0, 0]
            return f'The answer is {val}.'

        # Table/multi-column result — summarize for voice
        return _summarize_for_voice(question, result_df)

    except Exception as e:
        logger.warning('DuckDB SQL failed: %s. Falling back to Pandas.', e)
        return None  # Signal fallback
    finally:
        con.close()


def _pandas_analysis(path: str, question: str, ext: str, profile: str) -> str:
    """Fallback: Analyze data using Pandas NL2Py."""
    logger.info('Pandas fallback analysis: %s', path)
    try:
        if ext == '.csv':
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path)

        session_update('last_df', df)

        prompt = (
            f"You are an expert Python data analyst. Generate ONLY executable Python code.\n"
            f"Rules:\n"
            f"- The dataframe is already loaded as `df`.\n"
            f"- Store the final human-readable answer in a variable named `result`.\n"
            f"- `result` must be a short string suitable for voice output.\n"
            f"- Do NOT use print(). Do NOT use markdown. Do NOT use backticks.\n"
            f"- Do NOT use multi-line string literals. Use string concatenation or f-strings only.\n"
            f"- Return ONLY raw Python code, nothing else.\n\n"
            f"Data Profile:\n{profile}\n\n"
            f"Question: {question}"
        )

        code = _call_llm_for_code(prompt)
        if not code:
            return 'Sorry, I could not generate code to answer that.'

        logger.info('Generated Python:\n%s', code)

        # Safety gate
        BLOCKED = ['os.', 'subprocess', 'open(', 'import', '__', 'eval(', 'exec(']
        if any(b in code for b in BLOCKED):
            logger.warning('NL2Py Safety: Blocked unsafe code.')
            return 'The generated code looked unsafe, so I skipped it for safety.'

        namespace = {'df': df, 'pd': pd, 'np': np, 'plt': plt}
        exec(code, namespace, namespace)

        if 'result' in namespace:
            return str(namespace['result'])
        else:
            return 'The analysis finished but did not produce a clear answer.'

    except Exception as e:
        logger.error('Pandas analysis failed: %s', e)
        return 'Sorry, I had trouble analyzing that data. Could you rephrase your question?'


def analyze_data(path: str, question: str) -> str:
    """Analyze a local data file (CSV or Excel). DuckDB first, Pandas fallback."""
    try:
        target = Path(path).resolve()
        if not target.exists():
            return f"Sorry, I can't find that file."

        ext = target.suffix.lower()
        if ext not in ['.csv', '.xlsx', '.xls']:
            return f"I can only analyze CSV and Excel files, not {ext} files."

        # Step 1: Data preparation — profile the dataset
        try:
            profile, count, columns = _get_data_profile(str(target))
            logger.info('Data profiled: %d rows, %d columns', count, len(columns))
        except Exception as e:
            logger.error('Data profiling failed: %s', e)
            return 'Sorry, I had trouble reading that file. It might be corrupted.'

        # Step 2: Try DuckDB NL2SQL first (fast path)
        result = _duckdb_analysis(str(target), question, profile, columns)
        if result is not None:
            return result

        # Step 3: Fallback to Pandas NL2Py
        return _pandas_analysis(str(target), question, ext, profile)

    except Exception as e:
        logger.error('analyze_data failed: %s', e, exc_info=True)
        return 'Sorry, something went wrong while analyzing the data.'


def _search_data_files(keyword: str = "") -> list[Path]:
    """Search common folders AND all drive roots for CSV/Excel files matching a keyword."""
    from config import FOLDER_ALIASES
    import string
    
    valid_exts = {'.csv', '.xlsx', '.xls'}
    candidates = []
    seen = set()
    
    # Build scan list: configured folders + all drive roots
    scan_dirs = []
    
    # 1. Configured folder aliases
    for key in ['downloads', 'desktop', 'documents']:
        p = FOLDER_ALIASES.get(key)
        if p and Path(p).exists():
            scan_dirs.append((Path(p), 1))  # depth 1 = scan direct children only
    
    # 2. Project data folder
    project_data = Path(__file__).parent.parent / 'data'
    if project_data.exists():
        scan_dirs.append((project_data, 1))
    
    # 3. All available drive roots (C:\, D:\, E:\, etc.) — scan 2 levels deep
    for letter in string.ascii_uppercase:
        drive = Path(f'{letter}:\\')
        if drive.exists():
            scan_dirs.append((drive, 2))
    
    def _scan(folder: Path, max_depth: int, current_depth: int = 0):
        if current_depth > max_depth:
            return
        try:
            for f in folder.iterdir():
                if f.is_file() and f.suffix.lower() in valid_exts:
                    resolved = str(f.resolve())
                    if resolved not in seen:
                        seen.add(resolved)
                        candidates.append(f)
                elif f.is_dir() and current_depth < max_depth:
                    # Skip system/hidden folders
                    skip = {'$recycle.bin', 'windows', 'program files', 'program files (x86)', 
                            'programdata', 'appdata', '.git', '__pycache__', 'node_modules', '.venv'}
                    if f.name.lower() not in skip and not f.name.startswith('.'):
                        _scan(f, max_depth, current_depth + 1)
        except (PermissionError, OSError):
            pass
    
    for folder, depth in scan_dirs:
        _scan(folder, depth)
    
    # Filter by keyword if provided
    if keyword:
        kw = keyword.lower().strip()
        # Score matches: exact stem > starts with > contains
        scored = []
        for f in candidates:
            stem = f.stem.lower()
            # Strip all symbols: underscores, hyphens, dots, spaces → plain text
            stem_clean = stem.replace('_', ' ').replace('-', ' ').replace('.', ' ')
            stem_flat = stem_clean.replace(' ', '')
            kw_flat = kw.replace(' ', '')
            
            words = stem_clean.split()
            
            if stem_flat == kw_flat:
                scored.append((0, f))  # Best: exact match
            elif kw in words:
                scored.append((1, f))  # Great: word match
            elif stem_flat.startswith(kw_flat):
                scored.append((2, f))  # Good: starts with
            elif kw_flat in stem_flat:
                scored.append((3, f))  # OK: contains
        scored.sort(key=lambda x: x[0])
        return [f for _, f in scored]
    else:
        # No keyword — return most recent files
        candidates.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        return candidates[:5]


def quick_analyze(question: str = "Give me a summary of this data", keyword: str = "") -> str:
    """Find and analyze a data file. Use keyword to search by filename (e.g. 'churn', 'sales')."""
    matches = _search_data_files(keyword)
    
    if not matches:
        if keyword:
            return f"Sorry, I couldn't find any data file with '{keyword}' in the name on your system."
        return "Sorry, I couldn't find any CSV or Excel files on your system."
    
    chosen = matches[0]
    logger.info('Auto-detected data file: %s (keyword=%s, total_matches=%d)', chosen, keyword, len(matches))
    
    filename = chosen.name
    result = analyze_data(str(chosen), question)
    return f"Found {filename}. {result}"


TOOLS = {
    'analyze_data': analyze_data,
    'quick_analyze': quick_analyze,
}
