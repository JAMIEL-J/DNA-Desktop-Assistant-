# skills/data_engine/__init__.py
"""DNA Data Engine — Professional data analysis package."""
import datetime
import logging
import os
import re
from pathlib import Path

from config import ANALYSIS_OUTPUT_DIR
from .catalog import DataCatalog
from .profiler import DataProfiler
from .detector import PatternDetector
from .output_router import OutputRouter, OutputMode

logger = logging.getLogger('dna.data_engine')

_catalog = None


def _get_catalog():
    global _catalog
    if _catalog is None:
        _catalog = DataCatalog()
    return _catalog


def _format_profile_for_voice(profile: dict, findings: list[dict]) -> str:
    """Format the profile and findings into a voice-friendly summary."""
    filename = Path(profile.get('file_path', 'unknown')).name
    row_count = profile.get('row_count', 0)
    col_count = profile.get('column_count', 0)
    quality_score = profile.get('quality_score', 100.0)

    summary = (
        f"I have profiled the dataset {filename}. "
        f"It contains {row_count} rows and {col_count} columns, with an overall data quality score of {quality_score:.1f} percent. "
    )

    # Mention target variable if detected
    target_findings = [f for f in findings if f['type'] == 'target_column']
    if target_findings:
        summary += f"The column {target_findings[0]['column']} appears to be the target variable. "

    # Mention other key findings
    other_findings = [f for f in findings if f['type'] != 'target_column']
    if other_findings:
        summary += f"I detected {len(other_findings)} data patterns or issues. "
        high_med_findings = [f for f in other_findings if f['severity'] in ('HIGH', 'MEDIUM')]
        key_findings = high_med_findings if high_med_findings else other_findings
        detail_list = [f['detail'] for f in key_findings[:2]]
        summary += "Key findings: " + "; ".join(detail_list) + "."
    else:
        summary += "No significant anomalies or target variables were detected."

    return summary


def _summarize_for_voice(question: str, result_df) -> str:
    """Pass a query result through the LLM to get a voice-friendly summary."""
    import pandas as pd

    # Check if this is a describe() / summary dataframe
    is_describe = False
    try:
        is_describe = any(x in result_df.index for x in ['count', 'mean', 'min', 'max'])
    except Exception:
        pass

    try:
        show_index = not isinstance(result_df.index, pd.RangeIndex)
        table_str = result_df.head(20).to_string(index=show_index)
        prompt = (
            f"You are Jarvis, an elite executive AI data analyst speaking directly to the user.\n"
            f"Convert this SQL data query result into a clear, precise, and articulate voice response.\n\n"
            f"Mandatory Response Structure:\n"
            f"1. Direct Answer & Executive Assessment:\n"
            f"   - Answer the user's question directly with exact figures formatted with dollar signs (e.g. '$149,528 in Sales and $55,617 in Net Profit').\n"
            f"   - For TREND / TRAJECTORY questions (e.g. 'is revenue flat or increasing?'): Explicitly state the trajectory (e.g., 'Revenue is not flat; it increased 52% from $484K in 2020 to $733K in 2023').\n"
            f"   - For CATEGORY / BUSINESS PERFORMANCE questions (e.g. 'is Technology performing well?'): Evaluate the performance clearly (e.g., 'Technology is the top performing category with $836K in sales and a 17.4% profit margin').\n"
            f"2. Analytical Follow-Up: Always end with 1 proactive follow-up question inviting the user to explore a relevant slice or dimension (e.g., 'Would you like me to break down sales by region or explore category profit margins?').\n\n"
            f"Rules:\n"
            f"- Return ONLY the spoken response. No markdown formatting. No backticks. No raw code.\n"
            f"- Speak naturally and professionally in 2 to 3 sentences.\n\n"
            f"Original Question: {question}\n\n"
            f"SQL Result Data ({len(result_df)} rows):\n{table_str}"
        )
        from .llm_utils import _call_llm_for_code
        summary = _call_llm_for_code(prompt)
        if summary:
            summary = summary.strip().strip('`').strip('"').strip("'")
            logger.info('Voice summary: %s', summary)
            return summary
    except Exception as e:
        logger.warning('Voice summarization failed: %s', e)

    # Programmatic fallback for describe()
    if is_describe:
        try:
            parts = []
            count_val = None
            if 'count' in result_df.index:
                counts = result_df.loc['count'].dropna()
                if not counts.empty:
                    count_val = int(counts.iloc[0])
            
            if count_val is not None:
                parts.append(f"The dataset contains {count_val} rows.")
            else:
                parts.append("Here is a summary of the dataset.")

            for col in result_df.columns:
                col_series = result_df[col]
                # Numeric column summary
                if 'mean' in col_series.index and not pd.isna(col_series.get('mean')):
                    mean_val = col_series['mean']
                    min_val = col_series.get('min', None)
                    max_val = col_series.get('max', None)
                    col_summary = f"For column '{col}', the average is {mean_val:.1f}"
                    if min_val is not None and max_val is not None and not pd.isna(min_val) and not pd.isna(max_val):
                        col_summary += f", ranging from {min_val:.1f} to {max_val:.1f}"
                    col_summary += "."
                    parts.append(col_summary)
                # Categorical column summary
                elif 'unique' in col_series.index and not pd.isna(col_series.get('unique')):
                    uniq_val = int(col_series['unique'])
                    top_val = col_series.get('top', None)
                    col_summary = f"Column '{col}' has {uniq_val} unique values"
                    if top_val is not None and not pd.isna(top_val):
                        col_summary += f", with '{top_val}' being the most common"
                    col_summary += "."
                    parts.append(col_summary)
            
            if parts:
                return " ".join(parts)
        except Exception as ex:
            logger.warning('Programmatic describe fallback failed: %s', ex)

    # Fallback: return raw table if summarization fails
    show_index = not isinstance(result_df.index, pd.RangeIndex)
    display_res = result_df.head(10).to_string(index=show_index)
    return f'Here is the result:\n{display_res}'


def _format_query_log(profiler_queries: list, engine_query: str = None) -> str:
    """Format executed SQL queries into a markdown block."""
    if not profiler_queries and not engine_query:
        return ""
        
    lines = [
        "**📊 Database Queries Run:**",
        "```sql"
    ]
    
    # 1. Profiler queries
    for desc, query in profiler_queries:
        lines.append(f"-- {desc}")
        lines.append(f"{query};\n")
        
    # 2. Engine query
    if engine_query:
        lines.append("-- User Query: Answer specific question")
        lines.append(f"{engine_query};")
        
    lines.append("```\n")
    return "\n".join(lines)


_SIMPLE_Q = re.compile(r'\b(total|sum|average|avg|mean|count|how many|max|maximum|min|minimum|top|highest|lowest|summary|kpi)\b', re.I)
_MONEY_Q = re.compile(r'\b(sales|revenue|profit|price|cost|salary|amount|balance|spend|expense|margin|payment)\b', re.I)


def _fmt_num(value, money: bool) -> str:
    """Human number: commas, $ when the question smells like money."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if money:
        return f"${f:,.0f}" if f.is_integer() else f"${f:,.2f}"
    if f.is_integer():
        return f"{int(f):,}"
    return f"{f:,.2f}"


def _summarize_instant(question: str, result_df) -> str | None:
    """Zero-model-call narration for small factual results (instant lane).

    Returns None when the shape/question needs the LLM narrator.
    """
    try:
        if result_df is None or result_df.empty:
            return None
        if len(result_df) > 12 or result_df.shape[1] > 4:
            return None
        if not _SIMPLE_Q.search(question or ''):
            return None
        money = bool(_MONEY_Q.search(question or ''))
        cols = [str(c).replace('_', ' ') for c in result_df.columns]
        follow = "Want me to slice this another way, boss?"
        if result_df.shape == (1, 1):
            return f"{cols[0]} is {_fmt_num(result_df.iloc[0, 0], money)}, boss. {follow}"
        if len(result_df) == 1:
            bits = [f"{c} {_fmt_num(v, money)}" for c, v in zip(cols, list(result_df.iloc[0]))][:4]
            return f"Here it is, boss: " + ", ".join(bits) + f". {follow}"
        if result_df.shape[1] == 2:
            import pandas as pd
            vals = pd.to_numeric(result_df.iloc[:, 1], errors='coerce')
            if vals.notna().all():
                head = [f"{r.iloc[0]} at {_fmt_num(r.iloc[1], money)}" for _, r in result_df.head(3).iterrows()]
                top0, top1 = result_df.iloc[0].iloc[0], result_df.iloc[0].iloc[1]
                out = f"{top0} leads with {_fmt_num(top1, money)}, boss"
                if len(head) > 1:
                    out += ": " + ", ".join(head[1:])
                if len(result_df) > 1:
                    out += f". Total {_fmt_num(vals.sum(), money)}"
                return out + f". {follow}"
        return None
    except Exception:
        return None


def _strip_export_intent(question: str) -> str:
    """Remove export wording so SQL generation sees the analysis, not the export.

    Without this, 'export avg salary to csv' makes the LLM emit COPY...TO
    STDOUT, which 'runs' but returns a row-count frame — and that count is
    what got saved. (Live export bug, 2026-09-04.)
    """
    q = re.sub(r'\b(export|save|download)\b', '', question or '', flags=re.I)
    q = re.sub(r'\bto\s+(csv|excel|parquet|xlsx|xls|file)\b', '', q, flags=re.I)
    q = re.sub(r'\s+', ' ', q).strip()
    return q or question


def _extractive_summary(profile: dict, findings: list[dict], domain_name: str) -> str:
    """Model-free executive summary from computed stats (local-only deep lane)."""
    rows = profile.get('row_count', 0)
    cols = profile.get('column_count', 0)
    qual = profile.get('quality_score', 0.0)
    top = [f.get('detail', '') for f in (findings or [])[:2] if f.get('detail')]
    text = (f"{domain_name} dataset profiled: {rows:,} rows, {cols} columns, "
            f"quality {qual:.0f} percent, boss. ")
    text += ("Key findings: " + "; ".join(top) + ".") if top else "No major anomalies detected."
    return text


def run_analysis(path: str, question: str, sheet: str | int | None = None) -> str:
    """Full analysis entry point routing requests based on mode (Phase 2 & 3)."""
    logger.info('Running analysis for: %s with question: %s', path, question)

    # Speak verbal status cue to keep user engaged
    try:
        from pipeline.tts import speak
        speak("Running the numbers on the dataset, boss. Crunching the KPIs...")
    except Exception as e:
        logger.debug("TTS status update failed: %s", e)

    # Track the active dataset in session for follow-up routing
    try:
        from core.session import update as session_update
        session_update('active_file', path)
        session_update('active_skill', 'data')
    except Exception:
        pass

    catalog = _get_catalog()
    profiler = DataProfiler()
    detector = PatternDetector()
    router = OutputRouter()

    # 1. Output routing classification (deep intent wins over export wording:
    #    "export a full report" means the report, which lives on disk anyway)
    mode = router.classify(question)

    # 2. Session-cached profile: follow-ups skip re-profiling when the file
    #    hash is unchanged (previously every question paid full profiling).
    from .session import get_session, session_key_for_request
    kernel = get_session(session_key_for_request())
    profile, cache_hit = kernel.get_profile(path, sheet=sheet)
    if cache_hit:
        logger.info('Profile cache hit for %s — skipping re-profile.', Path(path).name)

    # Privacy switch: local-only projects skip cloud even with a key set.
    local_only = False
    try:
        from core.session import get as session_get
        local_only = session_get('local_only', None)
        if local_only is None:
            from pipeline.memory import get_preference
            local_only = get_preference('local_only') == '1'
        local_only = bool(local_only)
        from . import llm_utils as _llu
        _llu.FORCE_LOCAL = local_only
        if local_only:
            logger.info('Local-only mode: cloud LLM disabled for this run.')
    except Exception:
        pass
    findings = detector.detect(profile, kernel.samples.get(path))
    dataset_id = catalog.register_dataset(path, profile)

    # Sheet honesty: say which tab is loaded when workbooks have several.
    sheet_note = ""
    sheets = profile.get('sheets') or []
    if sheets:
        used = profile.get('sheet_used', sheets[0])
        if len(sheets) > 1:
            sheet_note = (f"Note: this workbook has {len(sheets)} tabs "
                          f"({', '.join(sheets[:6])}); I loaded '{used}', boss. ")
    if sheet_note:
        logger.info('Sheet note: %s', sheet_note)

    # 3. Route based on mode
    if mode == OutputMode.VOICE_ONLY:
        from .query_engine import QueryEngine
        engine = QueryEngine()
        res = engine.execute(path, question, profile)
        result_df = res['result_df']
        sql = res.get('sql', '')
        kernel.log_turn(question, sql, len(result_df))

        sampled_note = ""
        if res.get('sampled'):
            sampled_note = " (Based on a 10,000-row sample of the full file, boss.)"

        if result_df.empty:
            result_summary = "The query ran fine but returned no matching data."
        else:
            # Instant lane: small factual results narrate from templates with
            # zero model calls (~1s). Anything richer falls back to the LLM.
            result_summary = _summarize_instant(question, result_df) or \
                _summarize_for_voice(question, result_df)
            result_summary = result_summary.rstrip() + sampled_note

        result_summary = (sheet_note + result_summary) if sheet_note else result_summary
        catalog.log_analysis(
            dataset_id=dataset_id,
            question=question,
            query_type="query",
            result_summary=result_summary,
            generated_sql=sql,
            findings_json=findings
        )
        # Spoken answer first, audit trail after (was reversed: TTS wore the SQL dump).
        query_log_md = _format_query_log(profiler.query_log, sql)
        return f"{result_summary}\n{query_log_md}" if query_log_md else result_summary

    elif mode == OutputMode.DEEP_REPORT:
        from .analyst import DataAnalyst
        from .chart_engine import ChartEngine
        from .report_builder import ReportBuilder
        from .data_cleaner import DataCleaner
        from .semantic_resolver import SemanticColumnResolver
        from .domain_classifier import DomainClassifier
        from .chart_planner import DomainChartPlanner

        def _cue(text):
            try:
                from pipeline.tts import speak
                speak(text)
            except Exception as e:
                logger.debug("Deep progress cue failed: %s", e)

        _cue("Profiled, boss — digging into patterns and drivers.")

        # 1. Semantic Column Resolution
        resolver = SemanticColumnResolver()
        semantics = resolver.resolve(profile.get('schema', []), profiler.last_sample_df)

        # 2. Domain Classification
        classifier = DomainClassifier()
        domain_info = classifier.classify(profile.get('schema', []), semantics)
        profile['domain_info'] = domain_info

        # 3. Analyst insights with domain framing & numerical stats
        analyst = DataAnalyst()
        insights = analyst.analyze(profile, findings, question, domain_info)
        if local_only and insights.get('executive_summary', '').startswith("Data profiled successfully, but detailed"):
            insights['executive_summary'] = _extractive_summary(
                profile, findings, domain_info.get('domain_name', 'Business'))
        _cue("Analysis drafted, boss — building your charts.")

        # 4. Domain-Aware Dynamic SQL Chart Aggregations
        planner = DomainChartPlanner()
        domain_charts = planner.plan_and_execute(
            profiler.con, profiler.table_ref, profile.get('schema', []), semantics, domain_info, profiler.last_sample_df
        )


        _cue("Charts drafted, boss — assembling the dashboard and reports.")

        # 5. Setup output folder
        filename_stem = Path(path).stem
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        output_sub_dir = ANALYSIS_OUTPUT_DIR / f"{filename_stem}_{timestamp}"
        output_sub_dir.mkdir(parents=True, exist_ok=True)

        # 6. Generate static visual chart fallbacks
        chart_engine = ChartEngine()
        chart_paths = chart_engine.generate(profiler.last_sample_df, profile, findings, output_sub_dir)

        # 7. Scan data for quality issues and suggest fixes
        cleaner = DataCleaner()
        clean_issues = cleaner.scan(profiler.last_sample_df, profile)
        clean_fixes = []
        if clean_issues:
            clean_fixes = cleaner.suggest_fixes(clean_issues, profile)

        # 8. Real-time Pipeline Execution Telemetry Trace
        row_cnt = profile.get('row_count', 0)
        col_cnt = profile.get('column_count', 0)
        qual = profile.get('quality_score', 100.0)
        dom_name = domain_info.get('domain_name', 'Enterprise Data')
        conf = domain_info.get('confidence', 0.95)
        target_col = semantics.get('target_col', 'N/A')
        num_findings = len(findings)
        num_drivers = len(insights.get('key_drivers', []))
        num_recs = len(insights.get('recommendations', []))
        num_charts = len(domain_charts)

        now = datetime.datetime.now()
        pipeline_trace = [
            {
                'stage': 'Stage 1: Data Profiling & Schema Inference',
                'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'Completed successfully.',
                'summary': f"Profiled dataset ({row_cnt:,} rows, {col_cnt} columns). Domain classified as '{dom_name}' ({conf:.0%} confidence). Data quality score: {qual:.1f}%."
            },
            {
                'stage': 'Stage 2: Statistical Analysis & Anomaly Engine',
                'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'Completed successfully.',
                'summary': f"Resolved column semantics (Target Variable: '{target_col}'). Detected {num_findings} structural patterns & statistical anomalies. Ingested feature distributions."
            },
            {
                'stage': 'Stage 3: LLM Orchestration & Domain Analyst',
                'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'Completed successfully.',
                'summary': f"Generated narrative 360° executive summary, {num_drivers} strategic risk drivers, and {num_recs} high-priority recommendations via Gemini."
            },
            {
                'stage': 'Stage 4: Dynamic Visualization & Dashboard Build',
                'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
                'status': 'Completed successfully.',
                'summary': f"Executed dynamic SQL aggregations for {num_charts} domain charts. Assembled Finexy single-page Bento dashboard."
            }
        ]
        profile['pipeline_trace'] = pipeline_trace

        # 9. Get query history for the report
        filename = Path(path).name
        history = catalog.get_history(filename)

        # 10. Build and open the HTML dashboard with domain charts
        builder = ReportBuilder()
        report_path = builder.build(
            profile, findings, insights, chart_paths, history, output_sub_dir, clean_fixes, domain_charts
        )

        clean_count = len(clean_issues)
        clean_note = f" I also found {clean_count} data quality issues with cleaning recommendations." if clean_count > 0 else ""
        result_summary = f"I have performed a deep {domain_info['domain_name']} analysis of the dataset and generated {len(domain_charts)} dynamic charts and executive insights. Summary: {insights['executive_summary']}{clean_note}"

        # 11. Companion artifacts: markdown + Excel + rerunnable notebook.
        # Builders never fail the answer — voice delivers regardless.
        try:
            from .artifacts import build_markdown, build_excel, build_notebook
            meta = {'question': question, 'local_only': local_only}
            made = []
            if build_markdown(profile, findings, insights, history, output_sub_dir, meta):
                made.append('markdown')
            if build_excel(profile, findings, insights, chart_paths, history, output_sub_dir):
                made.append('Excel')
            if build_notebook(profile, question, profiler.query_log, history,
                              output_sub_dir, filename=Path(path).name):
                made.append('notebook')
            if made:
                result_summary += f" I also saved {', '.join(made)} reports, boss."
                _cue("Dashboard done, boss — Excel, notebook, and notes saved.")
            else:
                _cue("Dashboard done, boss.")
        except Exception as e:
            logger.warning('Artifact builders failed (voice answer unaffected): %s', e)
            _cue("Dashboard done, boss.")

        catalog.log_analysis(
            dataset_id=dataset_id,
            question=question,
            query_type="report",
            result_summary=result_summary,
            findings_json=findings,
            charts_json=chart_paths,
            report_path=report_path
        )
        query_log_md = _format_query_log(profiler.query_log)
        return f"{result_summary}\n{query_log_md}" if query_log_md else result_summary


    elif mode == OutputMode.EXPORT:
        from .query_engine import QueryEngine
        engine = QueryEngine()
        # Sanitize: generate SQL for the analysis, not the export wording.
        res = engine.execute(path, _strip_export_intent(question), profile)
        result_df = res['result_df']
        sql = res.get('sql', '')
        kernel.log_turn(question, sql, len(result_df))

        if result_df.empty:
            return "The query returned no data to export."

        os.makedirs(ANALYSIS_OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"export_{timestamp}.csv"
        export_path = ANALYSIS_OUTPUT_DIR / export_filename
        result_df.to_csv(export_path, index=False)

        result_summary = f"I have successfully exported the query result to {export_filename}."
        if sheet_note:
            result_summary = sheet_note + result_summary

        catalog.log_analysis(
            dataset_id=dataset_id,
            question=question,
            query_type="export",
            result_summary=result_summary,
            generated_sql=sql,
            report_path=str(export_path.resolve())
        )
        query_log_md = _format_query_log(profiler.query_log, sql)
        return f"{result_summary}\n{query_log_md}" if query_log_md else result_summary

    return "Unknown routing classification."


def run_quick_analysis(question: str, keyword: str = "") -> str:
    """Keyword-based entry. Finds file first, then analyzes."""
    logger.info('Running quick analysis for keyword: %s', keyword)
    catalog = _get_catalog()
    dataset = catalog.find_dataset(keyword)
    if not dataset:
        if keyword:
            return f"Sorry, I couldn't find any data file with '{keyword}' in the name on your system."
        return "Sorry, I couldn't find any CSV, Excel, or Parquet files on your system."

    filename = Path(dataset['file_path']).name
    result = run_analysis(dataset['file_path'], question)
    return f"Found {filename}. {result}"


def recall_recent_data(question: str = "") -> str:
    """Recall the most recently analyzed dataset from persistent history.

    This enables cross-session memory — even after a restart, the user
    can say "open the recent data we analyzed" and resume working.
    """
    logger.info('Recalling recent dataset from catalog')
    catalog = _get_catalog()
    recent = catalog.get_recent_dataset(n=1)

    if not recent:
        return "I don't have any previously analyzed datasets in my memory yet."

    dataset = recent[0]
    file_path = dataset.get('file_path', '')
    file_name = dataset.get('file_name', 'unknown')
    row_count = dataset.get('row_count', 0)
    col_count = dataset.get('column_count', 0)
    analysis_count = dataset.get('analysis_count', 0)
    last_analyzed = dataset.get('last_analyzed', '')

    # Verify the file still exists
    if not Path(file_path).is_file():
        return (
            f"The last dataset I analyzed was {file_name}, "
            f"but the file no longer exists at its original location."
        )

    # Restore active_file in session so follow-ups work
    try:
        from core.session import update as session_update
        session_update('active_file', file_path)
        session_update('active_skill', 'data')
    except Exception:
        pass

    # If user also asked a question, run analysis on the recalled file
    if question and question.strip():
        result = run_analysis(file_path, question)
        return f"Recalled {file_name}. {result}"

    # Otherwise return a summary of the recalled dataset
    friendly_time = ''
    try:
        dt = datetime.datetime.fromisoformat(last_analyzed)
        friendly_time = f" last analyzed on {dt.strftime('%B %d at %I:%M %p')}"
    except Exception:
        pass

    return (
        f"I've recalled {file_name}{friendly_time}. "
        f"It has {row_count} rows and {col_count} columns, "
        f"and has been analyzed {analysis_count} time{'s' if analysis_count != 1 else ''} so far. "
        f"You can now ask me anything about it."
    )


def load_dataset(keyword: str = "") -> str:
    """Load a dataset by keyword using fuzzy matching and set active session context."""
    from .dataset_loader import load_dataset_by_keyword
    return load_dataset_by_keyword(keyword)


def _resolve_one(ref: str) -> str | None:
    """A path stays a path; otherwise resolve via catalog keyword search."""
    ref = (ref or '').strip()
    if not ref:
        return None
    if Path(ref).is_file():
        return str(Path(ref).resolve())
    catalog = _get_catalog()
    hit = catalog.find_dataset(ref)
    return hit['file_path'] if hit else None


def open_datasets(refs: str = "") -> str:
    """Open several datasets into one shared session (joins run across views).

    Args:
        refs: comma-separated file paths or keywords, e.g. "sales.csv, products".
    """
    from .session import get_session, session_key_for_request
    parts = [p.strip() for p in (refs or '').replace(';', ',').split(',') if p.strip()]
    if not parts:
        return "Boss, tell me which datasets to open — separate names with commas."
    kernel = get_session(session_key_for_request())
    opened = []
    for part in parts:
        resolved = _resolve_one(part)
        if not resolved:
            return f"Boss, I couldn't find a dataset for '{part}'."
        info = kernel.open_file(resolved)
        opened.append(f"{Path(resolved).name} as {info['view']}")
    paths = [kernel.views[v] for v in [i.split(' as ')[-1] for i in opened]]
    try:
        from core.session import update as session_update
        session_update('active_files', paths)
        session_update('active_file', paths[0])
    except Exception:
        pass
    keys = kernel.suggest_keys()
    hint = ""
    exact = [k for k in keys if k.get('match') == 'exact']
    if exact:
        hint = " Shared keys I can join on: " + ", ".join(k['key'] for k in exact[:5]) + "."
    return f"Opened {len(opened)}, boss: " + "; ".join(opened) + "." + hint


def suggest_join_keys() -> str:
    """Propose join keys across the open datasets."""
    from .session import get_session, session_key_for_request
    kernel = get_session(session_key_for_request())
    if len(kernel.views) < 2:
        return "Boss, open at least two datasets first, then I'll propose join keys."
    keys = kernel.suggest_keys()
    if not keys:
        return "Boss, I found no shared key names across the open datasets."
    lines = [f"- {k['key']} ({k['match']}): {', '.join(k['refs'])}" for k in keys[:8]]
    return "Candidate join keys, boss:\n" + "\n".join(lines)


def join_datasets(fact: str = "", dim: str = "", fact_key: str = "", dim_key: str = "") -> str:
    """LEFT-join fact to dimension on a key, with grain validation.

    Reports fanout risk and unmatched rows instead of hiding them.
    """
    from .session import get_session, session_key_for_request
    if not (fact and dim and fact_key):
        return "Boss, I need the fact file, the dimension file, and the key — e.g. join sales to products on product id."
    fact_path, dim_path = _resolve_one(fact), _resolve_one(dim)
    if not fact_path:
        return f"Boss, I couldn't find the fact dataset '{fact}'."
    if not dim_path:
        return f"Boss, I couldn't find the dimension dataset '{dim}'."
    kernel = get_session(session_key_for_request())
    f_view = kernel.open_file(fact_path)['view']
    d_view = kernel.open_file(dim_path)['view']
    try:
        rep = kernel.join(f_view, d_view, fact_key, dim_key or None)
    except Exception as e:
        logger.warning('Join failed: %s', e)
        return f"Boss, that join did not run: {str(e)[:200]}"
    out = (f"Joined {Path(fact_path).name} to {Path(dim_path).name} on '{fact_key}', boss: "
           f"{rep['fact_rows']:,} fact rows stayed {rep['joined_rows']:,}; "
           f"{rep['unmatched_fact_rows']:,} found no dimension match. "
           f"Ask me anything across the joined view '{rep['view']}'.")
    if rep.get('warning'):
        out += " Warning: " + rep['warning']
    return out


# Skill module contract
TOOLS = {
    'quick_analyze': run_quick_analysis,
    'analyze_data': run_analysis,
    'recall_data': recall_recent_data,
    'load_dataset': load_dataset,
}
