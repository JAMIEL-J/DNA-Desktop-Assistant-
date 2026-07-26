# Data Analyst Module Modernization & Intelligence Upgrade Spec

**Date:** 2026-07-26  
**Status:** Approved  
**Target Module:** `skills/data_engine/` (`analyst.py`, `profiler.py`, `detector.py`, `chart_engine.py`, `report_builder.py`)

---

## 1. Overview & Objectives

The Data Analyst module in the DNA Assistant architecture requires a core modernization to elevate its performance from generic data profiling to enterprise-grade domain analytical reporting.

### Core Problems Solved
1. **Omission of Outlier Statistics in LLM Context**: `profiler.py` and `detector.py` computed statistical fences, but `analyst.py` omitted numeric stats and outlier metrics from the prompt sent to the LLM.
2. **Lack of Domain Classification & Semantic Mapping**: Datasets were processed using basic static fallbacks (top 3 categorical counts, raw histograms) without understanding column semantics or business domain context.
3. **Limited & Generic Chart Combinations**: Visualizations were capped at 3-4 basic single-variable charts instead of comprehensive multi-variable domain chart combinations.
4. **Disconnected Insights**: Visual charts lacked explicit analytical takeaways linking chart patterns to business insights.

---

## 2. Architecture & Subsystems

```
                     ┌────────────────────────┐
                     │   Uploaded CSV/Excel   │
                     └───────────┬────────────┘
                                 │
                     ┌───────────▼────────────┐
                     │     Data Profiler      │
                     │  (DuckDB + Outliers)   │
                     └───────────┬────────────┘
                                 │
                     ┌───────────▼────────────┐
                     │ Semantic Column        │
                     │ Resolver               │
                     └───────────┬────────────┘
                                 │
          ┌──────────────────────┴──────────────────────┐
          │                                             │
┌─────────▼──────────────┐                   ┌──────────▼─────────────┐
│    Domain Classifier   │                   │  Outlier Profiler      │
│  (Keywords + LLM Plan) │                   │  (IQR + Impact % Sum)  │
└─────────┬──────────────┘                   └──────────┬─────────────┘
          │                                             │
┌─────────▼──────────────┐                   ┌──────────▼─────────────┐
│  Domain Chart Planner  │                   │ Enriched Data Analyst  │
│  (6-10 DuckDB SQLs)    │                   │  (LLM Prompt + JSON)   │
└─────────┬──────────────┘                   └──────────┬─────────────┘
          │                                             │
          └──────────────────────┬──────────────────────┘
                                 │
                     ┌───────────▼────────────┐
                     │ Bento Report Builder   │
                     │ (Chart.js + Outliers)  │
                     └────────────────────────┘
```

---

## 3. Subsystem Specifications

### 3.1 Semantic Column Resolver (`skills/data_engine/semantic_resolver.py`)
Resolves raw/messy dataset column headers into standard semantic roles:
- `PRIMARY_METRIC`: Core numeric measure (`Sales`, `Revenue`, `Amount`, `Salary`, `Spend`, `Total_Cost`, `Balance`).
- `SECONDARY_METRIC`: Supporting numeric measure (`Profit`, `Discount`, `Quantity`, `Margin`, `Rating`).
- `PRIMARY_DIMENSION`: Key categorical grouping (`Category`, `Department`, `Region`, `Channel`, `Product_Line`).
- `SECONDARY_DIMENSION`: Secondary grouping (`Segment`, `Sub_Category`, `Job_Role`, `Customer_Type`, `Store`).
- `TEMPORAL_DIMENSION`: Time column (`Order_Date`, `Hire_Date`, `Timestamp`, `Year_Month`, `Created_At`).
- `ENTITY_ID`: High-cardinality identifier (`Order_ID`, `Customer_ID`, `Employee_ID`).

**Resolution Mechanism:**
1. Regex synonym lookup across 100+ common variations (e.g. `rev` -> `Revenue`, `dt_order` -> `Order_Date`).
2. Data type and cardinality analysis via DuckDB schema statistics.
3. Fallback LLM semantic classification for ambiguous custom headers.

---

### 3.2 Domain Classifier (`skills/data_engine/domain_classifier.py`)
Classifies the dataset into one of 5 primary business domains or a General fallback:
- **Sales / E-commerce**
- **HR / People**
- **Finance / Accounting**
- **Marketing / Campaigns**
- **Operations / Logistics**
- **General / Analytical**

**Classification Strategy:**
- Hybrid approach: Signature matching based on resolved column roles and domain vocabulary keywords.
- Lightweight LLM fallback when domain confidence score is < 0.4.

---

### 3.3 Outlier & Anomaly Engine (`profiler.py` & `detector.py`)
Extends numerical profiling to calculate comprehensive outlier metrics:
- **1.5x IQR & Z-Score Analysis**: Calculates lower/upper fences and outlier counts per numeric column.
- **Outlier Volume Impact %**: Computes total sum contribution of outlier rows (`SUM(Outliers) / SUM(Total)`).
- **Extreme Outliers List**: Extracts top 5 highest and lowest extreme values with row context.
- **Prompt Enrichment**: Injects detailed numerical profiles and outlier statistics into `analyst.py` prompt context.

---

### 3.4 Domain Chart Planner (`skills/data_engine/chart_planner.py`)
Generates an expanded suite of **6 to 10 multi-variable SQL aggregation queries** executed via DuckDB:

1. **Primary Volume & Revenue Driver** (Bar Chart): `SUM(Primary_Metric)` by `Primary_Dimension`
2. **Profitability & Efficiency Comparison** (Grouped / Dual-Axis Bar): `AVG(Secondary_Metric)` vs `SUM(Primary_Metric)` by `Primary_Dimension`
3. **Temporal Trend & Momentum** (Line Chart): `SUM(Primary_Metric)` over `Time`
4. **Sub-Segment Composition** (Stacked Bar / Donut Chart): Distribution of `Secondary_Dimension` within top `Primary_Dimensions`
5. **Outlier & Value Distribution Scatter** (Scatter Plot): `Primary_Metric` vs `Secondary_Metric` with highlighted fence thresholds
6. **Pareto Concentration (80/20 Rule)** (Cumulative Chart): Contribution of top categories to total metric sum
7. **Cross-Tabulation Matrix** (Heatmap): Density across `Primary_Dimension` x `Secondary_Dimension`
8. **Seasonality / Cyclical Pattern** (Bar Chart): Metric grouped by `Day_of_Week` or `Month`
9. **At-Risk / Low-Performing Cohorts** (Bar Chart): Bottom 10 categories sorted by lowest margin / performance
10. **Statistical Volatility & Spread** (Boxplot / Histogram): Distribution of primary metric values and outlier bounds

---

### 3.5 LLM Data Analyst (`skills/data_engine/analyst.py`)
Updates `ANALYST_RESPONSE_SCHEMA` to include:
- `outliers_and_anomalies`: Dedicated array for outlier findings with column name, severity, impact summary, and business recommendation.
- `chart_takeaways`: Key takeaway annotations linked directly to each generated domain chart.
- Enhanced prompt context containing explicit numerical statistics, outlier impact sums, and domain-specific terminology.

---

### 3.6 Bento Report Builder (`skills/data_engine/report_builder.py`)
- Renders responsive Chart.js visual widgets dynamically for all 6-10 domain chart combinations.
- Embeds a **Chart Insight Takeaway Banner** beneath every chart.
- Introduces an **Outliers & Extreme Volatility Highlights** card grid on the Insights and Overview tabs.
- Updates the Execution Audit Log to record Semantic Resolution, Domain Classification, Chart Aggregation SQLs, and Outlier Analysis.

---

## 4. Verification & Testing Criteria

1. **End-to-End Execution**: Run on `Superstore.csv` and verify all 6-10 charts render with paired chart takeaway banners.
2. **Outlier Verification**: Confirm outlier volume impact percentages (e.g. % of total revenue from top outlier orders) are accurate and visible in report insights.
3. **Domain Adaptation**: Test on Sales, HR, and Financial datasets to confirm dynamic adaptation of domain vocabulary and chart types.
4. **Schema Resilience**: Test with datasets containing non-standard column names (e.g., `amt`, `dept_code`, `emp_sal`) to confirm Semantic Column Resolver fallback.
