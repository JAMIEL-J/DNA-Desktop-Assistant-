# skills/data_engine/analyst.py
import json
import logging
import re
from typing import Dict, List, Any, Optional
from .llm_utils import call_llm_for_json

logger = logging.getLogger('dna.data_engine.analyst')


ANALYST_RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "executive_summary": {"type": "STRING"},
        "kpis": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "label": {"type": "STRING"},
                    "value": {"type": "STRING"},
                    "detail": {"type": "STRING"},
                },
                "required": ["label", "value", "detail"],
            },
        },
        "drivers": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "trigger_number": {"type": "INTEGER"},
                    "title": {"type": "STRING"},
                    "subtitle": {"type": "STRING"},
                    "statistics": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "business_insight": {"type": "STRING"},
                    "severity": {"type": "STRING", "enum": ["HIGH", "MEDIUM", "LOW"]},
                },
                "required": ["trigger_number", "title", "statistics", "business_insight", "severity"],
            },
        },
        "outliers_and_anomalies": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "column": {"type": "STRING"},
                    "severity": {"type": "STRING", "enum": ["HIGH", "MEDIUM", "LOW"]},
                    "outlier_count": {"type": "INTEGER"},
                    "volume_impact": {"type": "STRING"},
                    "business_insight": {"type": "STRING"},
                },
                "required": ["column", "severity", "outlier_count", "volume_impact", "business_insight"],
            },
        },
        "compound_segments": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "segment": {"type": "STRING"},
                    "total_records": {"type": "STRING"},
                    "rate_or_value": {"type": "STRING"},
                    "business_insight": {"type": "STRING"},
                },
                "required": ["segment", "total_records", "rate_or_value", "business_insight"],
            },
        },
        "recommendations": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "action": {"type": "STRING"},
                    "rationale": {"type": "STRING"},
                },
                "required": ["title", "action", "rationale"],
            },
        },
        "chart_takeaways": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "chart_id": {"type": "STRING"},
                    "takeaway": {"type": "STRING"},
                },
                "required": ["chart_id", "takeaway"],
            },
        },
    },
    "required": ["executive_summary", "kpis", "drivers", "outliers_and_anomalies", "compound_segments", "recommendations"],
}


class DataAnalyst:
    """LLM-powered insight generation. Receives pre-computed profile & stats, never raw data."""

    def __init__(self):
        self._stat_registry: dict[str, str] = {}
        self._stat_counter = 0

    def _next_id(self, text: str) -> str:
        """Register a stat, return its citation ID, e.g. '[S3]'."""
        self._stat_counter += 1
        sid = f"S{self._stat_counter}"
        self._stat_registry[sid] = text
        return f"[{sid}]"

    def analyze(self, profile: dict, findings: list[dict], question: str, domain_info: Optional[dict] = None) -> dict:
        """Generate executive summary, findings, outliers, and recommendations."""
        try:
            self._stat_registry = {}
            self._stat_counter = 0

            prompt = self._build_analyst_prompt(profile, findings, question, domain_info)
            logger.info('Calling LLM for enriched analysis insights...')
            result = call_llm_for_json(prompt, schema=ANALYST_RESPONSE_SCHEMA)
            if not result:
                logger.warning('LLM returned empty JSON result for analysis.')
                return self._fallback_analysis()

            invalid = self._validate_citations(result)
            if invalid:
                logger.warning(
                    'Analysis returned %d citation(s) not present in stat registry: %s',
                    len(invalid), invalid
                )

            logger.info('LLM analysis successfully generated.')
            return {
                'executive_summary': result.get('executive_summary', ''),
                'kpis': result.get('kpis', []),
                'drivers': result.get('drivers', []),
                'outliers_and_anomalies': result.get('outliers_and_anomalies', []),
                'compound_segments': result.get('compound_segments', []),
                'recommendations': result.get('recommendations', []),
                'chart_takeaways': result.get('chart_takeaways', [])
            }
        except Exception as e:
            logger.error('DataAnalyst failed: %s', e, exc_info=True)
            return self._fallback_analysis()

    def _validate_citations(self, result: dict) -> list[str]:
        """Return any [Sxx] citation IDs in the response that aren't in the registry."""
        blob = json.dumps(result)
        cited = set(re.findall(r'\[S\d+\]', blob))
        valid = {f"[{k}]" for k in self._stat_registry}
        return sorted(cited - valid)

    def _format_target_breakdowns(self, breakdowns: dict) -> str:
        """Format target breakdowns for the LLM prompt context."""
        if not breakdowns:
            return ""

        target = breakdowns.get('target_column')
        pos_class = breakdowns.get('positive_class')
        baseline = breakdowns.get('baseline_rate', 0.0)

        baseline_id = self._next_id(f"Baseline event rate for '{target}': {baseline:.2f}%")
        lines = [
            f"Target Column: '{target}' (Positive event: '{pos_class}')",
            f"{baseline_id} Baseline Event Rate: {baseline:.2f}% of all rows",
            "Cross-Tabulation Groupings (Categorical Columns vs Target):"
        ]

        for col, rows in breakdowns.get('categorical', {}).items():
            lines.append(f"- Column '{col}':")
            for row in rows[:6]:
                stat_text = (
                    f"Category '{row['category']}' in '{col}': Total {row['total_count']} "
                    f"({row['pct_of_dataset']:.1f}% of data), Event rate {row['event_pct']:.1f}%, "
                    f"contributes {row['pct_of_total_events']:.1f}% of total events"
                )
                sid = self._next_id(stat_text)
                lines.append(
                    f"  * {sid} Category '{row['category']}': Total Count: {row['total_count']} "
                    f"({row['pct_of_dataset']:.1f}% of data), "
                    f"Event Count: {row['event_count']} (event rate: {row['event_pct']:.1f}%), "
                    f"Contribution to total events: {row['pct_of_total_events']:.1f}%"
                )

        numeric_breakdowns = breakdowns.get('numeric', {})
        if numeric_breakdowns:
            lines.append("Numeric Column Means grouped by Target Status:")
            for col, rows in numeric_breakdowns.items():
                lines.append(f"- Column '{col}':")
                for row in rows:
                    sid = self._next_id(f"Mean '{col}' for status '{row['target_status']}': {row['mean_val']:.2f}")
                    lines.append(f"  * {sid} Status '{row['target_status']}': Average = {row['mean_val']:.2f}")

        return "\n".join(lines)

    def _format_numeric_stats(self, num_stats: dict) -> str:
        """Format detailed numerical statistics and outlier fences for LLM context."""
        if not num_stats:
            return "No numerical statistics available."

        lines = []
        for col, st in num_stats.items():
            mean_val = st.get('mean', 0.0)
            median_val = st.get('median', 0.0)
            std_val = st.get('std', 0.0)
            min_val = st.get('min', 0.0)
            max_val = st.get('max', 0.0)
            skew_val = st.get('skew', 0.0)

            col_clean = col.lower().strip()
            is_binary = (min_val == 0.0 and max_val == 1.0) or any(k in col_clean for k in ['senior', 'is_', 'has_', 'flag_', 'opt_'])

            if is_binary:
                penetration_pct = mean_val * 100.0 if mean_val <= 1.0 else mean_val
                sid_summary = self._next_id(
                    f"Column '{col}' (Binary Cohort Flag): Count Ratio / Penetration Rate={penetration_pct:.2f}% "
                    f"(1 = Active/Yes Cohort, 0 = Inactive/No Cohort)"
                )
                lines.append(f"- {sid_summary} Column '{col}' (Binary Indicator Cohort): Count Average / Penetration Rate={penetration_pct:.2f}% of population (1=Yes, 0=No)")
                continue

            outlier_cnt = st.get('outlier_count', 0)
            outlier_pct = st.get('outlier_pct', 0.0)
            impact_pct = st.get('outlier_impact_pct', 0.0)
            extremes = st.get('top_extremes', [])

            sid_summary = self._next_id(
                f"Column '{col}': Mean={mean_val:.2f}, Median={median_val:.2f}, Std={std_val:.2f}, "
                f"Min={min_val:.2f}, Max={max_val:.2f}, Skewness={skew_val:.2f}"
            )
            lines.append(f"- {sid_summary} Column '{col}': Mean={mean_val:.2f}, Median={median_val:.2f}, Range=[{min_val:.2f}, {max_val:.2f}]")

            if outlier_cnt > 0:
                sid_outlier = self._next_id(
                    f"Column '{col}' Outlier Summary: {outlier_cnt} outliers ({outlier_pct:.1f}% of data). "
                    f"Outliers represent {impact_pct:.1f}% of total sum volume. Top extremes: {extremes[:10]}"
                )
                lines.append(
                    f"  * {sid_outlier} Outlier Volume Impact: {outlier_cnt} outliers ({outlier_pct:.1f}% of rows) "
                    f"contribute {impact_pct:.1f}% of total column volume. Top Extremes: {extremes[:10]}"
                )

        return "\n".join(lines)

    def _format_domain_aggregations(self, domain_aggs: dict) -> str:
        """Format domain enterprise financial aggregations for LLM context."""
        if not domain_aggs:
            return ""

        lines = ["Domain Enterprise Aggregations & Profitability Metrics:"]
        
        tot_sales = domain_aggs.get('total_sales')
        tot_profit = domain_aggs.get('total_profit')
        margin_pct = domain_aggs.get('blended_margin_pct')
        avg_disc = domain_aggs.get('avg_discount_pct')

        if tot_sales is not None:
            sid_s = self._next_id(f"Total Revenue (Sales): ${tot_sales:,.2f}")
            lines.append(f"- {sid_s} Total Company Revenue (Sales): ${tot_sales:,.2f}")

        if tot_profit is not None:
            sid_p = self._next_id(f"Total Net Profit: ${tot_profit:,.2f}")
            lines.append(f"- {sid_p} Total Company Net Profit: ${tot_profit:,.2f}")

        if margin_pct is not None:
            sid_m = self._next_id(f"Blended Profit Margin: {margin_pct:.2f}%")
            lines.append(f"- {sid_m} Overall Blended Profit Margin: {margin_pct:.2f}%")

        if avg_disc is not None:
            sid_d = self._next_id(f"Average Discount Rate: {avg_disc:.2f}%")
            lines.append(f"- {sid_d} Overall Average Discount Rate: {avg_disc:.2f}%")

        loss_cnt = domain_aggs.get('loss_orders_count')
        loss_amt = domain_aggs.get('total_loss_amount')
        if loss_cnt and loss_amt:
            sid_loss = self._next_id(f"Loss-Making Orders: {loss_cnt} orders totaling ${abs(loss_amt):,.2f} in net profit loss")
            lines.append(f"- {sid_loss} Cumulative Loss-Making Orders: {loss_cnt} orders resulted in ${abs(loss_amt):,.2f} net profit loss")

        high_disc_cnt = domain_aggs.get('high_discount_orders')
        high_disc_prof = domain_aggs.get('high_discount_profit')
        if high_disc_cnt and high_disc_prof:
            sid_disc_loss = self._next_id(f"High Discount Orders (>=30%): {high_disc_cnt} orders yielding ${high_disc_prof:,.2f} net profit")
            lines.append(f"- {sid_disc_loss} Impact of High Discount (>=30%): {high_disc_cnt} orders resulted in total profit/loss of ${high_disc_prof:,.2f}")

        dim_brk = domain_aggs.get('dimensional_breakdowns', {})
        if dim_brk:
            lines.append("Dimensional Profitability & Revenue Breakdown:")
            for dim_name, rows in dim_brk.items():
                lines.append(f"  * Dimension '{dim_name}':")
                for r in rows:
                    cat = r['category']
                    s_val = r.get('sales', 0.0)
                    p_val = r.get('profit', 0.0)
                    m_val = r.get('margin_pct', 0.0)
                    sid_r = self._next_id(f"Dimension '{dim_name}' Category '{cat}': Sales=${s_val:,.2f}, Profit=${p_val:,.2f}, Margin={m_val:.2f}%")
                    lines.append(f"    - {sid_r} Category '{cat}': Sales=${s_val:,.2f}, Profit=${p_val:,.2f}, Profit Margin={m_val:.2f}%")

        return "\n".join(lines)

    def _get_domain_framework(self, domain: str) -> str:
        """Return domain-specific analytical framework guidelines for the LLM prompt."""
        domain_lower = (domain or 'general').lower()
        
        if 'sales' in domain_lower or 'e-commerce' in domain_lower:
            return """DOMAINS-SPECIFIC ANALYTICAL FRAMEWORK (SALES & E-COMMERCE):
- Perform margin decomposition: analyze top-line revenue vs net profit yield across categories and sub-categories.
- Evaluate discount elasticity: examine how heavy discounting (>=30%) impacts unit margins and total net profit.
- Analyze regional & fulfillment efficiency: compare shipping modes and regional sales distributions for profit erosion.
- Assess customer segment performance: identify high-margin vs loss-leading customer segments."""

        elif 'churn' in domain_lower or 'retention' in domain_lower:
            return """DOMAINS-SPECIFIC ANALYTICAL FRAMEWORK (CUSTOMER CHURN & RETENTION):
- Evaluate tenure volatility: identify high-risk tenure cohorts and early churn inflection points.
- Analyze monthly charges & ARPU risk: quantify total revenue at risk from churned contracts.
- Assess contract & payment channel risks: compare contract terms (month-to-month vs 2-year) and payment methods.
- Highlight service attachment impact: analyze how tech support, security, or streaming add-ons correlate with retention."""

        elif 'finance' in domain_lower or 'accounting' in domain_lower:
            return """DOMAINS-SPECIFIC ANALYTICAL FRAMEWORK (FINANCE & ACCOUNTING):
- Evaluate transaction risk concentration: identify extreme debit/credit outlier distributions.
- Analyze interest & fee yields: assess interest rates, balance bands, and default probabilities.
- Assess capital allocation & liquidity: review asset/liability balances and loan performance bands."""

        elif 'hr' in domain_lower or 'people' in domain_lower:
            return """DOMAINS-SPECIFIC ANALYTICAL FRAMEWORK (HR & PEOPLE ANALYTICS):
- Evaluate turnover & attrition drivers: analyze exit rates across departments, roles, and tenure bands.
- Analyze salary equity & compensation bands: cross-examine pay scales against performance ratings and tenure.
- Assess engagement & satisfaction impact: correlate work-life balance and satisfaction scores with retention."""

        else:
            return """DOMAINS-SPECIFIC ANALYTICAL FRAMEWORK (GENERAL BUSINESS ANALYTICS):
- Evaluate volume vs profitability trade-offs across dimensions.
- Identify primary variance drivers, concentration risks, and outlier volume impacts.
- Provide actionable operational recommendations to optimize efficiency and unit economics."""

    def _build_analyst_prompt(self, profile: dict, findings: list[dict], question: str, domain_info: Optional[dict] = None) -> str:
        """Build profile summary for LLM context."""
        schema_parts = []
        for col in profile.get('schema', []):
            schema_parts.append(f"{col['name']} ({col['type']})")
        schema_str = ", ".join(schema_parts)

        domain = domain_info.get('domain', 'general') if domain_info else 'general'
        domain_name = domain_info.get('domain_name', 'General Business Analytics') if domain_info else 'General Analytics'
        domain_framework = self._get_domain_framework(domain)

        num_stats_str = self._format_numeric_stats(profile.get('numeric_stats', {}))
        domain_aggs_str = self._format_domain_aggregations(profile.get('domain_aggregations', {}))

        corr_summary = []
        corr_matrix = profile.get('correlations', {})
        for c1, values in corr_matrix.items():
            for c2, val in values.items():
                if c1 < c2 and abs(val) > 0.5:
                    sid = self._next_id(f"Correlation {c1} vs {c2}: {val:.2f}")
                    corr_summary.append(f"{sid} {c1} vs {c2}: {val:.2f}")
        corr_str = ", ".join(corr_summary) if corr_summary else "No strong correlations"

        findings_str = ""
        for f in findings:
            sid = self._next_id(f"[{f['severity']}] {f['column']}: {f['detail']}")
            findings_str += f"- {sid} [{f['severity']}] {f['column']}: {f['detail']}\n"
        if not findings_str:
            findings_str = "No major anomalies detected."

        target_breakdowns_str = ""
        breakdowns = profile.get('target_breakdowns')
        if breakdowns:
            target_breakdowns_str = self._format_target_breakdowns(breakdowns)

        prompt = f"""You are a Principal Lead Data Analyst performing an executive-level business analysis in the field of {domain_name}.
User Query / Directive: "{question}"

{domain_framework}

DATASET PROFILE SUMMARY:
Row Count: {profile.get('row_count', 0)}
Column Count: {profile.get('column_count', 0)}
Schema: {schema_str}

{domain_aggs_str}

STATISTICAL REGISTRY & OUTLIER VOLUME IMPACT:
{num_stats_str}

{target_breakdowns_str}

STRONG CORRELATIONS:
{corr_str}

ANOMALY & OUTLIER FINDINGS:
{findings_str}

CRITICAL RULES FOR YOUR ANALYSIS:
1. Every numeric metric, KPI, percentage, or statistical claim in your response MUST cite its source statement from the Registry above using '[Sxx]' format.
2. In 'executive_summary', write a COMPREHENSIVE 4-PARAGRAPH HUMAN-LIKE BRIEFING suitable for voice narration:
   - Paragraph 1 (Financial Health & Scale): Outline top-line volume/revenue, net profit yield, blended margin, and dataset scope.
   - Paragraph 2 (Critical Risk Drivers): Detail profit erosion triggers, heavy discounting impact, or high-risk churn/attrition cohorts.
   - Paragraph 3 (Dimensional Disparities): Explain key category, regional, or segment variations in performance.
   - Paragraph 4 (Strategic Action Plan): Summarize the top 2-3 strategic priorities derived directly from the analysis.
   Make the summary thorough and natural for TTS voice engines (no raw markdown headings inside executive_summary, plain paragraphs separated by blank lines).
3. In 'kpis', include ALL key performance indicators (e.g. Total Revenue, Total Net Profit, Blended Margin %, High Discount Loss Impact, Loss-Making Orders Count).
4. In 'drivers', provide AT LEAST 5 deep, non-obvious business insights explaining profitability or risk variation across dimensions.
5. In 'outliers_and_anomalies', extract extreme values, volume impact percentages, and risk highlights.
6. In 'recommendations', provide AT LEAST 5 actionable, high-impact business recommendations.

Formulate your analysis according to the ANALYST_RESPONSE_SCHEMA JSON format. Return ONLY valid JSON.
"""
        return prompt


    def _fallback_analysis(self) -> dict:

        """Sensible fallback return structure when analysis fails."""
        return {
            'executive_summary': "Data profiled successfully, but detailed analytical insights could not be generated.",
            'kpis': [],
            'drivers': [],
            'outliers_and_anomalies': [],
            'compound_segments': [],
            'recommendations': [],
            'chart_takeaways': []
        }
