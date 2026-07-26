# skills/data_engine/__init__.py
"""DNA Data Engine — Professional data analysis package."""
import datetime
import logging
import os
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
            f"1. Direct Answer: Answer the user's question directly with exact values. For monetary values (sales, profit, revenue, charges), format them clearly with dollar amounts (e.g. '$149,528 in Sales and $55,617 in Net Profit').\n"
            f"2. Analytical Follow-Up: Always end with 1 proactive follow-up question inviting the user to explore a relevant slice or dimension (e.g., 'Would you like me to break down sales by region, or explore contract tenure impact?').\n\n"
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


def run_analysis(path: str, question: str) -> str:
    """Full analysis entry point routing requests based on mode (Phase 2 & 3)."""
    logger.info('Running analysis for: %s with question: %s', path, question)

    # Speak verbal status cue to keep user engaged
    try:
        from pipeline.tts import speak
        speak("Running the SQL code for the dataset, sir. Analyzing the KPIs...")
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

    # 1. Output routing classification
    mode = router.classify(question)

    # 2. Setup profile and anomalies
    profile = profiler.profile(path)
    findings = detector.detect(profile, profiler.last_sample_df)
    dataset_id = catalog.register_dataset(path, profile)

    # 3. Route based on mode
    if mode == OutputMode.VOICE_ONLY:
        from .query_engine import QueryEngine
        engine = QueryEngine()
        res = engine.execute(path, question, profile)
        result_df = res['result_df']
        sql = res['sql']

        if result_df.empty:
            result_summary = "The query ran fine but returned no matching data."
        else:
            result_summary = _summarize_for_voice(question, result_df)

        catalog.log_analysis(
            dataset_id=dataset_id,
            question=question,
            query_type="query",
            result_summary=result_summary,
            generated_sql=sql,
            findings_json=findings
        )
        query_log_md = _format_query_log(profiler.query_log, sql)
        return f"{query_log_md}{result_summary}"

    elif mode == OutputMode.DEEP_REPORT:
        from .analyst import DataAnalyst
        from .chart_engine import ChartEngine
        from .report_builder import ReportBuilder
        from .data_cleaner import DataCleaner
        from .semantic_resolver import SemanticColumnResolver
        from .domain_classifier import DomainClassifier
        from .chart_planner import DomainChartPlanner

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

        # 4. Domain-Aware Dynamic SQL Chart Aggregations
        planner = DomainChartPlanner()
        domain_charts = planner.plan_and_execute(
            profiler.con, profiler.table_ref, profile.get('schema', []), semantics, domain_info, profiler.last_sample_df
        )


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
        return f"{query_log_md}{result_summary}"


    elif mode == OutputMode.EXPORT:
        from .query_engine import QueryEngine
        engine = QueryEngine()
        res = engine.execute(path, question, profile)
        result_df = res['result_df']
        sql = res['sql']

        if result_df.empty:
            return "The query returned no data to export."

        os.makedirs(ANALYSIS_OUTPUT_DIR, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"export_{timestamp}.csv"
        export_path = ANALYSIS_OUTPUT_DIR / export_filename
        result_df.to_csv(export_path, index=False)

        result_summary = f"I have successfully exported the query result to {export_filename}."

        catalog.log_analysis(
            dataset_id=dataset_id,
            question=question,
            query_type="export",
            result_summary=result_summary,
            generated_sql=sql,
            report_path=str(export_path.resolve())
        )
        query_log_md = _format_query_log(profiler.query_log, sql)
        return f"{query_log_md}{result_summary}"

    return "Unknown routing classification."


def run_quick_analysis(question: str, keyword: str = "") -> str:
    """Keyword-based entry. Finds file first, then analyzes."""
    logger.info('Running quick analysis for keyword: %s', keyword)
    catalog = _get_catalog()
    dataset = catalog.find_dataset(keyword)
    if not dataset:
        if keyword:
            return f"Sorry, I couldn't find any data file with '{keyword}' in the name on your system."
        return "Sorry, I couldn't find any CSV or Excel files on your system."

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


# Skill module contract
TOOLS = {
    'quick_analyze': run_quick_analysis,
    'analyze_data': run_analysis,
    'recall_data': recall_recent_data,
    'load_dataset': load_dataset,
}
