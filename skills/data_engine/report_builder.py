import datetime
import html
import json
import logging
import webbrowser
from pathlib import Path

logger = logging.getLogger('dna.data_engine.report_builder')


class ReportBuilder:
    """Generates self-contained, beautifully styled, interactive HTML/Plotly dashboards."""

    def build(self, profile: dict, findings: list[dict],
              insights: dict, chart_paths: list[str],
              history: list[dict], output_path: Path,
              clean_fixes: list[dict] = None) -> str:
        """Build HTML dashboard, write it to output_path/report.html, open browser, and return path."""
        try:
            output_path.mkdir(parents=True, exist_ok=True)
            report_file = output_path / "report.html"

            # 1. Format Schema Table Rows
            schema_rows = ""
            total_rows = profile.get('row_count', 1)
            for col in profile.get('schema', []):
                col_name = col['name']
                col_type = col['type']

                # Null counts
                nulls = profile.get('null_summary', {}).get(col_name, {}).get('null_count', 0)
                null_pct = (nulls / total_rows) * 100 if total_rows > 0 else 0

                # Unique counts
                uniques = col.get('uniques', 'N/A')

                schema_rows += f"""
                <tr>
                    <td style="font-weight:600; color:#f9fafb;">{col_name}</td>
                    <td><code style="background:#111827; padding:2px 6px; border-radius:4px; color:#3b82f6; font-size:0.85rem;">{col_type}</code></td>
                    <td>{nulls} ({null_pct:.1f}%)</td>
                    <td>{uniques}</td>
                </tr>
                """

            # 2. Format Core KPIs Section
            kpis_html = ""
            for kpi in insights.get('kpis', []):
                label = kpi.get('label', '')
                value = kpi.get('value', '')
                detail = kpi.get('detail', '')
                kpis_html += f"""
                <div style="border-left:4px solid var(--accent-purple); padding:0.5rem 1rem; background:rgba(17, 24, 39, 0.3); border-radius:0 8px 8px 0; margin-bottom: 0.75rem;">
                    <div style="font-size:0.75rem; text-transform:uppercase; color:var(--text-secondary); font-weight:700; letter-spacing:0.05em;">{label}</div>
                    <div style="font-size:1.5rem; font-weight:700; color:var(--text-primary); margin:0.15rem 0;">{value}</div>
                    <div style="font-size:0.875rem; color:#cbd5e1; line-height:1.4;">{detail}</div>
                </div>
                """
            if not kpis_html:
                kpis_html = "<p style='color:#9ca3af;'>No core KPIs available.</p>"

            # 3. Format Key Drivers / Triggers
            drivers_html = ""
            for drv in insights.get('drivers', []):
                num = drv.get('trigger_number', '')
                emoji = drv.get('emoji', '🚨')
                title = drv.get('title', '')
                subtitle = drv.get('subtitle', '')
                stats = drv.get('statistics', [])
                insight = drv.get('business_insight', '')
                
                stats_list = "".join(f"<li style='margin-bottom:0.4rem;'>{s}</li>" for s in stats)
                severity = drv.get('severity', 'HIGH').upper()
                badge_class = f"badge-{severity.lower()}"
                
                drivers_html += f"""
                <div class="card" style="border-left: 5px solid {'#ef4444' if severity == 'HIGH' else '#f59e0b' if severity == 'MEDIUM' else '#10b981'}; margin-bottom: 1.25rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem; flex-wrap:wrap; gap:0.5rem;">
                        <h3 style="margin:0; font-size:1.15rem; color:var(--text-primary); font-family:'Outfit', sans-serif;">
                            {emoji} Trigger #{num}: {title} <span style="font-weight:normal; font-size:0.9rem; color:var(--text-secondary);">({subtitle})</span>
                        </h3>
                        <span class="badge {badge_class}">{severity}</span>
                    </div>
                    <ul style="margin: 0 0 1rem 0; padding-left: 1.25rem; color:#cbd5e1; font-size:0.925rem; line-height:1.5;">
                        {stats_list}
                    </ul>
                    <div style="background:rgba(15, 23, 42, 0.4); padding:0.75rem 1rem; border-radius:8px; border-left:3px solid var(--accent-teal); font-size:0.9rem; line-height:1.5;">
                        <strong>Business Insight:</strong> <span style="color:#cbd5e1;">{insight}</span>
                    </div>
                </div>
                """
            if not drivers_html:
                drivers_html = "<p style='color:#9ca3af;'>No drivers reported.</p>"

            # 4. Format Perfect Storm Segments
            ps_html = ""
            for seg in insights.get('perfect_storm_segments', []):
                segment = seg.get('segment', '')
                tot = seg.get('total_customers', '')
                rate = seg.get('rate', '')
                ins = seg.get('business_insight', '')
                
                ps_html += f"""
                <tr>
                    <td style="font-weight:600; color:#f9fafb; font-size:0.95rem;">{segment}</td>
                    <td>{tot}</td>
                    <td style="font-weight:700; color:#f87171; font-size:0.95rem;">{rate}</td>
                    <td style="color:#cbd5e1; font-size:0.9rem; line-height:1.5;"><strong>Business Insight:</strong> {ins}</td>
                </tr>
                """
            if not ps_html:
                ps_html = "<tr><td colspan='4' style='text-align:center; color:#9ca3af;'>No segments reported.</td></tr>"

            # 5. Format Strategic Recommendations
            recs_html = ""
            for rec in insights.get('recommendations', []):
                title = rec.get('title', '')
                action = rec.get('action', '')
                rationale = rec.get('rationale', '')
                
                recs_html += f"""
                <div class="card" style="border-top: 4px solid var(--accent-teal); display:flex; flex-direction:column; justify-content:space-between; height:100%; box-sizing:border-box;">
                    <div>
                        <h4 style="margin:0 0 0.5rem 0; color:var(--text-primary); font-size:1.05rem; font-family:'Outfit', sans-serif;">{title}</h4>
                        <p style="margin:0 0 0.75rem 0; color:#cbd5e1; font-size:0.9rem; line-height:1.5;"><strong>Action:</strong> {action}</p>
                    </div>
                    <p style="margin:0; color:var(--text-secondary); font-size:0.85rem; line-height:1.4; border-top:1px solid var(--border-color); padding-top:0.5rem;"><strong>Rationale:</strong> {rationale}</p>
                </div>
                """
            if not recs_html:
                recs_html = "<p style='color:#9ca3af;'>No recommendations generated.</p>"

            # 6. Format History Log Items
            history_html = ""
            for h in history:
                timestamp = h.get('timestamp', '')
                query_type = h.get('query_type', 'query').upper()
                sql_tag = ""
                if h.get('generated_sql'):
                    sql_tag = f"""
                    <details style="margin-top:0.5rem; cursor:pointer;">
                        <summary style="font-size:0.8rem; color:#3b82f6;">View SQL Query</summary>
                        <pre style="background:#111827; padding:0.5rem; border-radius:4px; overflow-x:auto; font-size:0.8rem; color:#cbd5e1; border:1px solid #1f2937; margin-top:0.25rem;">{h.get('generated_sql')}</pre>
                    </details>
                    """
                history_html += f"""
                <div class="history-item">
                    <div style="display:flex; justify-content:space-between; font-size:0.8rem; color:#9ca3af; margin-bottom:0.25rem;">
                        <span>{timestamp}</span>
                        <span class="badge" style="background:#111827; color:#9ca3af; border:1px solid #1f2937; font-size:0.7rem;">{query_type}</span>
                    </div>
                    <div style="font-weight:600; color:#f9fafb; font-size:0.85rem; margin-bottom:0.25rem;">Q: {h.get('question')}</div>
                    <div style="color:#cbd5e1; font-size:0.85rem; margin-bottom:0.25rem;">A: {h.get('result_summary')}</div>
                    {sql_tag}
                </div>
                """
            if not history_html:
                history_html = "<p style='color:#9ca3af;'>No query history recorded for this dataset.</p>"

            # 7. Format Cleaning Recommendations
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
                    <td style="font-weight:600; color:#f9fafb;">{col}</td>
                    <td><span class="badge" style="background:#111827; color:#14b8a6; border:1px solid #1f2937; font-size:0.75rem; font-weight:normal; text-transform:none;">{issue_type}</span></td>
                    <td style="color:#cbd5e1; font-size:0.9rem;">{detailed_rec}</td>
                    <td><code style="background:#111827; padding:4px 8px; border-radius:4px; color:#ef4444; font-size:0.85rem; border:1px solid #1f2937; display:block; white-space:pre-wrap;">{code_snippet}</code></td>
                </tr>
                """
            if not clean_rows:
                clean_rows = """
                <tr>
                    <td colspan="4" style="text-align:center; color:#9ca3af;">No data cleaning recommendations needed. Dataset is clean!</td>
                </tr>
                """

            filename = Path(profile.get('file_path', 'Unknown')).name
            filepath = profile.get('file_path', 'Unknown')
            quality_score = profile.get('quality_score', 100.0)

            # Replace-based HTML generation to prevent f-string parser collision with JS/CSS braces
            html_content = HTML_TEMPLATE
            html_content = html_content.replace("__FILENAME__", filename)
            html_content = html_content.replace("__FILEPATH__", filepath)
            html_content = html_content.replace("__GENERATED_AT__", datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            html_content = html_content.replace("__ROW_COUNT__", f"{profile.get('row_count', 0):,}")
            html_content = html_content.replace("__COLUMN_COUNT__", str(profile.get('column_count', 0)))
            html_content = html_content.replace("__QUALITY_SCORE__", f"{quality_score:.1f}%")
            html_content = html_content.replace("__QUALITY_COLOR__", '#10b981' if quality_score >= 85 else '#f59e0b' if quality_score >= 60 else '#f43f5e')
            html_content = html_content.replace("__EXECUTIVE_SUMMARY__", insights.get('executive_summary', 'No executive summary available.'))
            html_content = html_content.replace("__KPI_CARDS_HTML__", kpis_html)
            html_content = html_content.replace("__DRIVERS_HTML__", drivers_html)
            html_content = html_content.replace("__PERFECT_STORM_ROWS_HTML__", ps_html)
            html_content = html_content.replace("__RECOMMENDATIONS_HTML__", recs_html)
            html_content = html_content.replace("__CLEAN_ROWS__", clean_rows)
            html_content = html_content.replace("__SCHEMA_ROWS__", schema_rows)
            html_content = html_content.replace("__HISTORY_HTML__", history_html)

            # Inject serializable JSON profile data
            html_content = html_content.replace("__PROFILE_DATA_JSON__", json.dumps(profile))
            html_content = html_content.replace("__INSIGHTS_DATA_JSON__", json.dumps(insights))

            # Write to file
            with open(report_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.info('HTML/Plotly report written successfully to: %s', report_file)
            webbrowser.open(str(report_file.resolve()))

            return str(report_file.resolve())
        except Exception as e:
            logger.error('ReportBuilder failed: %s', e, exc_info=True)
            raise e


# State-of-the-art interactive template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DNA Dataset Report — __FILENAME__</title>
    
    <!-- Plotly Core JS -->
    <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
    
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700&family=Inter:wght@300;400;500;600;700&display=swap');
        
        :root {
            --bg-main: #0b0f19;
            --bg-card: rgba(17, 24, 39, 0.7);
            --bg-card-hover: rgba(31, 41, 55, 0.85);
            --border-color: #1f2937;
            --border-color-hover: #374151;
            --text-primary: #f9fafb;
            --text-secondary: #9ca3af;
            --text-muted: #6b7280;
            --accent-purple: #8b5cf6;
            --accent-blue: #3b82f6;
            --accent-teal: #14b8a6;
        }

        body {
            background-color: var(--bg-main);
            color: #d1d5db;
            font-family: 'Inter', sans-serif;
            margin: 0;
            padding: 2rem;
            line-height: 1.6;
        }

        .container {
            max-width: 1280px;
            margin: 0 auto;
        }

        header {
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 2rem;
            margin-bottom: 2.5rem;
        }

        h1, h2, h3, h4 {
            font-family: 'Outfit', sans-serif;
            color: var(--text-primary);
            font-weight: 700;
            margin-top: 0;
        }

        .header-title {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #a855f7 0%, #3b82f6 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .header-meta {
            font-size: 0.9rem;
            color: var(--text-secondary);
            display: flex;
            gap: 2rem;
            flex-wrap: wrap;
        }

        .header-meta span strong {
            color: var(--text-primary);
        }

        .grid-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }

        .card {
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.75rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
        }

        .card:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.4);
            border-color: var(--border-color-hover);
            background: var(--bg-card-hover);
        }

        .card-title {
            font-size: 0.85rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-secondary);
            margin-bottom: 0.75rem;
        }

        .card-value {
            font-size: 2.25rem;
            font-weight: 700;
            color: var(--text-primary);
        }

        .grid-summary {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }

        @media (max-width: 900px) {
            .grid-summary {
                grid-template-columns: 1fr;
            }
        }

        .executive-summary {
            font-size: 1.05rem;
            color: #cbd5e1;
            line-height: 1.7;
        }

        .badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .badge-high { background-color: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.4); }
        .badge-medium { background-color: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.4); }
        .badge-low { background-color: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }

        .grid-charts {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(480px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2.5rem;
        }

        @media (max-width: 600px) {
            .grid-charts {
                grid-template-columns: 1fr;
            }
        }

        .table-wrapper {
            overflow-x: auto;
            margin-bottom: 2.5rem;
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 16px;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }

        th, td {
            padding: 1.25rem;
            border-bottom: 1px solid var(--border-color);
        }

        th {
            background: rgba(17, 24, 39, 0.8);
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr:hover td {
            background: rgba(31, 41, 55, 0.4);
        }

        .history-wrapper {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            margin-bottom: 2.5rem;
        }

        .history-item {
            background: rgba(17, 24, 39, 0.4);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.25rem;
        }

        select, input {
            background: #111827;
            color: #f9fafb;
            border: 1px solid #1f2937;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 0.95rem;
            outline: none;
            cursor: pointer;
            font-family: 'Inter', sans-serif;
            transition: border-color 0.2s, box-shadow 0.2s;
        }

        select:hover, input:hover {
            border-color: #374151;
        }

        select:focus, input:focus {
            border-color: var(--accent-purple);
            box-shadow: 0 0 0 2px rgba(139, 92, 246, 0.2);
        }

        .chart-controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .no-target-alert {
            background: rgba(245, 158, 11, 0.1);
            border: 1px solid rgba(245, 158, 11, 0.3);
            border-radius: 12px;
            padding: 1.5rem;
            color: #fbbf24;
            margin-bottom: 2.5rem;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="header-title">DNA Business Intelligence Dashboard</div>
            <h2 style="margin: 0 0 1.25rem 0; font-size: 1.75rem; color: #f3f4f6;">__FILENAME__</h2>
            <div class="header-meta">
                <span>File Path: <strong>__FILEPATH__</strong></span>
                <span>Generated At: <strong>__GENERATED_AT__</strong></span>
            </div>
        </header>

        <!-- Base Metrics Stat Block -->
        <section class="grid-stats">
            <div class="card">
                <div class="card-title">Total Records Analyzed</div>
                <div class="card-value">__ROW_COUNT__</div>
            </div>
            <div class="card">
                <div class="card-title">Total Feature Columns</div>
                <div class="card-value">__COLUMN_COUNT__</div>
            </div>
            <div class="card">
                <div class="card-title">Dataset Health Score</div>
                <div class="card-value" style="color: __QUALITY_COLOR__;">__QUALITY_SCORE__</div>
            </div>
        </section>

        <!-- 1. Executive Summary & Core KPI -->
        <section style="margin-bottom: 3rem;">
            <h2 style="font-size: 1.6rem; border-left: 5px solid var(--accent-purple); padding-left: 0.75rem; margin-bottom: 1.5rem;">1. Executive Summary & Core KPI</h2>
            <div class="grid-summary">
                <div class="card">
                    <div class="card-title" style="color: var(--accent-purple);">Executive Summary</div>
                    <div class="executive-summary">
                        __EXECUTIVE_SUMMARY__
                    </div>
                </div>
                <div class="card" style="display:flex; flex-direction:column; justify-content:flex-start;">
                    <div class="card-title" style="color: var(--accent-purple);">Core KPIs</div>
                    <div style="display:flex; flex-direction:column; flex:1; justify-content:center;">
                        __KPI_CARDS_HTML__
                    </div>
                </div>
            </div>
        </section>

        <!-- 2. Key Drivers (Uncovered by Numbers) -->
        <section style="margin-bottom: 3rem;">
            <h2 style="font-size: 1.6rem; border-left: 5px solid #ef4444; padding-left: 0.75rem; margin-bottom: 1.5rem;">2. Key Churn Drivers (Uncovered by Numbers)</h2>
            <div style="display:flex; flex-direction:column;">
                __DRIVERS_HTML__
            </div>
        </section>

        <!-- 3. High-Volatility Customer Segment (The "Perfect Storm") -->
        <section style="margin-bottom: 3rem;" id="perfect-storm-section">
            <h2 style="font-size: 1.6rem; border-left: 5px solid var(--accent-blue); padding-left: 0.75rem; margin-bottom: 1.5rem;">3. High-Volatility Customer Segment (The "Perfect Storm")</h2>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th style="width: 25%;">Segment</th>
                            <th style="width: 15%;">Total Customers</th>
                            <th style="width: 15%;">Churn/Event Rate</th>
                            <th style="width: 45%;">Business Insight</th>
                        </tr>
                    </thead>
                    <tbody>
                        __PERFECT_STORM_ROWS_HTML__
                    </tbody>
                </table>
            </div>
        </section>

        <!-- 4. Strategic Churn Mitigation Recommendations -->
        <section style="margin-bottom: 3rem;">
            <h2 style="font-size: 1.6rem; border-left: 5px solid var(--accent-teal); padding-left: 0.75rem; margin-bottom: 1.5rem;">4. Strategic Churn Mitigation Recommendations</h2>
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap:1.5rem;">
                __RECOMMENDATIONS_HTML__
            </div>
        </section>

        <!-- Target Breakdown Charts section -->
        <section id="target-charts-section" style="display:none; margin-bottom: 3rem;">
            <h2 style="font-size: 1.6rem; border-left: 5px solid var(--accent-purple); padding-left: 0.75rem; margin-bottom: 1.5rem;">Interactive Target Drivers & Cohort Profiles</h2>
            <div class="grid-charts">
                <!-- Categorical drivers -->
                <div class="card">
                    <div class="chart-controls">
                        <div class="card-title" style="margin-bottom:0;">Categorical Feature Breakdown</div>
                        <select id="categorical-select"></select>
                    </div>
                    <div id="plotly-categorical" style="height: 400px; width: 100%;"></div>
                </div>
                
                <!-- Numeric drivers -->
                <div class="card">
                    <div class="chart-controls">
                        <div class="card-title" style="margin-bottom:0;">Numeric Feature Cohort Means</div>
                        <select id="numeric-select"></select>
                    </div>
                    <div id="plotly-numeric" style="height: 400px; width: 100%;"></div>
                </div>
            </div>
            
            <div class="grid-charts">
                <!-- Heatmap -->
                <div class="card" style="grid-column: 1 / -1;">
                    <div class="card-title">Feature Correlations Matrix</div>
                    <div id="plotly-heatmap" style="height: 500px; width: 100%;"></div>
                </div>
            </div>
        </section>

        <!-- Target Cohorts Table -->
        <section id="target-table-section" style="display:none; margin-bottom: 3rem;">
            <div class="chart-controls" style="margin-bottom: 1.5rem;">
                <h2 style="font-size: 1.6rem; border-left: 5px solid var(--accent-teal); padding-left: 0.75rem; margin-bottom: 0;">🎯 Cohort Analysis & Cross-Tabulations Table</h2>
                <input type="text" id="cohort-table-search" placeholder="Search cohorts...">
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Feature Column</th>
                            <th>Cohort Value</th>
                            <th>Cohort Count</th>
                            <th>Cohort Share of Dataset (%)</th>
                            <th>Event Count</th>
                            <th>Cohort Event Rate (%)</th>
                            <th>Contribution to Total Events (%)</th>
                        </tr>
                    </thead>
                    <tbody id="cohort-table-body">
                        <!-- Filled by JS -->
                    </tbody>
                </table>
            </div>
        </section>

        <div id="no-target-alert-box" class="no-target-alert" style="display:none;">
            <strong>Target Variable Warning:</strong> No binary target variable (e.g. churn, default) was found in this dataset. Advanced target breakdowns and cohort charts are disabled.
        </div>

        <!-- Data Cleaning Recommendations Block -->
        <section style="margin-bottom: 3rem;">
            <h2 style="font-size: 1.6rem; border-left: 5px solid #ef4444; padding-left: 0.75rem; margin-bottom: 1.5rem;">Data Cleaning & Quality Recommendations</h2>
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
                        __CLEAN_ROWS__
                    </tbody>
                </table>
            </div>
        </section>

        <!-- Schema Block -->
        <section style="margin-bottom: 3rem;">
            <div class="chart-controls" style="margin-bottom: 1.5rem;">
                <h2 style="font-size: 1.6rem; border-left: 5px solid var(--text-secondary); padding-left: 0.75rem; margin-bottom: 0;">Data Catalog Schema</h2>
                <input type="text" id="schema-table-search" placeholder="Search schema...">
            </div>
            <div class="table-wrapper">
                <table id="schema-table">
                    <thead>
                        <tr>
                            <th>Column Name</th>
                            <th>Data Type</th>
                            <th>Null Values</th>
                            <th>Cardinality (Uniques)</th>
                        </tr>
                    </thead>
                    <tbody>
                        __SCHEMA_ROWS__
                    </tbody>
                </table>
            </div>
        </section>

        <!-- History Log Block -->
        <section class="history-section">
            <h2 style="font-size: 1.6rem; border-left: 5px solid var(--text-muted); padding-left: 0.75rem; margin-bottom: 1.5rem;">Analysis History Log</h2>
            <div class="history-wrapper">
                __HISTORY_HTML__
            </div>
        </section>
    </div>

    <!-- Core Interactive Script -->
    <script>
        const profileData = __PROFILE_DATA_JSON__;
        const insightsData = __INSIGHTS_DATA_JSON__;
        const targetBreakdowns = profileData.target_breakdowns;

        // 1. Initial Target checks
        if (targetBreakdowns && targetBreakdowns.target_column) {
            document.getElementById('target-charts-section').style.display = 'block';
            document.getElementById('target-table-section').style.display = 'block';

            // Populate select inputs
            const catSelect = document.getElementById('categorical-select');
            const catCols = Object.keys(targetBreakdowns.categorical || {});
            catCols.forEach(col => {
                const opt = document.createElement('option');
                opt.value = col;
                opt.innerText = col;
                catSelect.appendChild(opt);
            });

            const numSelect = document.getElementById('numeric-select');
            const numCols = Object.keys(targetBreakdowns.numeric || {});
            numCols.forEach(col => {
                const opt = document.createElement('option');
                opt.value = col;
                opt.innerText = col;
                numSelect.appendChild(opt);
            });

            // Add change event listeners
            catSelect.addEventListener('change', (e) => renderCategoricalChart(e.target.value));
            numSelect.addEventListener('change', (e) => renderNumericChart(e.target.value));

            // Initial renders
            if (catCols.length > 0) renderCategoricalChart(catCols[0]);
            if (numCols.length > 0) renderNumericChart(numCols[0]);
            renderHeatmap();
            populateCohortTable();
        } else {
            document.getElementById('no-target-alert-box').style.display = 'block';
            document.getElementById('perfect-storm-section').style.display = 'none';
        }

        // 2. Render Categorical Double Bar Chart
        function renderCategoricalChart(colName) {
            const data = targetBreakdowns.categorical[colName];
            if (!data) return;

            const categories = data.map(d => String(d.category));
            const rates = data.map(d => d.event_pct);
            const shares = data.map(d => d.pct_of_total_events);

            const trace1 = {
                x: categories,
                y: rates,
                name: 'Cohort Event Rate (%)',
                type: 'bar',
                marker: { color: '#8b5cf6' },
                hovertemplate: '<b>%{x}</b><br>' +
                               'Event Rate: %{y:.2f}%<br>' +
                               'Total Count: %{customdata[0]:,}<br>' +
                               'Event Count: %{customdata[1]:,}<br>' +
                               '<extra></extra>',
                customdata: data.map(d => [d.total_count, d.event_count])
            };

            const trace2 = {
                x: categories,
                y: shares,
                name: 'Share of Total Events (%)',
                type: 'bar',
                marker: { color: '#3b82f6' },
                hovertemplate: '<b>%{x}</b><br>' +
                               'Event Share: %{y:.2f}%<br>' +
                               '<extra></extra>'
            };

            const layout = {
                barmode: 'group',
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#cbd5e1', family: 'Inter, sans-serif' },
                margin: { t: 20, b: 40, l: 50, r: 20 },
                xaxis: { gridcolor: '#1f2937', title: colName },
                yaxis: { gridcolor: '#1f2937', title: 'Percentage (%)' },
                legend: { orientation: 'h', y: -0.2, x: 0.5, xanchor: 'center' }
            };

            Plotly.newPlot('plotly-categorical', [trace1, trace2], layout, {responsive: true});
        }

        // 3. Render Numeric Comparative Bar Chart
        function renderNumericChart(colName) {
            const data = targetBreakdowns.numeric[colName];
            if (!data) return;

            const targetName = targetBreakdowns.target_column;
            const states = data.map(d => `${targetName}: ${d.target_status}`);
            const means = data.map(d => d.mean_val);

            const trace = {
                x: states,
                y: means,
                type: 'bar',
                marker: {
                    color: data.map(d => String(d.target_status) === String(targetBreakdowns.positive_class) ? '#ef4444' : '#10b981')
                },
                hovertemplate: '<b>%{x}</b><br>' +
                               'Average: %{y:.2f}<br>' +
                               'Records: %{customdata:,}<br>' +
                               '<extra></extra>',
                customdata: data.map(d => d.non_null_count)
            };

            const layout = {
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#cbd5e1', family: 'Inter, sans-serif' },
                margin: { t: 20, b: 40, l: 65, r: 20 },
                xaxis: { gridcolor: '#1f2937' },
                yaxis: { gridcolor: '#1f2937', title: 'Cohort Average' }
            };

            Plotly.newPlot('plotly-numeric', [trace], layout, {responsive: true});
        }

        // 4. Render Correlation Heatmap
        function renderHeatmap() {
            const corr = profileData.correlations;
            if (!corr || Object.keys(corr).length === 0) return;

            const cols = Object.keys(corr);
            const zValues = cols.map(c1 => cols.map(c2 => corr[c1][c2] || 0.0));

            const trace = {
                z: zValues,
                x: cols,
                y: cols,
                type: 'heatmap',
                colorscale: 'RdBu',
                reversescale: true,
                zmin: -1,
                zmax: 1,
                hovertemplate: '%{x} vs %{y}<br>Correlation: %{z:.2f}<extra></extra>'
            };

            const layout = {
                paper_bgcolor: 'rgba(0,0,0,0)',
                plot_bgcolor: 'rgba(0,0,0,0)',
                font: { color: '#cbd5e1', family: 'Inter, sans-serif' },
                margin: { t: 20, b: 40, l: 80, r: 20 },
                xaxis: { gridcolor: '#1f2937' },
                yaxis: { gridcolor: '#1f2937' }
            };

            Plotly.newPlot('plotly-heatmap', [trace], layout, {responsive: true});
        }

        // 5. Populate target cohort breakdown table
        function populateCohortTable() {
            const tbody = document.getElementById('cohort-table-body');
            let rowsHtml = '';
            const baseline = targetBreakdowns.baseline_rate;

            Object.entries(targetBreakdowns.categorical).forEach(([col, rows]) => {
                rows.forEach(r => {
                    const isHighRisk = r.event_pct > baseline;
                    const rateColor = isHighRisk ? '#f87171' : '#34d399';
                    const rateWeight = isHighRisk ? '600' : 'normal';

                    rowsHtml += `
                    <tr>
                        <td style="font-weight:600; color:#f9fafb;">${col}</td>
                        <td style="color:#3b82f6;">${r.category}</td>
                        <td>${r.total_count.toLocaleString()}</td>
                        <td>${r.pct_of_dataset.toFixed(1)}%</td>
                        <td>${r.event_count.toLocaleString()}</td>
                        <td style="font-weight:${rateWeight}; color:${rateColor};">${r.event_pct.toFixed(2)}%</td>
                        <td>${r.pct_of_total_events.toFixed(1)}%</td>
                    </tr>
                    `;
                });
            });
            tbody.innerHTML = rowsHtml;
        }

        // 6. Search Filters
        document.getElementById('cohort-table-search').addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            const rows = document.querySelectorAll('#cohort-table-body tr');
            rows.forEach(row => {
                const text = row.innerText.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        });

        document.getElementById('schema-table-search').addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase();
            const rows = document.querySelectorAll('#schema-table tbody tr');
            rows.forEach(row => {
                const text = row.innerText.toLowerCase();
                row.style.display = text.includes(query) ? '' : 'none';
            });
        });
    </script>
</body>
</html>
"""
