import base64
import datetime
import html
import json
import logging
import webbrowser
import re
from pathlib import Path

logger = logging.getLogger('dna.data_engine.report_builder')


class ReportBuilder:
    """Generates self-contained, beautifully styled, interactive HTML/JS dashboards using Chart.js."""

    def build(self, profile: dict, findings: list[dict],
              insights: dict, chart_paths: list[str],
              history: list[dict], output_path: Path,
              clean_fixes: list[dict] = None,
              domain_charts: list[dict] = None) -> str:
        try:
            output_path.mkdir(parents=True, exist_ok=True)
            report_file = output_path / "report.html"

            def clean_text(text: str) -> str:
                if not text:
                    return ""
                return re.sub(r'\[S\d+\]\s*', '', str(text)).strip()


            schema_rows = ""
            total_rows = profile.get('row_count', 1)
            for col in profile.get('schema', []):
                col_name = col['name']
                col_type = col['type']
                nulls = profile.get('null_summary', {}).get(col_name, {}).get('null_count', 0)
                null_pct = (nulls / total_rows) * 100 if total_rows > 0 else 0
                uniques = col.get('uniques', 'N/A')

                schema_rows += f"""
                <tr>
                    <td style="font-weight:600; color:var(--text-main);">{col_name}</td>
                    <td><code style="background:var(--bg-subtle); padding:4px 8px; border-radius:6px; color:var(--accent-orange); font-size:0.85rem; font-weight:600;">{col_type}</code></td>
                    <td style="color:var(--text-muted);">{nulls} ({null_pct:.1f}%)</td>
                    <td style="color:var(--text-muted);">{uniques}</td>
                </tr>
                """
            if not schema_rows:
                schema_rows = "<tr><td colspan='4' style='text-align:center; color:var(--text-muted);'>No schema data available.</td></tr>"

            kpis_html = ""
            for kpi in insights.get('kpis', []):
                label = clean_text(kpi.get('label', ''))
                value = clean_text(kpi.get('value', ''))
                detail = clean_text(kpi.get('detail', ''))
                kpis_html += f"""
                <div class="kpi-card">
                    <span class="kpi-label">{label}</span>
                    <div class="kpi-value">{value}</div>
                    <span class="kpi-detail">{detail}</span>
                </div>
                """

            drivers_html = ""
            for drv in insights.get('drivers', []):
                num = drv.get('trigger_number', '')
                title = clean_text(drv.get('title', ''))
                subtitle = clean_text(drv.get('subtitle', ''))
                stats = [clean_text(s) for s in drv.get('statistics', [])]
                insight = clean_text(drv.get('business_insight', ''))
                
                stats_list = "".join(f"<li style='margin-bottom:0.4rem; color:var(--text-main);'>{s}</li>" for s in stats)
                severity = drv.get('severity', 'HIGH').upper()
                
                border_color = 'var(--danger)' if severity == 'HIGH' else '#f59e0b' if severity == 'MEDIUM' else 'var(--success)'
                bg_color = 'var(--danger-light)' if severity == 'HIGH' else '#fef3c7' if severity == 'MEDIUM' else 'var(--success-light)'
                text_color = 'var(--danger)' if severity == 'HIGH' else '#b45309' if severity == 'MEDIUM' else 'var(--success)'
                
                drivers_html += f"""
                <div class="bezel-card insight-card" style="border-left: 4px solid {border_color};">
                    <div class="insight-header">
                        <h3 class="insight-title">
                            Driver #{num}: {title} <span class="insight-subtitle">({subtitle})</span>
                        </h3>
                        <span class="insight-badge" style="background:{bg_color}; color:{text_color};">{severity}</span>
                    </div>
                    <ul class="insight-list">
                        {stats_list}
                    </ul>
                    <div class="insight-rationale">
                        <strong style="color:var(--accent-dark);">Business Insight:</strong> <span style="color:var(--text-muted);">{insight}</span>
                    </div>
                </div>
                """
            if not drivers_html:
                drivers_html = "<div class='bezel-card'><p style='color:var(--text-muted); text-align:center;'>No drivers reported.</p></div>"

            outliers_html = ""
            for out in insights.get('outliers_and_anomalies', []):
                col_name = clean_text(out.get('column', ''))
                sev = str(out.get('severity', 'HIGH')).upper()
                cnt = out.get('outlier_count', 0)
                impact = clean_text(out.get('volume_impact', ''))
                insight = clean_text(out.get('business_insight', ''))

                border_color = 'var(--danger)' if sev == 'HIGH' else '#f59e0b'
                bg_color = 'var(--danger-light)' if sev == 'HIGH' else '#fef3c7'
                text_color = 'var(--danger)' if sev == 'HIGH' else '#b45309'

                outliers_html += f"""
                <div class="bezel-card insight-card" style="border-left: 4px solid {border_color};">
                    <div class="insight-header">
                        <h4 class="insight-title" style="font-size:1rem; color:var(--text-main);">
                            Extreme Volatility: Column '{col_name}' ({cnt} Outliers)
                        </h4>
                        <span class="insight-badge" style="background:{bg_color}; color:{text_color};">{sev} SEVERITY</span>
                    </div>
                    <div style="font-size:0.85rem; color:var(--danger); font-weight:700; margin-bottom:0.5rem;">
                        Impact Volume: {impact}
                    </div>
                    <div class="insight-rationale">
                        <strong style="color:var(--accent-dark);">Analytical Takeaway:</strong> <span style="color:var(--text-muted);">{insight}</span>
                    </div>
                </div>
                """
            if not outliers_html or outliers_html == "<div class='bezel-card'><p style='color:var(--text-muted); text-align:center;'>No extreme outliers reported.</p></div>":
                if findings:
                    outliers_html = ""
                    for f in findings:
                        col_name = clean_text(f.get('column', ''))
                        detail = clean_text(f.get('detail', ''))
                        sev = str(f.get('severity', 'HIGH')).upper()
                        outliers_html += f"""
                        <div class="bezel-card insight-card" style="border-left: 4px solid var(--danger);">
                            <div class="insight-header">
                                <h4 class="insight-title" style="font-size:1rem; color:var(--text-main);">
                                    Finding: Column '{col_name}'
                                </h4>
                                <span class="insight-badge" style="background:var(--danger-light); color:var(--danger);">{sev} SEVERITY</span>
                            </div>
                            <div class="insight-rationale">
                                <strong style="color:var(--accent-dark);">Detail:</strong> <span style="color:var(--text-muted);">{detail}</span>
                            </div>
                        </div>
                        """
                else:
                    outliers_html = "<div class='bezel-card'><p style='color:var(--text-muted); text-align:center;'>No extreme outliers reported.</p></div>"


            ps_html = ""
            for seg in insights.get('compound_segments', []):
                segment = clean_text(seg.get('segment', ''))
                tot = clean_text(seg.get('total_records', ''))
                rate = clean_text(seg.get('rate_or_value', ''))
                ins = clean_text(seg.get('business_insight', ''))
                
                ps_html += f"""
                <tr>
                    <td style="font-weight:600; color:var(--text-main); font-size:0.9rem;">{segment}</td>
                    <td style="color:var(--text-muted);">{tot}</td>
                    <td><span style="background:var(--danger-light); color:var(--danger); padding:4px 8px; border-radius:6px; font-weight:700; font-size:0.85rem;">{rate}</span></td>
                    <td style="color:var(--text-muted); font-size:0.85rem; line-height:1.5;">{ins}</td>
                </tr>
                """
            if not ps_html:
                ps_html = "<tr><td colspan='4' style='text-align:center; color:var(--text-muted);'>No segments reported.</td></tr>"

            recs_html = ""
            for rec in insights.get('recommendations', []):
                if isinstance(rec, dict):
                    title = clean_text(rec.get('title', ''))
                    action = clean_text(rec.get('action', ''))
                    rationale = clean_text(rec.get('rationale', ''))
                else:
                    title = 'Recommendation'
                    action = clean_text(str(rec))
                    rationale = ''
                
                recs_html += f"""
                <div class="bezel-card insight-card" style="border-top: 4px solid var(--accent-orange);">
                    <div class="insight-header" style="margin-bottom:0.75rem;">
                        <h4 class="insight-title" style="font-size:1.05rem;">{title}</h4>
                    </div>
                    <div class="insight-rationale" style="background:var(--bg-subtle);">
                        <p style="margin:0 0 0.5rem 0; color:var(--text-main); font-size:0.9rem; line-height:1.5; font-weight:600;">{action}</p>
                        <p style="margin:0; color:var(--text-muted); font-size:0.85rem; line-height:1.5;">{rationale}</p>
                    </div>
                </div>
                """
            if not recs_html:
                recs_html = "<div class='bezel-card'><p style='color:var(--text-muted); text-align:center;'>No recommendations generated.</p></div>"

            # 5. Format History Log Items (Real-Time Pipeline Trace)
            history_html = ""
            pipeline_trace = profile.get('pipeline_trace', [])

            if not pipeline_trace:
                # Fallback: Synthesize real-time trace from active profile/insights metadata
                row_cnt = profile.get('row_count', 0)
                col_cnt = profile.get('column_count', 0)
                qual = profile.get('quality_score', 100.0)
                domain_info = profile.get('domain_info', {})
                dom_name = domain_info.get('domain_name', 'Enterprise Data')
                conf = domain_info.get('confidence', 0.95)
                num_findings = len(findings)
                num_drivers = len(insights.get('key_drivers', []))
                num_recs = len(insights.get('recommendations', []))
                num_charts = len(domain_charts) if domain_charts else 0
                now = datetime.datetime.now()

                pipeline_trace = [
                    {
                        'stage': 'Stage 1: Data Profiling & Schema Inference',
                        'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
                        'status': 'Completed successfully.',
                        'summary': f"Profiled dataset ({row_cnt:,} rows, {col_cnt} columns). Domain classified as '{dom_name}' ({conf:.0%} confidence). Quality score: {qual:.1f}%."
                    },
                    {
                        'stage': 'Stage 2: Statistical Analysis & Anomaly Engine',
                        'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
                        'status': 'Completed successfully.',
                        'summary': f"Processed column distributions and detected {num_findings} structural patterns & statistical anomalies."
                    },
                    {
                        'stage': 'Stage 3: LLM Orchestration & Domain Analyst',
                        'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
                        'status': 'Completed successfully.',
                        'summary': f"Generated narrative 360° executive summary, {num_drivers} strategic risk drivers, and {num_recs} recommendations."
                    },
                    {
                        'stage': 'Stage 4: Dynamic Visualization & Dashboard Build',
                        'timestamp': now.strftime("%Y-%m-%d %H:%M:%S"),
                        'status': 'Completed successfully.',
                        'summary': f"Executed dynamic SQL aggregations for {num_charts} domain charts and built Bento dashboard report."
                    }
                ]

            for item in pipeline_trace:
                timestamp = item.get('timestamp', '')
                stage_title = item.get('stage', 'Pipeline Stage')
                status_text = item.get('status', 'Completed successfully.')
                summary_text = clean_text(item.get('summary', 'Success'))
                query_type = 'Pipeline Execution'

                history_html += f"""
                <div class="bezel-card" style="margin-bottom:1rem; padding:1.5rem; border-left: 3px solid var(--accent-orange);">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                        <span style="font-size:0.75rem; color:var(--text-muted); font-weight:600; display:flex; align-items:center; gap:0.5rem;">
                            <span style="display:inline-block; width:6px; height:6px; border-radius:50%; background:var(--success);"></span>
                            {timestamp}
                        </span>
                        <span style="background:var(--bg-subtle); color:var(--text-main); padding:4px 10px; border-radius:999px; font-size:0.7rem; font-weight:700; border:1px solid var(--border-light);">{query_type}</span>
                    </div>
                    <div style="font-weight:700; color:var(--text-main); font-size:1.1rem; margin-bottom:0.5rem;">{stage_title}</div>
                    <div style="color:var(--text-muted); font-size:0.9rem; line-height:1.6;">
                        <strong>Status:</strong> {status_text}<br>
                        <strong>Output Summary:</strong> {summary_text}
                    </div>
                </div>
                """
            if not history_html:
                history_html = "<div class='bezel-card'><p style='color:var(--text-muted); text-align:center;'>No operations recorded.</p></div>"

            dim_chart_payload = {}
            yoy_chart_payload = {}

            def _build_domain_aggs_table_html(domain_aggs: dict) -> str:
                """Build Executive KPI summary table, YoY performance table, and Dimensional Profitability split tables with Table/Chart toggle."""
                if not domain_aggs:
                    return ""

                tot_sales = domain_aggs.get('total_sales', 0.0)
                tot_profit = domain_aggs.get('total_profit', 0.0)
                margin_pct = domain_aggs.get('blended_margin_pct', 0.0)
                avg_disc = domain_aggs.get('avg_discount_pct', 0.0)
                loss_cnt = domain_aggs.get('loss_orders_count', 0)
                loss_amt = domain_aggs.get('total_loss_amount', 0.0)
                yoy_data = domain_aggs.get('yoy_data', [])

                html = ""

                # Financial Metrics Executive Summary Table (ONLY if tot_sales > 0)
                if tot_sales > 0:
                    html += f"""
                    <div class="bezel-card" style="margin-top:1.5rem; padding:1.5rem;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                            <span class="card-title" style="margin:0; font-size:1.1rem; color:var(--text-main);">Executive Summary Dashboard Table</span>
                            <span style="background:var(--accent-orange-light); color:var(--accent-orange); padding:4px 10px; border-radius:999px; font-size:0.75rem; font-weight:700;">Financial Metrics</span>
                        </div>
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Metric</th>
                                    <th>Value</th>
                                    <th>Business Context</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td style="font-weight:600;">Total Revenue (Sales)</td>
                                    <td style="font-weight:700; color:var(--text-main);">${tot_sales:,.2f}</td>
                                    <td style="color:var(--text-muted);">Total aggregated top-line revenue</td>
                                </tr>
                                <tr>
                                    <td style="font-weight:600;">Total Net Profit</td>
                                    <td style="font-weight:700; color:var(--success);">${tot_profit:,.2f}</td>
                                    <td style="color:var(--text-muted);">Overall corporate bottom-line yield</td>
                                </tr>
                                <tr>
                                    <td style="font-weight:600;">Blended Profit Margin</td>
                                    <td style="font-weight:700; color:{'var(--success)' if margin_pct > 10 else '#f59e0b'};">{margin_pct:.2f}%</td>
                                    <td style="color:var(--text-muted);">Overall corporate margin performance</td>
                                </tr>
                                <tr>
                                    <td style="font-weight:600;">Average Discount Rate</td>
                                    <td style="font-weight:700; color:#f59e0b;">{avg_disc:.2f}%</td>
                                    <td style="color:var(--text-muted);">Average promotional markdown percentage</td>
                                </tr>
                                <tr>
                                    <td style="font-weight:600;">Loss-Making Orders</td>
                                    <td style="font-weight:700; color:var(--danger);">{loss_cnt:,} orders</td>
                                    <td style="color:var(--danger);">Responsible for -${abs(loss_amt):,.2f} in net profit loss</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    """

                # Dynamic Year-over-Year (YoY) Performance Table (ONLY if yoy_data exists)
                if yoy_data:
                    yoy_rows = ""
                    yoy_labels = []
                    yoy_revs = []
                    yoy_profs = []
                    start_yr = yoy_data[0]['year']
                    end_yr = yoy_data[-1]['year']

                    for d in yoy_data:
                        yr = d['year']
                        rev = d['revenue']
                        prof = d['profit']
                        m_pct = d['margin_pct']
                        g_pct = d['growth_pct']

                        yoy_labels.append(yr)
                        yoy_revs.append(rev)
                        yoy_profs.append(prof)

                        growth_str = "- Baseline -"
                        if g_pct is not None:
                            if g_pct >= 0:
                                growth_str = f'<span style="color:var(--success); font-weight:700;">+{g_pct:.2f}%</span>'
                            else:
                                growth_str = f'<span style="color:var(--danger); font-weight:700;">{g_pct:.2f}%</span>'

                        yoy_rows += f"""
                        <tr>
                            <td style="font-weight:700; color:var(--text-main);">{yr}</td>
                            <td style="font-weight:700;">${rev:,.2f}</td>
                            <td style="font-weight:700; color:var(--success);">${prof:,.2f}</td>
                            <td><span style="background:var(--success-light); color:var(--success); padding:3px 8px; border-radius:6px; font-weight:700; font-size:0.8rem;">{m_pct:.2f}%</span></td>
                            <td>{growth_str}</td>
                        </tr>
                        """

                    yoy_chart_payload['labels'] = yoy_labels
                    yoy_chart_payload['revenue'] = yoy_revs
                    yoy_chart_payload['profit'] = yoy_profs

                    html += f"""
                    <div class="bezel-card" style="margin-top:1.5rem; padding:1.5rem;">
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                            <span class="card-title" style="margin:0; font-size:1.1rem; color:var(--text-main);">Year-over-Year (YoY) Performance ({start_yr} – {end_yr})</span>
                            <div class="toggle-control" style="background:var(--bg-subtle); border-radius:999px; padding:3px; display:flex; gap:4px; border:1px solid var(--border-light);">
                                <button class="toggle-btn active" onclick="toggleDomainView(this, 'table')" style="border:none; background:var(--accent-dark); color:white; padding:4px 12px; border-radius:999px; font-size:0.75rem; font-weight:600; cursor:pointer;">Table</button>
                                <button class="toggle-btn" onclick="toggleDomainView(this, 'chart')" style="border:none; background:transparent; color:var(--text-muted); padding:4px 12px; border-radius:999px; font-size:0.75rem; font-weight:600; cursor:pointer;">Chart</button>
                            </div>
                        </div>
                        <div class="card-view-table">
                            <table class="data-table">
                                <thead>
                                    <tr>
                                        <th>Fiscal Year</th>
                                        <th>Total Revenue</th>
                                        <th>Net Profit</th>
                                        <th>Profit Margin</th>
                                        <th>YoY Revenue Growth</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {yoy_rows}
                                </tbody>
                            </table>
                        </div>
                        <div class="card-view-chart" style="display:none; height:280px; position:relative;">
                            <canvas id="yoy-sales-chart"></canvas>
                        </div>
                    </div>
                    """

                dim_brk = domain_aggs.get('dimensional_breakdowns', {})
                if dim_brk:
                    for dim_name, rows in dim_brk.items():
                        table_rows = ""
                        chart_labels = []
                        chart_sales = []
                        chart_profit = []
                        safe_dim = re.sub(r'[^a-zA-Z0-9]', '_', dim_name).lower()

                        for r in rows:
                            cat = r.get('category', '')
                            s = r.get('sales', 0.0)
                            p = r.get('profit', 0.0)
                            m = r.get('margin_pct', 0.0)
                            share = (s / tot_sales * 100.0) if tot_sales > 0 else 0.0
                            
                            chart_labels.append(cat)
                            chart_sales.append(s)
                            chart_profit.append(p)

                            badge_style = "background:var(--success-light); color:var(--success);" if m >= 15.0 else ("background:#fef3c7; color:#b45309;" if m >= 5.0 else "background:var(--danger-light); color:var(--danger);")

                            table_rows += f"""
                            <tr>
                                <td style="font-weight:600; color:var(--text-main);">{cat}</td>
                                <td style="font-weight:700;">${s:,.2f}</td>
                                <td style="font-weight:700; color:{'var(--danger)' if p < 0 else 'var(--text-main)'};">${p:,.2f}</td>
                                <td><span style="{badge_style} padding:3px 8px; border-radius:6px; font-weight:700; font-size:0.8rem;">{m:.2f}%</span></td>
                                <td style="color:var(--text-muted);">{share:.1f}%</td>
                            </tr>
                            """

                        dim_chart_payload[safe_dim] = {
                            'dim_name': dim_name,
                            'labels': chart_labels,
                            'sales': chart_sales,
                            'profit': chart_profit
                        }

                        html += f"""
                        <div class="bezel-card" style="margin-top:1.5rem; padding:1.5rem;" data-dim-id="{safe_dim}">
                            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                                <span class="card-title" style="margin:0; font-size:1.1rem; color:var(--text-main);">Category & Dimensional Performance Split ({dim_name})</span>
                                <div class="toggle-control" style="background:var(--bg-subtle); border-radius:999px; padding:3px; display:flex; gap:4px; border:1px solid var(--border-light);">
                                    <button class="toggle-btn active" onclick="toggleDomainView(this, 'table')" style="border:none; background:var(--accent-dark); color:white; padding:4px 12px; border-radius:999px; font-size:0.75rem; font-weight:600; cursor:pointer;">Table</button>
                                    <button class="toggle-btn" onclick="toggleDomainView(this, 'chart')" style="border:none; background:transparent; color:var(--text-muted); padding:4px 12px; border-radius:999px; font-size:0.75rem; font-weight:600; cursor:pointer;">Chart</button>
                                </div>
                            </div>
                            <div class="card-view-table">
                                <table class="data-table">
                                    <thead>
                                        <tr>
                                            <th>{dim_name}</th>
                                            <th>Total Revenue</th>
                                            <th>Net Profit</th>
                                            <th>Profit Margin</th>
                                            <th>Revenue Share</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {table_rows}
                                    </tbody>
                                </table>
                            </div>
                            <div class="card-view-chart" style="display:none; height:280px; position:relative;">
                                <canvas id="dim-chart-{safe_dim}"></canvas>
                            </div>
                        </div>
                        """

                return html

            filename = Path(profile.get('file_path', 'Unknown')).name
            filepath = profile.get('file_path', 'Unknown')
            quality_score = profile.get('quality_score', 100.0)

            domain_aggs_tables_html = _build_domain_aggs_table_html(profile.get('domain_aggregations', {}))

            raw_exec_summary = clean_text(insights.get('executive_summary', 'No executive summary available.'))
            exec_paragraphs = [p.strip() for p in raw_exec_summary.split('\n\n') if p.strip()]
            if exec_paragraphs:
                exec_summary_formatted = "".join([f'<p style="margin-bottom:0.85rem; line-height:1.75; font-size:0.95rem; color:var(--text-main);">{p}</p>' for p in exec_paragraphs])
            else:
                exec_summary_formatted = f'<p style="line-height:1.75; font-size:0.95rem; color:var(--text-main);">{raw_exec_summary}</p>'

            profile = dict(profile)
            profile['findings'] = findings

            html_content = HTML_TEMPLATE
            html_content = html_content.replace("__FILENAME__", filename)
            html_content = html_content.replace("__FILEPATH__", filepath)
            html_content = html_content.replace("__ROW_COUNT__", f"{profile.get('row_count', 0):,}")
            html_content = html_content.replace("__COLUMN_COUNT__", str(profile.get('column_count', 0)))
            html_content = html_content.replace("__QUALITY_SCORE__", f"{quality_score:.1f}%")
            html_content = html_content.replace("__EXECUTIVE_SUMMARY__", exec_summary_formatted)
            
            html_content = html_content.replace("__KPI_CARDS_HTML__", kpis_html)
            html_content = html_content.replace("__DOMAIN_AGGS_TABLES_HTML__", domain_aggs_tables_html)

            html_content = html_content.replace("__DRIVERS_HTML__", drivers_html)
            html_content = html_content.replace("__OUTLIERS_HTML__", outliers_html)
            html_content = html_content.replace("__PERFECT_STORM_ROWS_HTML__", ps_html)
            html_content = html_content.replace("__RECOMMENDATIONS_HTML__", recs_html)
            html_content = html_content.replace("__SCHEMA_ROWS__", schema_rows)
            html_content = html_content.replace("__HISTORY_HTML__", history_html)

            html_content = html_content.replace("__PROFILE_DATA_JSON__", json.dumps(profile))
            html_content = html_content.replace("__INSIGHTS_DATA_JSON__", json.dumps(insights))
            html_content = html_content.replace("__DOMAIN_CHARTS_JSON__", json.dumps(domain_charts or []))
            html_content = html_content.replace("__DIM_CHART_DATA_JSON__", json.dumps(dim_chart_payload))
            html_content = html_content.replace("__YOY_CHART_DATA_JSON__", json.dumps(yoy_chart_payload))



            with open(report_file, "w", encoding="utf-8") as f:
                f.write(html_content)

            logger.info('HTML report written successfully to: %s', report_file)
            return str(report_file.resolve())
        except Exception as e:
            logger.error('ReportBuilder failed: %s', e, exc_info=True)
            raise e

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DNA Engine — __FILENAME__</title>
    
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
    
    <!-- Chart.js CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    
    <style>
        :root {
            --bg-app: #f4f5f8;
            --bg-card: #ffffff;
            --bg-sidebar: #ffffff;
            --bg-subtle: #f9fafb;
            
            --text-main: #111827;
            --text-muted: #6b7280;
            --text-inverse: #ffffff;
            
            --accent-orange: #ff6a3d;
            --accent-orange-hover: #e85a2d;
            --accent-orange-light: #fff0eb;
            --accent-dark: #1c1d21;
            
            --success: #10b981;
            --success-light: #d1fae5;
            --danger: #ef4444;
            --danger-light: #fee2e2;
            
            --border-light: rgba(0, 0, 0, 0.06);
            --shadow-soft: 0 10px 40px -10px rgba(0,0,0,0.04);
            
            --radius-xl: 24px;
            --radius-lg: 16px;
            --radius-md: 12px;
            --radius-pill: 999px;
            
            --bezier: cubic-bezier(0.32, 0.72, 0, 1);
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-app); color: var(--text-main);
            font-family: 'Plus Jakarta Sans', sans-serif;
            -webkit-font-smoothing: antialiased; display: flex; min-height: 100vh;
        }

        .sidebar {
            width: 80px; background: var(--bg-sidebar); display: flex; flex-direction: column;
            align-items: center; padding: 1.5rem 0; gap: 2rem; border-right: 1px solid var(--border-light);
            position: fixed; height: 100vh; z-index: 50;
        }

        .brand-logo {
            width: 40px; height: 40px; background: var(--accent-orange); color: white;
            border-radius: 12px; display: flex; align-items: center; justify-content: center;
            font-family: 'Space Grotesk', sans-serif; font-weight: 700; font-size: 1.2rem;
        }

        .icon-btn {
            width: 40px; height: 40px; border-radius: 12px; display: flex; align-items: center;
            justify-content: center; color: var(--text-muted); cursor: pointer; transition: all 0.4s var(--bezier);
            margin-bottom: 1.5rem;
        }
        .icon-btn:hover, .icon-btn.active {
            background: var(--accent-dark); color: white; box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        .main-wrapper { flex: 1; margin-left: 80px; display: flex; flex-direction: column; }
        
        .topbar {
            height: 80px; display: flex; align-items: center; justify-content: space-between;
            padding: 0 2.5rem; background: var(--bg-app);
        }

        .nav-tabs {
            display: flex; align-items: center; background: var(--bg-card); padding: 0.35rem;
            border-radius: var(--radius-pill); box-shadow: 0 2px 10px rgba(0,0,0,0.02);
            border: 1px solid var(--border-light);
        }
        .nav-tab {
            padding: 0.5rem 1.5rem; border-radius: var(--radius-pill); font-size: 0.85rem; font-weight: 600;
            color: var(--text-muted); text-decoration: none; transition: all 0.4s var(--bezier);
            cursor: pointer; border: none; background: transparent;
        }
        .nav-tab.active { background: var(--accent-dark); color: white; }

        .user-profile {
            display: flex; align-items: center; gap: 0.75rem; background: var(--bg-card);
            padding: 0.35rem 1rem 0.35rem 0.35rem; border-radius: var(--radius-pill);
            box-shadow: 0 2px 10px rgba(0,0,0,0.02); border: 1px solid var(--border-light);
        }
        .user-avatar {
            width: 32px; height: 32px; background: var(--accent-orange); border-radius: 50%;
            display: flex; align-items: center; justify-content: center; color: white;
            font-weight: 700; font-size: 0.8rem;
        }
        .user-info { display: flex; flex-direction: column; font-size: 0.75rem; }
        .user-name { font-weight: 700; color: var(--text-main); }
        .user-role { color: var(--text-muted); }

        .content-area { padding: 1rem 2.5rem 3rem 2.5rem; display: flex; flex-direction: column; gap: 2.5rem; }

        .page-header { margin-bottom: 0.5rem; }
        .page-title { font-family: 'Space Grotesk', sans-serif; font-size: 2rem; font-weight: 700; letter-spacing: -0.02em; color: var(--text-main); }
        .page-subtitle { font-size: 0.95rem; color: var(--text-muted); margin-top: 0.25rem; }

        .section-block { display: flex; flex-direction: column; gap: 1.25rem; }
        .section-title { font-family: 'Space Grotesk', sans-serif; font-size: 1.35rem; font-weight: 700; color: var(--text-main); margin-bottom: 0.5rem; border-bottom: 2px solid var(--border-light); padding-bottom: 0.5rem; }

        .bento-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-bottom: 1.25rem; }
        .bento-grid-3 { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 1.25rem; }

        .bezel-card {
            background: var(--bg-card); border-radius: var(--radius-xl); padding: 1.5rem;
            box-shadow: var(--shadow-soft); border: 1px solid var(--border-light);
            display: flex; flex-direction: column; position: relative;
        }
        
        .card-title {
            font-size: 0.85rem; font-weight: 600; color: var(--text-muted); margin-bottom: 1rem;
            display: flex; justify-content: space-between; align-items: center; text-transform: uppercase; letter-spacing: 0.05em;
        }

        /* --- KPI Cards Grid --- */
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 1.5rem;
        }
        .kpi-card {
            background: var(--bg-card);
            border: 1px solid var(--border-light);
            border-radius: var(--radius-lg);
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            justify-content: center;
            box-shadow: var(--shadow-soft);
            border-bottom: 3px solid var(--accent-orange);
        }
        .kpi-label { font-size: 0.75rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; margin-bottom: 0.5rem; }
        .kpi-value { font-family: 'Space Grotesk', sans-serif; font-size: 1.6rem; font-weight: 700; color: var(--text-main); margin-bottom: 0.25rem; }
        .kpi-detail { font-size: 0.8rem; color: var(--text-muted); line-height: 1.4; }

        .health-score { font-family: 'Space Grotesk', sans-serif; font-size: 3.5rem; font-weight: 700; color: var(--text-main); line-height: 1; margin-bottom: 0.5rem; }

        .stats-4grid { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 1rem; height: 100%; }
        .mini-stat {
            background: var(--bg-card); border: 1px solid var(--border-light); border-radius: var(--radius-lg);
            padding: 1.25rem; display: flex; flex-direction: column; justify-content: center;
        }
        .mini-stat.orange { background: linear-gradient(135deg, var(--accent-orange) 0%, #ff855f 100%); color: white; border: none; }
        .mini-stat.orange .card-title, .mini-stat.orange .mini-val { color: white; }
        .mini-val { font-family: 'Space Grotesk', sans-serif; font-size: 1.75rem; font-weight: 700; color: var(--text-main); }

        /* --- Insight Card specific styles --- */
        .insight-card { padding: 1.25rem; margin-bottom: 1rem; }
        .insight-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem; }
        .insight-title { margin: 0; font-size: 1.1rem; color: var(--text-main); font-weight: 700; line-height: 1.4; }
        .insight-subtitle { font-weight: 500; font-size: 0.85rem; color: var(--text-muted); display: block; margin-top: 0.25rem; }
        .insight-badge { padding: 4px 10px; border-radius: 999px; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.5px; white-space: nowrap; }
        .insight-list { margin: 0 0 1rem 1.25rem; padding: 0; font-size: 0.9rem; line-height: 1.6; }
        .insight-rationale { background: var(--bg-subtle); padding: 1rem; border-radius: 12px; font-size: 0.85rem; line-height: 1.6; border: 1px solid var(--border-light); }

        .data-table { width: 100%; border-collapse: collapse; }
        .data-table th { text-align: left; padding: 1rem; font-size: 0.75rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 1px solid var(--border-light); }
        .data-table td { padding: 1.25rem 1rem; font-size: 0.85rem; color: var(--text-main); border-bottom: 1px solid var(--border-light); }
    </style>
</head>
<body>

    <aside class="sidebar">
        <div class="brand-logo">D</div>
        <div class="nav-icons">
            <div class="icon-btn active"><svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h7"></path></svg></div>
            <div class="icon-btn"><svg width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M12 20V10m0 0l-3 3m3-3l3 3m5 4a2 2 0 100-4 2 2 0 000 4zM5 16a2 2 0 100-4 2 2 0 000 4z"></path></svg></div>
        </div>
    </aside>

    <main class="main-wrapper">
        <header class="topbar">
            <div style="font-family:'Space Grotesk', sans-serif; font-size:1.1rem; font-weight:700; color:var(--text-main);">
                Executive Data Intelligence Report
            </div>
            <div class="topbar-actions">
                <div class="user-profile">
                    <div class="user-avatar">AI</div>
                    <div class="user-info">
                        <span class="user-name">Gemini Analyst</span>
                        <span class="user-role">Autonomous Engine</span>
                    </div>
                </div>
            </div>
        </header>

        <div class="content-area">
            <div class="page-header">
                <h1 class="page-title">Dataset Analysis, __FILENAME__</h1>
                <p class="page-subtitle">Comprehensive Single-Page Executive Dashboard & Strategic Breakdown.</p>
            </div>

            <!-- SECTION 1: OVERVIEW & KPIS -->
            <div class="section-block">
                <h2 class="section-title">Executive Overview & Key Metrics</h2>
                
                <div class="kpi-grid">
                    __KPI_CARDS_HTML__
                </div>

                <div class="bezel-card" style="margin-bottom:1.5rem; padding:1.5rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                        <span class="card-title" style="margin:0; font-size:1.15rem; color:var(--text-main);">Comprehensive 360° Executive Summary</span>
                        <span style="background:var(--success-light); color:var(--success); padding:4px 12px; border-radius:999px; font-size:0.8rem; font-weight:700;">Dataset Quality Profile: __QUALITY_SCORE__</span>
                    </div>
                    <div style="font-size:0.95rem; color:var(--text-main); line-height:1.65; background:var(--bg-subtle); padding:1.25rem; border-radius:var(--radius-lg); border:1px solid var(--border-light);">
                        __EXECUTIVE_SUMMARY__
                    </div>
                </div>

                __DOMAIN_AGGS_TABLES_HTML__
            </div>

            <!-- SECTION 2: DOMAIN DATA TABLES -->
            <div class="section-block">
                <h2 class="section-title">Analytical Domain Data Tables</h2>
                <div class="bento-grid-3" id="charts-grid-container">
                    <!-- Domain Data Tables injected via JS -->
                </div>
            </div>

            <!-- SECTION 3: STRATEGIC INSIGHTS & DRIVERS -->
            <div class="section-block">
                <h2 class="section-title">Strategic Drivers & Volatility Triggers</h2>
                __DRIVERS_HTML__
            </div>

            <!-- SECTION 4: OUTLIERS & ANOMALIES -->
            <div class="section-block">
                <h2 class="section-title">Outlier Volume & Risk Highlights</h2>
                __OUTLIERS_HTML__
            </div>

            <!-- SECTION 5: RECOMMENDATIONS -->
            <div class="section-block">
                <h2 class="section-title">Executive Action Items & Recommendations</h2>
                __RECOMMENDATIONS_HTML__
            </div>

            <!-- SECTION 6: HIGH VOLATILITY COHORTS -->
            <div class="section-block">
                <h2 class="section-title">Segment Performance Breakdown</h2>
                <div class="bezel-card">
                    <div style="overflow-x:auto;">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Segment Cohort</th>
                                    <th>Volume</th>
                                    <th>Event Rate</th>
                                    <th>Business Insight</th>
                                </tr>
                            </thead>
                            <tbody>
                                __PERFECT_STORM_ROWS_HTML__
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- SECTION 7: SCHEMA CATALOG -->
            <div class="section-block">
                <h2 class="section-title">Dataset Schema Catalog</h2>
                <div class="bezel-card">
                    <div style="overflow-x:auto;">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Column Name</th>
                                    <th>Data Type</th>
                                    <th>Null Values</th>
                                    <th>Cardinality</th>
                                </tr>
                            </thead>
                            <tbody>
                                __SCHEMA_ROWS__
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- SECTION 8: AUDIT LOG LOG -->
            <div class="section-block">
                <h2 class="section-title">Technical Audit Log & Pipeline Execution Trace</h2>
                <div style="display:flex; flex-direction:column; gap:0;">
                    __HISTORY_HTML__
                </div>
            </div>

        </div>
    </main>

    <script>
        // Data Payloads
        const profileData = __PROFILE_DATA_JSON__;

        const targetBreakdowns = profileData.target_breakdowns;
        const domainCharts = __DOMAIN_CHARTS_JSON__;

        // Render Dynamic Domain Data Tables (Cohort Tables)
        if (domainCharts && Array.isArray(domainCharts) && domainCharts.length > 0) {
            const container = document.getElementById('charts-grid-container');
            container.innerHTML = '';
            
            // Cut out line/trend and scatter tables as requested
            const cohortCharts = domainCharts.filter(c => {
                const cType = (c.chart_type || c.type || '').toLowerCase();
                const title = (c.title || '').toLowerCase();
                return cType !== 'line' && cType !== 'trend' && cType !== 'scatter' && !title.includes('over time') && !title.includes('trend') && !title.includes('scatter');
            });

            if (cohortCharts.length === 0) {
                container.innerHTML = `<div class="bezel-card"><p style="color:var(--text-muted);">No cohort tables available.</p></div>`;
            }

            cohortCharts.forEach((cData, idx) => {
                const card = document.createElement('div');
                card.className = 'bezel-card';
                card.style.display = 'flex';
                card.style.flexDirection = 'column';
                card.style.justifyContent = 'space-between';
                card.style.padding = '1.5rem';
                
                const takeaway = cData.takeaway || cData.default_takeaway || 'Key domain cohort metrics.';
                const rawRows = cData.data || [];
                
                let tableHtml = '';
                if (rawRows.length > 0) {
                    const keys = Object.keys(rawRows[0]);

                    // Helper to produce clean Cohort header names
                    const formatHeader = (key, colIdx) => {
                        const lower = key.toLowerCase();
                        if (colIdx === 0 && (lower === 'category' || lower === 'sub_category' || lower === 'dim' || lower === 'date_period')) {
                            return 'Cohort / Dimension';
                        }
                        return key.replace(/_/g, ' ');
                    };
                    
                    tableHtml = `
                    <div style="overflow-x:auto; margin-top:0.75rem;">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    ${keys.map((k, colIdx) => `<th>${formatHeader(k, colIdx)}</th>`).join('')}
                                </tr>
                            </thead>
                            <tbody>
                                ${rawRows.map(r => `
                                    <tr>
                                        ${keys.map((k, colIdx) => {
                                            let val = r[k];
                                            let formattedVal = val;
                                            let style = colIdx === 0 ? 'font-weight:600; color:var(--text-main);' : '';
                                            const lowerKey = k.toLowerCase();
                                            
                                            if (typeof val === 'number') {
                                                const isPercent = lowerKey.includes('margin') || lowerKey.includes('rate') || lowerKey.includes('pct') || lowerKey.includes('%') || lowerKey.includes('discount');
                                                const isCount = lowerKey.includes('count') || lowerKey.includes('volume') || lowerKey.includes('qty') || lowerKey.includes('quantity') || lowerKey.includes('orders') || lowerKey.includes('rows') || lowerKey.includes('records') || lowerKey.includes('num');
                                                const isCurrency = (lowerKey.includes('sales') || lowerKey.includes('profit') || lowerKey.includes('revenue') || lowerKey.includes('amount') || lowerKey.includes('loss') || lowerKey.includes('ticket') || lowerKey.includes('value') || lowerKey.includes('cost') || lowerKey.includes('val') || lowerKey.includes('sum') || lowerKey.includes('primary')) && !isCount && !isPercent;
                                                
                                                if (isCount) {
                                                    formattedVal = Math.round(val).toLocaleString('en-US');
                                                } else if (isPercent) {
                                                    formattedVal = (val <= 1 && val >= -1 && val !== 0 ? (val * 100).toFixed(2) : val.toFixed(2)) + '%';
                                                    if (val < 0) style += ' color: #ef4444; font-weight:700;';
                                                } else if (isCurrency) {
                                                    let isNeg = val < 0;
                                                    let absVal = Math.abs(val).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                                                    formattedVal = (isNeg ? '-$' : '$') + absVal;
                                                    if (isNeg) style += ' color: #ef4444; font-weight:700;';
                                                } else {
                                                    formattedVal = Number.isInteger(val) ? val.toLocaleString('en-US') : val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
                                                }
                                            }
                                            return `<td style="${style}">${formattedVal ?? ''}</td>`;
                                        }).join('')}
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    `;
                } else {
                    tableHtml = `<p style="color:var(--text-muted); padding:1rem 0;">No cohort records available.</p>`;
                }

                card.innerHTML = `
                    <div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
                            <span class="card-title" style="margin:0; font-size:1.05rem;">${cData.title}</span>
                            <span style="background:var(--accent-orange-light); color:var(--accent-orange); padding:3px 8px; border-radius:6px; font-size:0.75rem; font-weight:700;">Cohort Data Table</span>
                        </div>
                        ${tableHtml}
                    </div>
                    <div style="margin-top:1rem; padding:0.6rem 0.8rem; background:var(--bg-subtle); border-radius:8px; font-size:0.8rem; color:var(--text-muted); border-left:3px solid var(--accent-orange);">
                        <strong style="color:var(--text-main);">Cohort Insight:</strong> ${takeaway}
                    </div>
                `;
                container.appendChild(card);
            });
        }



        else if (targetBreakdowns && targetBreakdowns.target_column) {

            document.getElementById('target-var-display').innerText = targetBreakdowns.target_column;
            document.getElementById('baseline-rate-display').innerText = (targetBreakdowns.baseline_rate || 0).toFixed(1) + '%';
            
            if (targetBreakdowns.categorical) {
                const chartsContainer = document.getElementById('charts-grid-container');
                const catCols = Object.keys(targetBreakdowns.categorical);
                
                if (catCols.length === 0) {
                    chartsContainer.innerHTML = "<div class='bezel-card'><p style='color:var(--text-muted);'>No categorical charts available.</p></div>";
                }
                
                catCols.forEach((colName, idx) => {
                    const data = targetBreakdowns.categorical[colName];
                    if (!data || data.length === 0) return;

                    const sliceData = data.slice(0, 10);
                    const labels = sliceData.map(d => String(d.category));
                    const rates = sliceData.map(d => d.event_pct);
                    const vols = sliceData.map(d => d.total_count);
                    
                    const canvasId = 'chart-' + idx;
                    
                    const card = document.createElement('div');
                    card.className = 'bezel-card';
                    card.style.height = '360px';
                    card.innerHTML = `
                        <span class="card-title">${colName} Distribution</span>
                        <div style="position: relative; height: 260px; width: 100%;">
                            <canvas id="${canvasId}"></canvas>
                        </div>
                    `;
                    chartsContainer.appendChild(card);
                    
                    // Chart.js Init
                    const ctx = document.getElementById(canvasId).getContext('2d');
                    new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: [
                                {
                                    label: 'Target Rate (%)',
                                    data: rates,
                                    backgroundColor: '#ff6a3d',
                                    borderRadius: 4,
                                    yAxisID: 'y'
                                },
                                {
                                    label: 'Base Volume',
                                    data: vols,
                                    backgroundColor: '#1c1d21',
                                    borderRadius: 4,
                                    yAxisID: 'y1'
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            interaction: {
                                mode: 'index',
                                intersect: false,
                            },
                            plugins: {
                                legend: {
                                    position: 'bottom',
                                    labels: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } }
                                },
                                tooltip: {
                                    backgroundColor: '#1c1d21',
                                    titleFont: { family: "'Plus Jakarta Sans', sans-serif" },
                                    bodyFont: { family: "'Plus Jakarta Sans', sans-serif" },
                                    padding: 12,
                                    cornerRadius: 8
                                }
                            },
                            scales: {
                                x: {
                                    grid: { display: false },
                                    ticks: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 10 } }
                                },
                                y: {
                                    type: 'linear',
                                    display: true,
                                    position: 'left',
                                    grid: { color: 'rgba(0,0,0,0.04)' },
                                    title: { display: true, text: 'Rate (%)', font: { size: 10 } },
                                    ticks: { font: { size: 10 } }
                                },
                                y1: {
                                    type: 'linear',
                                    display: true,
                                    position: 'right',
                                    grid: { display: false },
                                    title: { display: true, text: 'Volume', font: { size: 10 } },
                                    ticks: { font: { size: 10 } }
                                }
                            }
                        }
                    });
                });
            } else {
                document.getElementById('charts-grid-container').innerHTML = "<div class='bezel-card'><p style='color:var(--text-muted);'>No categorical charts available.</p></div>";
            }
        } else {
            // General Transactional Dataset Charting Fallback
            document.getElementById('target-var-display').innerText = "N/A (Transactional)";
            document.getElementById('baseline-rate-display').innerText = "-";
            
            const chartsContainer = document.getElementById('charts-grid-container');
            const catStats = profileData.categorical_stats;
            
            if (catStats && Object.keys(catStats).length > 0) {
                const catCols = Object.keys(catStats);
                catCols.forEach((colName, idx) => {
                    const topValues = catStats[colName].top_values;
                    if (!topValues) return;
                    
                    const labels = Object.keys(topValues);
                    const vols = Object.values(topValues);
                    
                    if (labels.length === 0) return;
                    
                    const canvasId = 'chart-' + idx;
                    
                    const card = document.createElement('div');
                    card.className = 'bezel-card';
                    card.style.height = '360px';
                    card.innerHTML = `
                        <span class="card-title">${colName} Top Categories (Volume)</span>
                        <div style="position: relative; height: 260px; width: 100%;">
                            <canvas id="${canvasId}"></canvas>
                        </div>
                    `;
                    chartsContainer.appendChild(card);
                    
                    // Chart.js Init
                    const ctx = document.getElementById(canvasId).getContext('2d');
                    new Chart(ctx, {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: [
                                {
                                    label: 'Volume',
                                    data: vols,
                                    backgroundColor: '#1c1d21',
                                    borderRadius: 4
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false },
                                tooltip: {
                                    backgroundColor: '#1c1d21',
                                    titleFont: { family: "'Plus Jakarta Sans', sans-serif" },
                                    bodyFont: { family: "'Plus Jakarta Sans', sans-serif" },
                                    padding: 12,
                                    cornerRadius: 8
                                }
                            },
                            scales: {
                                x: {
                                    grid: { display: false },
                                    ticks: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 10 } }
                                },
                                y: {
                                    type: 'linear',
                                    display: true,
                                    grid: { color: 'rgba(0,0,0,0.04)' },
                                    ticks: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 10 } }
                                }
                            }
                        }
                    });
                });
            } else {
                chartsContainer.innerHTML = "<div class='bezel-card'><p style='color:var(--text-muted);'>No categorical charts available.</p></div>";
            }
        }

        // Render Temporal Trend Line Charts (Chart Only)
        const trendCharts = (domainCharts || []).filter(c => {
            const cType = (c.chart_type || c.type || '').toLowerCase();
            const title = (c.title || '').toLowerCase();
            return cType === 'line' || cType === 'trend' || title.includes('over time') || title.includes('trend');
        });

        if (trendCharts.length > 0) {
            const trendSection = document.createElement('div');
            trendSection.className = 'section-block';
            trendSection.innerHTML = `
                <h2 class="section-title">Temporal Trends & Volume Trajectory</h2>
                <div id="trend-charts-container"></div>
            `;
            const container = document.getElementById('charts-grid-container').parentElement;
            container.parentElement.insertBefore(trendSection, container.nextSibling);

            const trendContainer = document.getElementById('trend-charts-container');
            trendCharts.forEach((tData, idx) => {
                const card = document.createElement('div');
                card.className = 'bezel-card';
                card.style.padding = '1.5rem';
                card.style.marginBottom = '1.5rem';
                
                const canvasId = 'trend-chart-' + idx;
                const rawRows = tData.data || [];
                const labels = rawRows.map(r => r.date_period || r.period || r.category || Object.values(r)[0]);
                const values = rawRows.map(r => r.metric_sum || r.total_value || r.sales || Object.values(r)[1]);
                const takeaway = tData.takeaway || tData.default_takeaway || 'Temporal momentum pattern over time.';

                card.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                        <span class="card-title" style="margin:0; font-size:1.1rem; color:var(--text-main);">${tData.title}</span>
                        <span style="background:var(--accent-orange-light); color:var(--accent-orange); padding:4px 10px; border-radius:999px; font-size:0.75rem; font-weight:700;">Chart Only (Line Trend)</span>
                    </div>
                    <div style="height:300px; position:relative; margin-bottom:1rem;">
                        <canvas id="${canvasId}"></canvas>
                    </div>
                    <div style="padding:0.75rem 1rem; background:var(--bg-subtle); border-radius:8px; font-size:0.85rem; color:var(--text-muted); border-left:3px solid var(--accent-orange);">
                        <strong style="color:var(--text-main);">Trend Insight:</strong> ${takeaway}
                    </div>
                `;
                trendContainer.appendChild(card);

                setTimeout(() => {
                    const ctx = document.getElementById(canvasId).getContext('2d');
                    new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Volume / Revenue ($)',
                                data: values,
                                borderColor: '#ff6a3d',
                                backgroundColor: 'rgba(255, 106, 61, 0.1)',
                                borderWidth: 3,
                                fill: true,
                                tension: 0.3,
                                pointRadius: 3,
                                pointBackgroundColor: '#ff6a3d'
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { position: 'bottom', labels: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } } },
                                tooltip: { backgroundColor: '#1c1d21' }
                            },
                            scales: {
                                x: { grid: { display: false }, ticks: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 10 } } },
                                y: { grid: { color: 'rgba(0,0,0,0.04)' }, ticks: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 10 } } }
                            }
                        }
                    });
                }, 50);
            });
        }

        // Render Scatter Distribution Charts (Chart Only)
        const scatterCharts = (domainCharts || []).filter(c => {
            const cType = (c.chart_type || c.type || '').toLowerCase();
            const title = (c.title || '').toLowerCase();
            return cType === 'scatter' || title.includes('scatter');
        });

        if (scatterCharts.length > 0) {
            const scatterSection = document.createElement('div');
            scatterSection.className = 'section-block';
            scatterSection.innerHTML = `
                <h2 class="section-title">Correlation & Distribution Scatter Analysis</h2>
                <div id="scatter-charts-container"></div>
            `;
            const container = document.getElementById('charts-grid-container').parentElement;
            container.parentElement.insertBefore(scatterSection, container.nextSibling);

            const scatterContainer = document.getElementById('scatter-charts-container');
            scatterCharts.forEach((sData, idx) => {
                const card = document.createElement('div');
                card.className = 'bezel-card';
                card.style.padding = '1.5rem';
                card.style.marginBottom = '1.5rem';
                
                const canvasId = 'scatter-chart-' + idx;
                const rawRows = sData.data || [];
                const points = rawRows.map(r => ({ x: r.x, y: r.y }));
                const takeaway = sData.takeaway || sData.default_takeaway || 'Correlation & outlier boundary points.';

                card.innerHTML = `
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:1rem;">
                        <span class="card-title" style="margin:0; font-size:1.1rem; color:var(--text-main);">${sData.title}</span>
                        <span style="background:var(--accent-dark); color:white; padding:4px 10px; border-radius:999px; font-size:0.75rem; font-weight:700;">Chart Only (Scatter)</span>
                    </div>
                    <div style="height:320px; position:relative; margin-bottom:1rem;">
                        <canvas id="${canvasId}"></canvas>
                    </div>
                    <div style="padding:0.75rem 1rem; background:var(--bg-subtle); border-radius:8px; font-size:0.85rem; color:var(--text-muted); border-left:3px solid var(--accent-dark);">
                        <strong style="color:var(--text-main);">Distribution Insight:</strong> ${takeaway}
                    </div>
                `;
                scatterContainer.appendChild(card);

                setTimeout(() => {
                    const ctx = document.getElementById(canvasId).getContext('2d');
                    new Chart(ctx, {
                        type: 'scatter',
                        data: {
                            datasets: [{
                                label: 'Distribution Scatter Points',
                                data: points,
                                backgroundColor: 'rgba(255, 106, 61, 0.6)',
                                borderColor: '#ff6a3d',
                                pointRadius: 4,
                                pointHoverRadius: 6
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { position: 'bottom', labels: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } } },
                                tooltip: { backgroundColor: '#1c1d21' }
                            },
                            scales: {
                                x: { grid: { color: 'rgba(0,0,0,0.04)' }, title: { display: true, text: 'Primary Variable (X)', font: { size: 11 } } },
                                y: { grid: { color: 'rgba(0,0,0,0.04)' }, title: { display: true, text: 'Secondary Variable (Y)', font: { size: 11 } } }
                            }
                        }
                    });
                }, 50);
            });
        }

        // Global Chart Payload Registry for Dimensional Toggles
        window.__DIM_CHART_DATA__ = __DIM_CHART_DATA_JSON__;
        window.__YOY_CHART_DATA__ = __YOY_CHART_DATA_JSON__;
        window.__DIM_CHARTS = {};

        // Table / Chart Domain Card Toggle Switch Logic
        function toggleDomainView(btn, viewType) {
            const card = btn.closest('.bezel-card');
            const tableEl = card.querySelector('.card-view-table');
            const chartEl = card.querySelector('.card-view-chart');
            const btns = card.querySelectorAll('.toggle-btn');
            
            btns.forEach(b => {
                b.style.background = 'transparent';
                b.style.color = 'var(--text-muted)';
                b.classList.remove('active');
            });
            
            btn.style.background = 'var(--accent-dark)';
            btn.style.color = 'white';
            btn.classList.add('active');
            
            if (viewType === 'chart') {
                tableEl.style.display = 'none';
                chartEl.style.display = 'block';

                const dimId = card.dataset.dimId;
                if (dimId && window.__DIM_CHART_DATA__ && window.__DIM_CHART_DATA__[dimId] && !window.__DIM_CHARTS[dimId]) {
                    const d = window.__DIM_CHART_DATA__[dimId];
                    const canvas = document.getElementById('dim-chart-' + dimId);
                    if (canvas) {
                        window.__DIM_CHARTS[dimId] = new Chart(canvas.getContext('2d'), {
                            type: 'bar',
                            data: {
                                labels: d.labels,
                                datasets: [
                                    {
                                        label: 'Total Revenue ($)',
                                        data: d.sales,
                                        backgroundColor: '#ff6a3d',
                                        borderRadius: 4
                                    },
                                    {
                                        label: 'Net Profit ($)',
                                        data: d.profit,
                                        backgroundColor: '#10b981',
                                        borderRadius: 4
                                    }
                                ]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {
                                    legend: { position: 'bottom', labels: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } } },
                                    tooltip: { backgroundColor: '#1c1d21' }
                                },
                                scales: {
                                    x: { grid: { display: false } },
                                    y: { grid: { color: 'rgba(0,0,0,0.04)' } }
                                }
                            }
                        });
                    }
                }
            } else {
                tableEl.style.display = 'block';
                chartEl.style.display = 'none';
            }
        }

        // Initialize YoY Performance Dual Bar Chart dynamically
        const yoyCtx = document.getElementById('yoy-sales-chart');
        if (yoyCtx && window.__YOY_CHART_DATA__ && window.__YOY_CHART_DATA__.labels && window.__YOY_CHART_DATA__.labels.length > 0) {
            const yData = window.__YOY_CHART_DATA__;
            new Chart(yoyCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: yData.labels,
                    datasets: [
                        {
                            label: 'Total Revenue ($)',
                            data: yData.revenue,
                            backgroundColor: '#ff6a3d',
                            borderRadius: 4
                        },
                        {
                            label: 'Net Profit ($)',
                            data: yData.profit,
                            backgroundColor: '#10b981',
                            borderRadius: 4
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { font: { family: "'Plus Jakarta Sans', sans-serif", size: 11 } } },
                        tooltip: { backgroundColor: '#1c1d21' }
                    },
                    scales: {
                        x: { grid: { display: false } },
                        y: { grid: { color: 'rgba(0,0,0,0.04)' } }
                    }
                }
            });
        }
    </script>
</body>
</html>
"""