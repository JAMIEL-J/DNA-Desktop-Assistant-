# skills/data_engine/analyst.py
import logging
from .llm_utils import call_llm_for_json

logger = logging.getLogger('dna.data_engine.analyst')


class DataAnalyst:
    """LLM-powered insight generation. Receives pre-computed profile, never raw data."""

    def analyze(self, profile: dict, findings: list[dict], question: str) -> dict:
        """Generate executive summary, findings, and recommendations."""
        try:
            prompt = self._build_analyst_prompt(profile, findings, question)
            logger.info('Calling LLM for analysis insights...')
            result = call_llm_for_json(prompt)
            if not result:
                logger.warning('LLM returned empty JSON result for analysis.')
                return self._fallback_analysis()

            logger.info('LLM analysis successfully generated.')
            return {
                'executive_summary': result.get('executive_summary', ''),
                'kpis': result.get('kpis', []),
                'drivers': result.get('drivers', []),
                'perfect_storm_segments': result.get('perfect_storm_segments', []),
                'recommendations': result.get('recommendations', []),
            }
        except Exception as e:
            logger.error('DataAnalyst failed: %s', e, exc_info=True)
            return self._fallback_analysis()

    def _format_target_breakdowns(self, breakdowns: dict) -> str:
        """Format target breakdowns for the LLM prompt context."""
        if not breakdowns:
            return ""
            
        target = breakdowns.get('target_column')
        pos_class = breakdowns.get('positive_class')
        baseline = breakdowns.get('baseline_rate', 0.0)
        
        lines = [
            f"Target Column: '{target}' (Positive event: '{pos_class}')",
            f"Baseline Event Rate: {baseline:.2f}% of all rows",
            "Cross-Tabulation Groupings (Categorical Columns vs Target):"
        ]
        
        # Categorical
        for col, rows in breakdowns.get('categorical', {}).items():
            lines.append(f"- Column '{col}':")
            # Limit to top 6 categories to avoid prompt overflow
            for row in rows[:6]:
                lines.append(
                    f"  * Category '{row['category']}': Total Count: {row['total_count']} ({row['pct_of_dataset']:.1f}% of data), "
                    f"Event Count: {row['event_count']} (event rate: {row['event_pct']:.1f}%), "
                    f"Contribution to total events: {row['pct_of_total_events']:.1f}%"
                )
                
        # Numeric cohort means
        numeric_breakdowns = breakdowns.get('numeric', {})
        if numeric_breakdowns:
            lines.append("Numeric Column Means grouped by Target Status:")
            for col, rows in numeric_breakdowns.items():
                lines.append(f"- Column '{col}':")
                for row in rows:
                    lines.append(f"  * Status '{row['target_status']}': Average = {row['mean_val']:.2f}")
                    
        return "\n".join(lines)

    def _build_analyst_prompt(self, profile: dict, findings: list[dict], question: str) -> str:
        """Build profile summary for LLM context."""
        # Schema overview
        schema_parts = []
        for col in profile.get('schema', []):
            schema_parts.append(f"{col['name']} ({col['type']})")
        schema_str = ", ".join(schema_parts)

        # Correlation summary (moderate/strong only)
        corr_summary = []
        corr_matrix = profile.get('correlations', {})
        for c1, values in corr_matrix.items():
            for c2, val in values.items():
                if c1 < c2 and abs(val) > 0.5:
                    corr_summary.append(f"{c1} vs {c2}: {val:.2f}")
        corr_str = ", ".join(corr_summary) if corr_summary else "No strong correlations"

        # Anomalies/patterns
        findings_str = ""
        for f in findings:
            findings_str += f"- [{f['severity']}] {f['column']}: {f['detail']}\n"
        if not findings_str:
            findings_str = "No major anomalies detected."

        target_breakdowns_str = ""
        breakdowns = profile.get('target_breakdowns')
        if breakdowns:
            target_breakdowns_str = (
                "\nTarget Column and Correlation Breakdowns:\n"
                f"{self._format_target_breakdowns(breakdowns)}\n"
            )

        prompt = (
            f"You are a professional business intelligence director and senior data analyst. Generate a structured, data-driven report in JSON format.\n"
            f"Rules:\n"
            f"- Return ONLY a JSON object. No markdown. No backticks. No explanation.\n"
            f"- The response must match the schema exactly:\n"
            f"  {{\n"
            f"    \"executive_summary\": \"string\",\n"
            f"    \"kpis\": [\n"
            f"      {{\"label\": \"string\", \"value\": \"string\", \"detail\": \"string\"}}\n"
            f"    ],\n"
            f"    \"drivers\": [\n"
            f"      {{\n"
            f"        \"trigger_number\": 1,\n"
            f"        \"emoji\": \"string\",\n"
            f"        \"title\": \"string\",\n"
            f"        \"subtitle\": \"string\",\n"
            f"        \"statistics\": [\"string\"],\n"
            f"        \"business_insight\": \"string\",\n"
            f"        \"severity\": \"HIGH|MEDIUM|LOW\"\n"
            f"      }}\n"
            f"    ],\n"
            f"    \"perfect_storm_segments\": [\n"
            f"      {{\"segment\": \"string\", \"total_customers\": \"string\", \"rate\": \"string\", \"business_insight\": \"string\"}}\n"
            f"    ],\n"
            f"    \"recommendations\": [\n"
            f"      {{\"title\": \"string\", \"action\": \"string\", \"rationale\": \"string\"}}\n"
            f"    ]\n"
            f"  }}\n"
            f"- Report Structure & Persona Rules:\n"
            f"  * Act as an Elite Senior BI Director: focus heavily on exact numbers, counts (volumes), and contribution percentages alongside rates.\n"
            f"  * Core KPIs: List 2-3 key metrics (e.g. Total Customer Base, Overall Rate/Value, and a brief description of the impact).\n"
            f"  * Key Drivers / Triggers: Identify 3-5 distinct drivers of the target event. Group findings by 'Trigger #X: Title (Subtitle)'. For example: '🚨 Trigger #1: The Support Ticket \"Red Line\" (Critical Operational Risk)'.\n"
            f"  * For each trigger, provide specific statistics (e.g. churn rates for different ticket cohorts) and a clear 'Business Insight' explaining the root cause or friction point.\n"
            f"  * High-Volatility Segment ('Perfect Storm'): Cross-reference high-risk factors to define 1-2 segments where the target event rate is extreme (e.g. Month-to-Month + Fiber Optic + Electronic Check has 60.37% rate, representing X of Y total events).\n"
            f"  * Strategic Recommendations: Detail 3-4 concrete actions to mitigate the risk, linking each back to a driver with a clear rationale.\n\n"
            f"Data Profile:\n"
            f"- Rows: {profile.get('row_count')}\n"
            f"- Columns: {profile.get('column_count')}\n"
            f"- Schema: {schema_str}\n"
            f"{target_breakdowns_str}"
            f"- Correlations: {corr_str}\n"
            f"- Detected Anomalies/Patterns:\n{findings_str}\n\n"
            f"User's Question: {question}"
        )
        return prompt

    def _fallback_analysis(self) -> dict:
        """Sensible fallback return structure when analysis fails."""
        return {
            'executive_summary': "Data profiled successfully, but detailed analytical insights could not be generated.",
            'kpis': [],
            'drivers': [],
            'perfect_storm_segments': [],
            'recommendations': []
        }
