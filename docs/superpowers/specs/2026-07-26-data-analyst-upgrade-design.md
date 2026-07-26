# Data Analyst Module Modernization & Intelligence Upgrade Spec

**Date:** 2026-07-26  
**Status:** Approved (Refined)  
**Target Module:** `skills/data_engine/` (`analyst.py`, `profiler.py`, `detector.py`, `chart_engine.py`, `report_builder.py`)

---

## 1. Overview & Objectives

The Data Analyst module in the DNA Assistant architecture requires a core modernization to elevate its performance from generic data profiling to enterprise-grade domain analytical reporting.

### Core Problems Solved
1. **Omission of Outlier Statistics in LLM Context**: `profiler.py` and `detector.py` computed statistical fences, but `analyst.py` omitted numeric stats and outlier metrics from the prompt sent to the LLM.
2. **Lack of Domain Classification & Semantic Mapping**: Datasets were processed using basic static fallbacks (top 3 categorical counts, raw histograms) without understanding column semantics or business domain context.
3. **Arbitrary Chart Caps & Low Complexity**: Visualizations were capped at fixed numbers instead of scaling dynamically based on dataset richness and column count.
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
│  (Dynamic Adaptive SQL)│                   │  (LLM Prompt + JSON)   │
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
- `TARGET_LABEL`: Binary or classification outcome (`Churn`, `Status`, `Default`, `Converted`, `Is_Fraud`).
- `ENTITY_ID`: High-cardinality identifier (`Order_ID`, `Customer_ID`, `Employee_ID`).

**Resolution Mechanism:**
1. Regex synonym lookup across 100+ common variations (e.g. `rev` -> `Revenue`, `dt_order` -> `Order_Date`, `retention_flag` -> `Churn`).
2. Data type and cardinality analysis via DuckDB schema statistics.
3. Fallback LLM semantic classification for ambiguous custom headers.

---

### 3.2 Domain Classifier & Specialized High-Accuracy Domain Rules (`skills/data_engine/domain_classifier.py`)
Classifies the dataset with deep focus on **Sales**, **Finance**, and **Churn**:

1. **Sales / E-Commerce Domain**:
   - Signature: `Sales`, `Revenue`, `Profit`, `Discount`, `Quantity`, `Category`, `Region`, `Customer`.
   - Key Analytical Targets: Total Volume, Profitability Margin, Price Elasticity, Discount Sensitivity, Regional Pareto.
2. **Finance / Accounting Domain**:
   - Signature: `Amount`, `Balance`, `Credit`, `Debit`, `Expense`, `Transaction`, `Risk`, `Account`, `Loss`.
   - Key Analytical Targets: Cash Flow Ratio, Debit vs Credit Balance, Transaction Value Skew, Account Volatility, High-Value Transaction Anomalies.
3. **Customer Churn / Retention Domain**:
   - Signature: `Churn`, `Status`, `Tenure`, `Contract`, `MonthlyCharges`, `TotalCharges`, `Subscription`, `Activity_Score`.
   - Key Analytical Targets: Baseline Churn Event Rate, Cohort Churn Rates, Tenure Risk Curve, Contract & Plan Sensitivity, High-Value Customer Churn Exposure.
4. **HR / People**: `Department`, `Salary`, `Tenure`, `Performance`, `Job_Role`.
5. **Marketing & Operations**: `Campaign`, `Clicks`, `Spend`, `Ship_Mode`, `Warehouse`.

---

### 3.3 Outlier & Anomaly Engine (`profiler.py` & `detector.py`)
Extends numerical profiling to calculate comprehensive outlier metrics:
- **1.5x IQR & Z-Score Analysis**: Calculates lower/upper fences and outlier counts per numeric column.
- **Outlier Volume Impact %**: Computes total sum contribution of outlier rows (`SUM(Outliers) / SUM(Total)`).
- **Extreme Outliers List**: Extracts top 5 highest and lowest extreme values with row context.
- **Prompt Enrichment**: Injects detailed numerical profiles and outlier statistics into `analyst.py` prompt context.

---

### 3.4 Dynamic Adaptive Chart Planner (`skills/data_engine/chart_planner.py`)
Generates a **dynamically scaled chart suite (uncapped)** based on dataset column count, categorical cardinality, and numerical richness:
- **Small Datasets (1–5 columns)**: 4–6 targeted core charts.
- **Medium Datasets (6–12 columns)**: 8–12 multi-variable combinations.
- **Large Datasets (13+ columns)**: 12–16+ comprehensive multi-dimensional charts.

#### Specialized Chart Combinations Matrix:
* **Sales Combinations**:
  - `SUM(Sales)` by `Category` (Bar)
  - `AVG(Profit_Margin)` vs `AVG(Discount)` by `Category` (Dual Axis / Grouped Bar)
  - `SUM(Sales)` & `SUM(Profit)` over Time (Monthly Trend)
  - Sub-Category Contribution to Revenue (Stacked Bar / Donut)
  - Price vs Quantity Scatter with Outlier Fences
  - Cumulative 80/20 Revenue Pareto Chart
  - Regional Profitability Heatmap
* **Finance Combinations**:
  - Transaction Amount Frequency Distribution (Histogram + KDE)
  - Cash Flow / Debit vs Credit Breakdown (Grouped Bar)
  - Transaction Value vs Risk Score Scatter Plot
  - Monthly Expense Category Breakdown
  - Top 1% Extreme Financial Transaction Outliers (Scatter / Boxplot)
  - Cumulative Loss Concentration by Account Group
* **Churn & Retention Combinations**:
  - Baseline Churn Rate by Contract Type (Bar)
  - Tenure vs Churn Rate Cohort Curve (Line / Step)
  - Monthly Recurring Revenue (MRR) at Risk by Churn Status (Stacked Bar)
  - Monthly Charges vs Total Charges Churn Scatter Plot
  - Churn Rate by Customer Segment & Payment Method (Heatmap)
  - Support Ticket Volume vs Churn Probability

---

### 3.5 LLM Data Analyst (`skills/data_engine/analyst.py`)
Updates `ANALYST_RESPONSE_SCHEMA` to include:
- `outliers_and_anomalies`: Dedicated array for outlier findings with column name, severity, impact summary, and business recommendation.
- `chart_takeaways`: Key takeaway annotations linked directly to each generated domain chart.
- Enhanced prompt context containing explicit numerical statistics, outlier impact sums, and domain-specific terminology for Sales, Finance, and Churn.

---

### 3.6 Bento Report Builder (`skills/data_engine/report_builder.py`)
- Renders responsive Chart.js visual widgets dynamically for all adaptive chart combinations.
- Embeds a **Chart Insight Takeaway Banner** beneath every chart.
- Introduces an **Outliers & Extreme Volatility Highlights** card grid on the Insights and Overview tabs.
- Updates the Execution Audit Log to record Semantic Resolution, Domain Classification, Chart Aggregation SQLs, and Outlier Analysis.

---

## 4. Verification & Testing Criteria

1. **Adaptive Chart Scaling**: Confirm small datasets generate 4–6 charts while complex datasets generate 12–16+ charts dynamically without artificial truncation.
2. **Priority Domain Accuracy**: Validate specialized metrics on Sales (`Superstore.csv`), Finance (`transactions.csv`), and Churn (`churn.csv`) datasets.
3. **Outlier Verification**: Confirm outlier volume impact percentages (e.g. % of total revenue from top outlier orders) are accurate and visible in report insights.
4. **Schema Resilience**: Test with datasets containing non-standard column names (e.g., `amt`, `dept_code`, `emp_sal`) to confirm Semantic Column Resolver fallback.
