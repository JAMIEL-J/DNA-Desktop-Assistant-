# skills/data_engine/data_cleaner.py
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger('dna.data_engine.data_cleaner')


class DataCleaner:
    """Detects data quality issues and provides LLM-backed pandas cleaning code suggestions."""

    def scan(self, df_sample: pd.DataFrame, profile: dict) -> list[dict]:
        """Returns list of cleaning suggestions."""
        issues = []
        try:
            if df_sample is None or df_sample.empty:
                return issues

            issues.extend(self._check_duplicates(df_sample))
            issues.extend(self._check_mixed_types(df_sample))
            issues.extend(self._check_whitespace(df_sample))
            issues.extend(self._check_inconsistent_categories(df_sample))

            logger.info('Clean scan complete: found %d quality issues', len(issues))
        except Exception as e:
            logger.error('DataCleaner scan failed: %s', e, exc_info=True)

        return issues

    def _check_duplicates(self, df_sample: pd.DataFrame) -> list[dict]:
        """Check for duplicated rows."""
        dup_count = df_sample.duplicated().sum()
        if dup_count > 0:
            return [{
                'column': 'Dataset',
                'issue_type': 'duplicated_rows',
                'count': int(dup_count),
                'suggestion': f"Found {dup_count} duplicate rows. Consider dropping duplicates using df.drop_duplicates()."
            }]
        return []

    def _check_mixed_types(self, df_sample: pd.DataFrame) -> list[dict]:
        """Check for columns with mixed types."""
        issues = []
        for col in df_sample.columns:
            types = df_sample[col].dropna().apply(lambda x: type(x).__name__).unique()
            if len(types) > 1:
                issues.append({
                    'column': col,
                    'issue_type': 'mixed_types',
                    'count': len(types),
                    'suggestion': f"Column '{col}' has mixed data types: {', '.join(types)}. Consider casting to a single type using df['{col}'].astype()."
                })
        return issues

    def _check_whitespace(self, df_sample: pd.DataFrame) -> list[dict]:
        """Check for leading/trailing whitespaces in string columns."""
        issues = []
        string_cols = df_sample.select_dtypes(include=['object']).columns
        for col in string_cols:
            try:
                ws_mask = df_sample[col].astype(str).str.strip() != df_sample[col].astype(str)
                ws_count = (ws_mask & df_sample[col].notna()).sum()
                if ws_count > 0:
                    issues.append({
                        'column': col,
                        'issue_type': 'leading_trailing_whitespace',
                        'count': int(ws_count),
                        'suggestion': f"Column '{col}' contains {ws_count} values with leading or trailing whitespace. Consider stripping whitespaces using df['{col}'] = df['{col}'].str.strip()."
                    })
            except Exception as e:
                logger.warning('Whitespace check failed for column %s: %s', col, e)
        return issues

    def _check_inconsistent_categories(self, df_sample: pd.DataFrame) -> list[dict]:
        """Check for categorical values differing only by case/whitespace."""
        issues = []
        string_cols = df_sample.select_dtypes(include=['object']).columns
        for col in string_cols:
            try:
                values = df_sample[col].dropna().astype(str).unique()
                if len(values) > 1:
                    lowered_values = [v.lower().strip() for v in values]
                    unique_lowered = set(lowered_values)
                    if len(unique_lowered) < len(values):
                        issues.append({
                            'column': col,
                            'issue_type': 'inconsistent_casing',
                            'count': len(values) - len(unique_lowered),
                            'suggestion': f"Column '{col}' contains values with inconsistent casing/whitespace. Consider standardizing casing using df['{col}'] = df['{col}'].str.lower().str.strip()."
                        })
            except Exception as e:
                logger.warning('Categorical consistency check failed for column %s: %s', col, e)
        return issues

    def suggest_fixes(self, issues: list[dict], profile: dict) -> list[dict]:
        """LLM generates context-aware pandas fix recommendations."""
        if not issues:
            return []

        # 1. Format issues into prompt
        issues_str = ""
        for issue in issues:
            issues_str += f"- Column: {issue['column']}, Issue: {issue['issue_type']}, Count: {issue['count']}, Base Suggestion: {issue['suggestion']}\n"

        prompt = (
            f"You are a professional Python data cleaning expert. I have scanned a dataset and found the following quality issues:\n"
            f"{issues_str}\n"
            f"Please review these issues and generate a JSON list of detailed context-aware fix recommendations.\n"
            f"Rules:\n"
            f"- Return ONLY a JSON list of objects matching the schema exactly:\n"
            f"  [\n"
            f"    {{\n"
            f"      \"column\": \"string\",\n"
            f"      \"issue_type\": \"string\",\n"
            f"      \"detailed_recommendation\": \"string\",\n"
            f"      \"code_snippet\": \"string\"\n"
            f"    }}\n"
            f"  ]\n"
            f"- Do NOT use markdown. Do NOT use backticks. Do NOT explain anything else.\n"
            f"- Provide the actual pandas code snippet required to resolve the issue."
        )

        try:
            from .llm_utils import call_llm_for_json
            results = call_llm_for_json(prompt)
            if isinstance(results, list):
                return results
            if isinstance(results, dict) and 'fixes' in results:
                return results['fixes']
            if isinstance(results, dict) and results:
                return [results]
        except Exception as e:
            logger.warning('Failed to generate LLM cleaning recommendations: %s', e)

        # 2. Baseline fallback suggestions
        FALLBACK_SNIPPETS = {
            'leading_trailing_whitespace': lambda col: f"df['{col}'] = df['{col}'].str.strip()",
            'duplicated_rows': lambda col: "df = df.drop_duplicates()",
            'mixed_types': lambda col: f"df['{col}'] = pd.to_numeric(df['{col}'], errors='coerce')",
            'inconsistent_casing': lambda col: f"df['{col}'] = df['{col}'].str.lower().str.strip()",
        }
        fallback_fixes = []
        for issue in issues:
            snippet_fn = FALLBACK_SNIPPETS.get(issue['issue_type'], lambda col: f"df['{col}'] = ...")
            fallback_fixes.append({
                'column': issue['column'],
                'issue_type': issue['issue_type'],
                'detailed_recommendation': issue['suggestion'],
                'code_snippet': snippet_fn(issue['column'])
            })
        return fallback_fixes
