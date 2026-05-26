# skills/data_engine/chart_engine.py
import logging
from pathlib import Path
import matplotlib
import numpy as np
import pandas as pd

# Switch backend to Agg for thread-safe headless image generation
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger('dna.data_engine.chart_engine')


class ChartEngine:
    """Auto-generates visual charts based on dataset profiles, types, and anomalies."""

    def __init__(self):
        # Configure overall professional styling properties
        plt.style.use('dark_background')
        plt.rcParams['figure.facecolor'] = '#0f172a'  # slate-900
        plt.rcParams['axes.facecolor'] = '#1e293b'    # slate-800
        plt.rcParams['axes.edgecolor'] = '#334155'    # slate-700
        plt.rcParams['grid.color'] = '#334155'
        plt.rcParams['xtick.color'] = '#94a3b8'       # slate-400
        plt.rcParams['ytick.color'] = '#94a3b8'
        plt.rcParams['text.color'] = '#e2e8f0'        # slate-200

    def generate(self, df_sample: pd.DataFrame, profile: dict,
                 findings: list[dict], output_dir: Path) -> list[str]:
        """Generate relevant visualization charts. Returns list of absolute PNG paths."""
        charts = []
        try:
            if df_sample is None or df_sample.empty:
                logger.warning('Empty dataframe passed to ChartEngine. Skipping visualization.')
                return charts

            output_dir.mkdir(parents=True, exist_ok=True)
            numeric_cols = df_sample.select_dtypes(include=[np.number]).columns.tolist()
            categorical_cols = df_sample.select_dtypes(include=['object', 'category']).columns.tolist()

            # 1. Correlation Heatmap (if 3+ numeric columns)
            if len(numeric_cols) >= 3:
                try:
                    plt.figure(figsize=(8, 6))
                    corr = df_sample[numeric_cols].corr().fillna(0.0)
                    sns.heatmap(
                        corr, annot=True, cmap="coolwarm", fmt=".2f",
                        vmin=-1, vmax=1, cbar=True, square=True
                    )
                    plt.title("Numerical Correlation Matrix", pad=15)
                    plt.tight_layout()
                    path = output_dir / "correlation_heatmap.png"
                    plt.savefig(path, facecolor='#0f172a', bbox_inches='tight')
                    plt.close()
                    charts.append(str(path.resolve()))
                except Exception as e:
                    logger.warning('Failed to generate correlation matrix: %s', e)

            # 2. Distribution Histograms for Top Numeric Columns (max 3)
            for col in numeric_cols[:3]:
                try:
                    plt.figure(figsize=(6, 4))
                    sns.histplot(df_sample[col].dropna(), kde=True, color='#8b5cf6')  # violet-500
                    plt.title(f"Distribution of {col}", pad=10)
                    plt.xlabel(col)
                    plt.ylabel("Frequency")
                    plt.tight_layout()
                    col_safe = col.lower().replace(' ', '_').replace('/', '_')
                    path = output_dir / f"dist_{col_safe}.png"
                    plt.savefig(path, facecolor='#0f172a', bbox_inches='tight')
                    plt.close()
                    charts.append(str(path.resolve()))
                except Exception as e:
                    logger.warning('Failed to generate histogram for %s: %s', col, e)

            # 3. Bar Charts for Categorical Columns (max 3, categories < 15)
            for col in categorical_cols[:3]:
                try:
                    counts = df_sample[col].dropna().value_counts().head(15)
                    if len(counts) > 1:
                        plt.figure(figsize=(6, 4))
                        sns.barplot(
                            x=counts.values, y=counts.index.astype(str),
                            palette="viridis", hue=counts.index.astype(str), legend=False
                        )
                        plt.title(f"Top Values in {col}", pad=10)
                        plt.xlabel("Count")
                        plt.ylabel(col)
                        plt.tight_layout()
                        col_safe = col.lower().replace(' ', '_').replace('/', '_')
                        path = output_dir / f"bar_{col_safe}.png"
                        plt.savefig(path, facecolor='#0f172a', bbox_inches='tight')
                        plt.close()
                        charts.append(str(path.resolve()))
                except Exception as e:
                    logger.warning('Failed to generate bar plot for %s: %s', col, e)

            # 4. Target vs Feature Plots (if target column found)
            target_col = None
            for f in findings:
                if f['type'] == 'target_column':
                    target_col = f['column']
                    break

            if target_col and target_col in df_sample.columns:
                features = [c for c in numeric_cols if c != target_col]
                if features:
                    # Pick the most-correlated feature (not just the first one)
                    feat = features[0]  # default fallback
                    corr_matrix = profile.get('correlations', {})
                    if target_col in corr_matrix:
                        target_corrs = corr_matrix[target_col]
                        sorted_feats = sorted(
                            [(f, abs(v)) for f, v in target_corrs.items() if f != target_col and f in features],
                            key=lambda x: x[1], reverse=True
                        )
                        if sorted_feats:
                            feat = sorted_feats[0][0]
                    try:
                        plt.figure(figsize=(6, 4))
                        if df_sample[target_col].nunique() <= 5:
                            sns.boxplot(data=df_sample, x=target_col, y=feat, palette="plasma")
                        else:
                            sns.scatterplot(data=df_sample, x=feat, y=target_col, color='#f59e0b')  # amber-500
                        plt.title(f"{feat} vs Target ({target_col})", pad=10)
                        plt.xlabel(target_col)
                        plt.ylabel(feat)
                        plt.tight_layout()
                        feat_safe = feat.lower().replace(' ', '_').replace('/', '_')
                        path = output_dir / f"target_vs_{feat_safe}.png"
                        plt.savefig(path, facecolor='#0f172a', bbox_inches='tight')
                        plt.close()
                        charts.append(str(path.resolve()))
                    except Exception as e:
                        logger.warning('Failed to generate target vs feature plot: %s', e)

            # 5. Time Series Plot if Datetime Column Detected
            date_col = None
            for col in df_sample.columns:
                if pd.api.types.is_datetime64_any_dtype(df_sample[col]):
                    date_col = col
                    break
            if not date_col:
                for f in findings:
                    if f['type'] == 'date_column' and f['column'] in df_sample.columns:
                        date_col = f['column']
                        break

            if date_col:
                try:
                    temp_dates = pd.to_datetime(df_sample[date_col], errors='coerce')
                    if temp_dates.notna().any():
                        y_col = None
                        if target_col and target_col != date_col and pd.api.types.is_numeric_dtype(df_sample[target_col]):
                            y_col = target_col
                        else:
                            features = [c for c in numeric_cols if c != date_col]
                            if features:
                                y_col = features[0]

                        if y_col:
                            plot_df = pd.DataFrame({
                                date_col: temp_dates,
                                y_col: df_sample[y_col]
                            }).dropna().sort_values(date_col)

                            if len(plot_df) > 5:
                                plt.figure(figsize=(8, 4))
                                plt.plot(plot_df[date_col], plot_df[y_col], color='#06b6d4', linewidth=2)  # teal-500
                                plt.title(f"{y_col} Over Time", pad=10)
                                plt.xlabel("Date")
                                plt.ylabel(y_col)
                                plt.xticks(rotation=45)
                                plt.tight_layout()
                                path = output_dir / "time_series.png"
                                plt.savefig(path, facecolor='#0f172a', bbox_inches='tight')
                                plt.close()
                                charts.append(str(path.resolve()))
                except Exception as e:
                    logger.warning('Failed to generate time series chart: %s', e)

            logger.info('Chart Engine complete: generated %d charts', len(charts))
        except Exception as e:
            logger.error('ChartEngine generation failed completely: %s', e, exc_info=True)
        finally:
            plt.close('all')  # Ensure no figure leaks on exceptions

        return charts
