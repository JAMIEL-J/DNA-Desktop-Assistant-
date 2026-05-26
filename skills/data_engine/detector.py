# skills/data_engine/detector.py
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger('dna.data_engine.detector')


class PatternDetector:
    """Rule-based anomaly and pattern detection. No LLM needed."""

    def detect(self, profile: dict, df_sample: pd.DataFrame) -> list[dict]:
        """Run all detection rules. Returns list of findings."""
        findings = []
        try:
            if df_sample is None or df_sample.empty:
                logger.warning('Empty sample dataframe passed to PatternDetector.')
                return findings

            findings.extend(self._detect_outliers(df_sample))
            findings.extend(self._detect_target_column(profile))
            findings.extend(self._detect_high_cardinality(profile))
            findings.extend(self._detect_date_columns(profile, df_sample))
            findings.extend(self._detect_null_patterns(profile))
            findings.extend(self._detect_null_patterns_in_sample(df_sample))
            findings.extend(self._detect_class_imbalance(profile, df_sample))
            findings.extend(self._detect_skewness(profile))
            findings.extend(self._detect_constant_columns(profile))
            
            logger.info('Detection complete: found %d patterns/anomalies', len(findings))
        except Exception as e:
            logger.error('Detection failed: %s', e, exc_info=True)
            
        return findings

    def _detect_outliers(self, df_sample: pd.DataFrame) -> list[dict]:
        """IQR method (1.5x fence) to detect numeric outliers."""
        findings = []
        numeric_cols = df_sample.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            series = df_sample[col].dropna()
            if len(series) < 5:
                continue
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue
            lower_fence = q1 - 1.5 * iqr
            upper_fence = q3 + 1.5 * iqr
            outliers = series[(series < lower_fence) | (series > upper_fence)]
            if len(outliers) > 0:
                pct = len(outliers) / len(series)
                severity = 'MEDIUM' if pct > 0.05 else 'LOW'
                findings.append({
                    'type': 'outlier',
                    'column': col,
                    'detail': f"{col} has {len(outliers)} outliers (values outside [{lower_fence:.1f}, {upper_fence:.1f}])",
                    'severity': severity
                })
        return findings

    def _detect_target_column(self, profile: dict) -> list[dict]:
        """Detect binary target columns or columns likely to be the classification label."""
        findings = []
        common_targets = {'churn', 'target', 'label', 'class', 'clicked', 'purchased', 'default', 'survived', 'status'}
        for col in profile['schema']:
            name_lower = col['name'].lower()
            if col['uniques'] == 2:
                if any(t in name_lower for t in common_targets):
                    findings.append({
                        'type': 'target_column',
                        'column': col['name'],
                        'detail': f"{col['name']} appears to be the target variable (binary classes detected).",
                        'severity': 'LOW'
                    })
                    return findings  # Return first detected target
        
        # Fallback to name search
        for col in profile['schema']:
            name_lower = col['name'].lower()
            if name_lower in common_targets:
                findings.append({
                    'type': 'target_column',
                    'column': col['name'],
                    'detail': f"{col['name']} appears to be the target variable based on name similarity.",
                    'severity': 'LOW'
                })
                return findings
        return findings

    def _detect_high_cardinality(self, profile: dict) -> list[dict]:
        """Detect columns with unique/total ratio > 0.9, likely IDs."""
        findings = []
        row_count = profile['row_count']
        if row_count <= 5:
            return findings
        for col in profile['schema']:
            uniques = col['uniques']
            ratio = uniques / row_count
            if ratio > 0.9 and uniques > 5:
                findings.append({
                    'type': 'high_cardinality',
                    'column': col['name'],
                    'detail': f"{col['name']} is likely an ID column ({uniques} unique values, {ratio*100:.1f}% unique).",
                    'severity': 'LOW'
                })
        return findings

    def _detect_date_columns(self, profile: dict, df_sample: pd.DataFrame) -> list[dict]:
        """Detect datetime columns using type and regex/parse check."""
        findings = []
        date_keywords = {'date', 'time', 'timestamp', 'year', 'month', 'created', 'updated'}
        for col in df_sample.columns:
            name_lower = col.lower()
            is_dt = pd.api.types.is_datetime64_any_dtype(df_sample[col])
            if is_dt:
                findings.append({
                    'type': 'date_column',
                    'column': col,
                    'detail': f"{col} detected as datetime column.",
                    'severity': 'LOW'
                })
                continue
                
            if df_sample[col].dtype == 'object':
                sample_series = df_sample[col].dropna().head(10)
                if len(sample_series) == 0:
                    continue
                if any(kw in name_lower for kw in date_keywords):
                    try:
                        pd.to_datetime(sample_series, errors='raise')
                        findings.append({
                            'type': 'date_column',
                            'column': col,
                            'detail': f"{col} detected as datetime column.",
                            'severity': 'LOW'
                        })
                    except (ValueError, TypeError):
                        pass
        return findings

    def _detect_null_patterns(self, profile: dict) -> list[dict]:
        """Detect missing value proportions and patterns."""
        findings = []
        nulls = profile.get('null_summary', {})
        for col, stats in nulls.items():
            if stats['null_pct'] > 10.0:
                severity = 'HIGH' if stats['null_pct'] > 50.0 else 'MEDIUM'
                findings.append({
                    'type': 'null_pattern',
                    'column': col,
                    'detail': f"{col} has a high missingness rate of {stats['null_pct']:.1f}% ({stats['null_count']} missing rows).",
                    'severity': severity
                })
        return findings

    def _detect_null_patterns_in_sample(self, df_sample: pd.DataFrame) -> list[dict]:
        """Detect co-occurrence of null values."""
        findings = []
        null_cols = [c for c in df_sample.columns if df_sample[c].isnull().any()]
        if len(null_cols) < 2:
            return findings

        # Calculate correlation of null indicators
        null_df = df_sample[null_cols].isnull().astype(int)
        corr = null_df.corr().fillna(0.0)
        for i in range(len(null_cols)):
            for j in range(i + 1, len(null_cols)):
                c1, c2 = null_cols[i], null_cols[j]
                val = corr.loc[c1, c2]
                if val > 0.99:
                    findings.append({
                        'type': 'null_correlation',
                        'column': f"{c1} & {c2}",
                        'detail': f"Missing values in {c1} and {c2} correlate perfectly (100%). They may be missing for the same reason.",
                        'severity': 'MEDIUM'
                    })
        return findings

    def _detect_class_imbalance(self, profile: dict, df_sample: pd.DataFrame) -> list[dict]:
        """Detect class imbalance in categorical columns (minority class < 20%)."""
        findings = []
        for col in profile['schema']:
            if 1 < col['uniques'] <= 5:
                counts = df_sample[col['name']].dropna().value_counts()
                if len(counts) < 2:
                    continue
                total = counts.sum()
                proportions = counts / total
                min_pct = proportions.values[-1] * 100.0
                
                if min_pct < 20.0:
                    details = ", ".join([f"{val}: {pct*100:.1f}%" for val, pct in proportions.items()])
                    findings.append({
                        'type': 'class_imbalance',
                        'column': col['name'],
                        'detail': f"{col['name']} has class imbalance: {details}",
                        'severity': 'MEDIUM' if min_pct < 10.0 else 'LOW'
                    })
        return findings

    def _detect_skewness(self, profile: dict) -> list[dict]:
        """Detect skewed numerical columns from skewness statistic."""
        findings = []
        num_stats = profile.get('numeric_stats', {})
        for col, stats in num_stats.items():
            skew = stats.get('skew', 0.0)
            if abs(skew) > 1.0:
                direction = "right-skewed" if skew > 0 else "left-skewed"
                findings.append({
                    'type': 'skewness',
                    'column': col,
                    'detail': f"{col} is highly {direction} (skewness: {skew:.2f}).",
                    'severity': 'LOW'
                })
        return findings

    def _detect_constant_columns(self, profile: dict) -> list[dict]:
        """Detect constant columns (only 1 unique value)."""
        findings = []
        for col in profile['schema']:
            if col['uniques'] == 1:
                findings.append({
                    'type': 'constant_column',
                    'column': col['name'],
                    'detail': f"{col['name']} is constant (only 1 unique value) — consider dropping this column.",
                    'severity': 'LOW'
                })
        return findings
