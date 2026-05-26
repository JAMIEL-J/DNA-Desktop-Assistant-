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
                'findings': result.get('findings', []),
                'recommendations': result.get('recommendations', []),
            }
        except Exception as e:
            logger.error('DataAnalyst failed: %s', e, exc_info=True)
            return self._fallback_analysis()

    def _build_analyst_prompt(self, profile: dict, findings: list[dict], question: str) -> str:
        """Build ~200 token profile summary for LLM context."""
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

        prompt = (
            f"You are a professional business intelligence and data analyst. Generate a structured data analysis report in JSON format.\n"
            f"Rules:\n"
            f"- Return ONLY a JSON object. No markdown. No backticks. No explanation.\n"
            f"- The response must match the schema exactly:\n"
            f"  {{\n"
            f"    \"executive_summary\": \"string\",\n"
            f"    \"findings\": [\n"
            f"      {{\"title\": \"string\", \"detail\": \"string\", \"impact\": \"HIGH|MEDIUM|LOW\"}}\n"
            f"    ],\n"
            f"    \"recommendations\": [\n"
            f"      {{\"action\": \"string\", \"rationale\": \"string\", \"priority\": 1}}\n"
            f"    ]\n"
            f"  }}\n"
            f"- Keep it highly professional, insightful, and concise.\n\n"
            f"Data Profile:\n"
            f"- Rows: {profile.get('row_count')}\n"
            f"- Columns: {profile.get('column_count')}\n"
            f"- Schema: {schema_str}\n"
            f"- Correlations: {corr_str}\n"
            f"- Detected Anomalies/Patterns:\n{findings_str}\n\n"
            f"User's Question: {question}"
        )
        return prompt

    def _fallback_analysis(self) -> dict:
        """Sensible fallback return structure when analysis fails."""
        return {
            'executive_summary': "Data profiled successfully, but detailed analytical insights could not be generated.",
            'findings': [],
            'recommendations': []
        }
