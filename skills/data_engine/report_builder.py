import base64
import datetime
import html
import logging
import os
import webbrowser
from pathlib import Path

logger = logging.getLogger('dna.data_engine.report_builder')


def _get_base64_img(path: str) -> str:
    """Read a PNG file and return a base64 encoded data URI."""
    try:
        with open(path, "rb") as image_file:
            encoded = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:image/png;base64,{encoded}"
    except Exception as e:
        logger.warning('Could not base64 encode image %s: %s', path, e)
        return ""


class ReportBuilder:
    """Generates self-contained, beautifully styled HTML dashboards for data analysis reports."""

    def build(self, profile: dict, findings: list[dict],
              insights: dict, chart_paths: list[str],
              history: list[dict], output_path: Path,
              clean_fixes: list[dict] = None) -> str:
        """Build HTML dashboard, write it to output_path/report.html, open browser, and return path."""
        try:
            output_path.mkdir(parents=True, exist_ok=True)
            report_file = output_path / "report.html"

            # 1. Base64 encoding for self-contained charts
            charts_html = ""
            for p in chart_paths:
                b64 = _get_base64_img(p)
                if b64:
                    title = Path(p).stem.replace('_', ' ').title()
                    charts_html += f"""
                    <div class="card chart-card">
                        <div class="card-title" style="margin-bottom: 1rem;">{title}</div>
                        <img src="{b64}" alt="{title}" style="width:100%; border-radius:8px;">
                    </div>
                    """
            if not charts_html:
                charts_html = "<p style='color:#94a3b8; grid-column:1/-1; text-align:center;'>No charts generated.</p>"

            # 2. Format Schema Table Rows
            schema_rows = ""
            total_rows = profile.get('row_count', 1)
            for col in profile.get('schema', []):
                col_name = col['name']
                col_type = col['type']

                # Null counts
                nulls = profile.get('null_summary', {}).get(col_name, {}).get('null_count', 0)
                null_pct = (nulls / total_rows) * 100 if total_rows > 0 else 0

                # Unique counts (stored in schema by profiler's DuckDB COUNT DISTINCT)
                uniques = col.get('uniques', 'N/A')

                schema_rows += f"""
                <tr>
                    <td style="font-weight:600; color:#f8fafc;">{col_name}</td>
                    <td><code style="background:#1e293b; padding:2px 6px; border-radius:4px; color:#38bdf8; font-size:0.85rem;">{col_type}</code></td>
                    <td>{nulls} ({null_pct:.1f}%)</td>
                    <td>{uniques}</td>
                </tr>
                """

            # 3. Format Findings/Anomalies Cards
            findings_html = ""
            for f in findings:
                sev = f.get('severity', 'LOW').upper()
                badge_class = f"badge-{sev.lower()}"
                findings_html += f"""
                <div class="finding-card">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                        <strong style="color:#f8fafc; font-size:1rem;">{f.get('column', 'Dataset')}</strong>
                        <span class="badge {badge_class}">{sev}</span>
                    </div>
                    <p style="margin:0; color:#cbd5e1; font-size:0.9rem;">{f.get('detail', '')}</p>
                </div>
                """
            if not findings_html:
                findings_html = "<p style='color:#94a3b8;'>No anomalies or patterns were detected.</p>"

            # 4. Format Recommendations (handles both string and structured dict formats)
            recs_html = ""
            for rec in insights.get('recommendations', []):
                # Support both flat strings and structured dicts from analyst
                if isinstance(rec, dict):
                    rec_text = rec.get('action', rec.get('recommendation', str(rec)))
                    rationale = rec.get('rationale', '')
                    if rationale:
                        rec_text = f"{rec_text} <span style='color:#94a3b8; font-size:0.85rem;'>— {rationale}</span>"
                else:
                    rec_text = str(rec)
                recs_html += f"""
                <li class="rec-item">
                    <svg class="rec-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"></path>
                    </svg>
                    <span>{rec_text}</span>
                </li>
                """
            if not recs_html:
                recs_html = "<p style='color:#94a3b8;'>No recommendations generated.</p>"

            # 5. Format History Log Items
            history_html = ""
            for h in history:
                timestamp = h.get('timestamp', '')
                query_type = h.get('query_type', 'query').upper()
                sql_tag = ""
                if h.get('generated_sql'):
                    sql_tag = f"""
                    <details style="margin-top:0.5rem; cursor:pointer;">
                        <summary style="font-size:0.8rem; color:#38bdf8;">View SQL Query</summary>
                        <pre style="background:#0f172a; padding:0.5rem; border-radius:4px; overflow-x:auto; font-size:0.8rem; color:#cbd5e1; border:1px solid #334155; margin-top:0.25rem;">{h.get('generated_sql')}</pre>
                    </details>
                    """
                history_html += f"""
                <div class="history-item">
                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:#94a3b8; margin-bottom:0.25rem;">
                        <span>{timestamp}</span>
                        <span class="badge" style="background:#1e293b; color:#94a3b8; border:1px solid #334155; font-size:0.7rem;">{query_type}</span>
                    </div>
                    <div style="font-weight:600; color:#f8fafc; font-size:0.85rem; margin-bottom:0.25rem;">Q: {h.get('question')}</div>
                    <div style="color:#cbd5e1; font-size:0.85rem; margin-bottom:0.25rem;">A: {h.get('result_summary')}</div>
                    {sql_tag}
                </div>
                """
            if not history_html:
                history_html = "<p style='color:#94a3b8;'>No query history recorded for this dataset.</p>"

            # 5b. Format Cleaning Recommendations
            if clean_fixes is None:
                clean_fixes = []
            clean_rows = ""
            for fix in clean_fixes:
                col = fix.get('column', 'Dataset')
                issue_type = fix.get('issue_type', '').replace('_', ' ').title()
                detailed_rec = fix.get('detailed_recommendation', '')
                code_snippet = html.escape(fix.get('code_snippet', ''))
                clean_rows += f"""
                <tr>
                    <td style="font-weight:600; color:#f8fafc;">{col}</td>
                    <td><span class="badge" style="background:#1e293b; color:#38bdf8; border:1px solid #334155; font-size:0.75rem; font-weight:normal; text-transform:none;">{issue_type}</span></td>
                    <td style="color:#cbd5e1; font-size:0.9rem;">{detailed_rec}</td>
                    <td><code style="background:#0f172a; padding:4px 8px; border-radius:4px; color:#ef4444; font-size:0.85rem; border:1px solid #334155; display:block; white-space:pre-wrap;">{code_snippet}</code></td>
                </tr>
                """
            if not clean_rows:
                clean_rows = """
                <tr>
                    <td colspan="4" style="text-align:center; color:#94a3b8;">No data cleaning recommendations needed. Dataset is clean!</td>
                </tr>
                """

            # 6. HTML Template Construction
            filename = Path(profile.get('file_path', 'Unknown')).name
            filepath = profile.get('file_path', 'Unknown')
            quality_score = profile.get('quality_score', 100.0)

            html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DNA Dataset Report — {filename}</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        :root {{
            --bg-main: #0f172a;
            --bg-card: rgba(30, 41, 59, 0.7);
            --border-color: #334155;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --text-muted: #64748b;
            --accent-purple: #8b5cf6;
            --accent-blue: #3b82f6;
            --accent-teal: #06b6d4;
        }}

        body {{
            background-color: var(--bg-main);
            color: #e2e8f0;
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 2rem;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        header {{
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
        }}

        h1, h2, h3 {{
            color: var(--text-primary);
            font-weight: 600;
            margin-top: 0;
        }}

        .header-title {{
            font-size: 2.25rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #a855f7 0%, #3b82f6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .header-meta {{
            font-size: 0.875rem;
            color: var(--text-secondary);
            display: flex;
            gap: 1.5rem;
            flex-wrap: wrap;
        }}

        .header-meta span strong {{
            color: var(--text-primary);
        }}

        .grid-stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }}

        .card {{
            background: var(--bg-card);
            backdrop-filter: blur(8px);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
            transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
        }}

        .card:hover {{
            transform: translateY(-4px);
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
            border-color: #475569;
        }}

        .card-title {{
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            margin-bottom: 0.75rem;
        }}

        .card-value {{
            font-size: 2rem;
            font-weight: 700;
            color: var(--text-primary);
        }}

        .grid-summary {{
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }}

        @media (max-width: 768px) {{
            .grid-summary {{
                grid-template-columns: 1fr;
            }}
        }}

        .executive-summary {{
            font-size: 1.1rem;
            color: #cbd5e1;
        }}

        .recommendation-list {{
            list-style: none;
            padding-left: 0;
            margin: 0;
        }}

        .rec-item {{
            display: flex;
            align-items: flex-start;
            margin-bottom: 0.75rem;
            font-size: 0.95rem;
        }}

        .rec-icon {{
            width: 1.25rem;
            height: 1.25rem;
            color: #10b981;
            margin-right: 0.75rem;
            flex-shrink: 0;
            margin-top: 0.15rem;
        }}

        .badge {{
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 9999px;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
        }}

        .badge-high {{ background-color: #fca5a5; color: #7f1d1d; }}
        .badge-medium {{ background-color: #fde047; color: #713f12; }}
        .badge-low {{ background-color: #86efac; color: #14532d; }}

        .finding-card {{
            border-left: 4px solid var(--border-color);
            background: rgba(30, 41, 59, 0.4);
            padding: 0.75rem 1rem;
            border-radius: 0 8px 8px 0;
            margin-bottom: 1rem;
        }}

        .finding-card:has(.badge-high) {{ border-left-color: #ef4444; }}
        .finding-card:has(.badge-medium) {{ border-left-color: #eab308; }}
        .finding-card:has(.badge-low) {{ border-left-color: #22c55e; }}

        .charts-section {{
            margin-bottom: 2.5rem;
        }}

        .grid-charts {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 1.5rem;
        }}

        @media (max-width: 500px) {{
            .grid-charts {{
                grid-template-columns: 1fr;
            }}
        }}

        .table-wrapper {{
            overflow-x: auto;
            margin-bottom: 2.5rem;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 12px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}

        th, td {{
            padding: 1rem;
            border-bottom: 1px solid var(--border-color);
        }}

        th {{
            background: rgba(15, 23, 42, 0.6);
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 0.85rem;
            text-transform: uppercase;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        tr:hover td {{
            background: rgba(30, 41, 59, 0.5);
        }}

        .history-section {{
            margin-bottom: 2.5rem;
        }}

        .history-wrapper {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }}

        .history-item {{
            background: rgba(30, 41, 59, 0.4);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-title">DNA Dataset Report</div>
            <h2 style="margin: 0 0 1rem 0; font-size: 1.5rem; color: #cbd5e1;">{filename}</h2>
            <div class="header-meta">
                <span>File Path: <strong>{filepath}</strong></span>
                <span>Generated At: <strong>{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</strong></span>
            </div>
        </header>

        <!-- Metrics Block -->
        <section class="grid-stats">
            <div class="card">
                <div class="card-title">Total Rows</div>
                <div class="card-value">{profile.get('row_count', 0):,}</div>
            </div>
            <div class="card">
                <div class="card-title">Total Columns</div>
                <div class="card-value">{profile.get('column_count', 0)}</div>
            </div>
            <div class="card">
                <div class="card-title">Data Quality Score</div>
                <div class="card-value" style="color: {'#10b981' if quality_score >= 85 else '#f59e0b' if quality_score >= 60 else '#f43f5e'};">
                    {quality_score:.1f}%
                </div>
            </div>
        </section>

        <!-- Insights Summary Block -->
        <section class="grid-summary">
            <div class="card" style="display:flex; flex-direction:column; justify-content:space-between;">
                <div>
                    <div class="card-title">Executive Summary</div>
                    <div class="executive-summary">
                        {insights.get('executive_summary', 'No executive summary available.')}
                    </div>
                </div>
                <div style="margin-top: 1.5rem;">
                    <div class="card-title">Recommendations</div>
                    <ul class="recommendation-list">
                        {recs_html}
                    </ul>
                </div>
            </div>
            <div class="card">
                <div class="card-title">Anomalies & Patterns</div>
                <div style="max-height: 320px; overflow-y: auto;">
                    {findings_html}
                </div>
            </div>
        </section>

        <!-- Charts Block -->
        <section class="charts-section">
            <h2 style="margin-bottom: 1.5rem;">Data Visualizations</h2>
            <div class="grid-charts">
                {charts_html}
            </div>
        </section>

        <!-- Data Cleaning Recommendations Block -->
        <section style="margin-bottom: 2.5rem;">
            <h2 style="margin-bottom: 1.5rem;">Data Cleaning & Quality Recommendations</h2>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th style="width: 15%;">Column</th>
                            <th style="width: 15%;">Issue Type</th>
                            <th style="width: 45%;">Detailed Recommendation</th>
                            <th style="width: 25%;">Pandas Code Snippet</th>
                        </tr>
                    </thead>
                    <tbody>
                        {clean_rows}
                    </tbody>
                </table>
            </div>
        </section>

        <!-- Schema Block -->
        <section>
            <h2 style="margin-bottom: 1.5rem;">Data Catalog Schema</h2>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Column Name</th>
                            <th>Data Type</th>
                            <th>Null Values</th>
                            <th>Cardinality (Uniques)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {schema_rows}
                    </tbody>
                </table>
            </div>
        </section>

        <!-- History Log Block -->
        <section class="history-section">
            <h2 style="margin-bottom: 1.5rem;">Analysis History Log</h2>
            <div class="history-wrapper">
                {history_html}
            </div>
        </section>
    </div>
</body>
</html>
"""

            # 7. Write to file
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.info('HTML report written successfully to: %s', report_file)

            # 8. Auto-open report in default web browser
            webbrowser.open(str(report_file.resolve()))

            return str(report_file.resolve())
        except Exception as e:
            logger.error('ReportBuilder failed: %s', e, exc_info=True)
            raise e
