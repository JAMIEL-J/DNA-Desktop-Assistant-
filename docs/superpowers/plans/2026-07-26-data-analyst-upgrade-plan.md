# Data Analyst Module Modernization & Intelligence Upgrade Implementation Plan

**Spec File:** `docs/superpowers/specs/2026-07-26-data-analyst-upgrade-design.md`  
**Date:** 2026-07-26  
**Status:** Ready for Execution  

---

## Task Breakdown & Implementation Steps

### Task 1: Create Semantic Column Resolver (`skills/data_engine/semantic_resolver.py`)
- [ ] Create `SemanticColumnResolver` class.
- [ ] Implement regex synonym mapping dictionary matching 100+ column variations:
  - `PRIMARY_METRIC`: `sales`, `revenue`, `amount`, `salary`, `spend`, `total_cost`, `balance`, `val`.
  - `SECONDARY_METRIC`: `profit`, `discount`, `quantity`, `margin`, `rating`, `performance_score`, `charges`.
  - `PRIMARY_DIMENSION`: `category`, `department`, `region`, `channel`, `product_line`, `contract`.
  - `SECONDARY_DIMENSION`: `segment`, `sub_category`, `job_role`, `customer_type`, `store`, `payment_method`.
  - `TEMPORAL_DIMENSION`: `date`, `order_date`, `hire_date`, `timestamp`, `year_month`, `created_at`.
  - `TARGET_LABEL`: `churn`, `status`, `default`, `converted`, `is_fraud`, `survived`.
  - `ENTITY_ID`: `id`, `order_id`, `customer_id`, `employee_id`.
- [ ] Implement statistical validation using DuckDB schema & unique counts.
- [ ] Add LLM fallback function `_llm_resolve_semantics()` for obscure column headers.

### Task 2: Create Domain Classifier (`skills/data_engine/domain_classifier.py`)
- [ ] Create `DomainClassifier` class.
- [ ] Implement signature matching for:
  - **Sales / E-Commerce**
  - **Finance / Accounting**
  - **Customer Churn / Retention**
  - **HR / People**
  - **Marketing / Campaigns**
  - **Operations / Logistics**
- [ ] Add domain confidence scoring (if confidence < 0.4, trigger LLM domain classification fallback).

### Task 3: Upgrade Outlier & Statistical Engine (`skills/data_engine/profiler.py` & `detector.py`)
- [ ] Extend `DataProfiler._numeric_stats()` in `profiler.py` to calculate IQR fences (`Q1 - 1.5*IQR`, `Q3 + 1.5*IQR`), Z-scores, and top 5 extreme values.
- [ ] Add **Outlier Volume Impact %**: `SUM(outlier_rows) / SUM(total_metric)` via DuckDB SQL query.
- [ ] Update `PatternDetector._detect_outliers()` in `detector.py` to produce structured outlier findings with volume impact percentages.

### Task 4: Create Dynamic Adaptive Chart Planner (`skills/data_engine/chart_planner.py`)
- [ ] Create `DomainChartPlanner` class.
- [ ] Implement adaptive scaling logic:
  - Small Datasets (1-5 cols): 4-6 targeted charts.
  - Medium Datasets (6-12 cols): 8-12 charts.
  - Large Datasets (13+ cols): 12-16+ domain combinations.
- [ ] Write SQL aggregation generators for Sales, Finance, Churn, HR, and General domains:
  - Sales: Revenue by Category, Margin vs Discount, Time Trends, Sub-category stacked, Price vs Qty scatter, 80/20 Pareto.
  - Finance: Transaction distribution, Cash flow debit/credit ratio, Risk vs Value scatter, Extreme outlier scatter.
  - Churn: Churn rate by contract, Tenure vs Churn risk curve, MRR at risk, Charges scatter plot, Segment heatmap.
- [ ] Execute aggregation queries via DuckDB and output structured JSON payloads.

### Task 5: Upgrade LLM Data Analyst Prompt & Response Schema (`skills/data_engine/analyst.py`)
- [ ] Update `ANALYST_RESPONSE_SCHEMA` to add `outliers_and_anomalies` array and `chart_takeaways` dictionary.
- [ ] Update `_build_analyst_prompt()` to format explicit `Numeric Statistics & Outliers Context` block.
- [ ] Inject domain-specific vocabulary guidelines based on the detected domain.

### Task 6: Upgrade Bento Dashboard Report Builder (`skills/data_engine/report_builder.py`)
- [ ] Update HTML/JS dashboard template to render responsive Chart.js visual cards dynamically for all adaptive chart payloads.
- [ ] Add **Chart Takeaway Banner** beneath each chart canvas.
- [ ] Add **Outliers & Extreme Volatility Highlights** card grid on Overview and Insights tabs.
- [ ] Update Execution Audit Log to trace Semantic Resolution, Domain Classification, SQL Chart Planning, and Outlier Analysis.

### Task 7: End-to-End Verification & Testing
- [ ] Create `scratch/test_data_analyst_upgrade.py`.
- [ ] Test execution on `Sample - Superstore.csv` (Sales domain).
- [ ] Test execution on `data/churn.csv` (Churn domain).
- [ ] Validate chart rendering, outlier impact percentages, and audit log traces.

---

## File Edits & Creation Summary
- `skills/data_engine/semantic_resolver.py` (New)
- `skills/data_engine/domain_classifier.py` (New)
- `skills/data_engine/chart_planner.py` (New)
- `skills/data_engine/profiler.py` (Modify)
- `skills/data_engine/detector.py` (Modify)
- `skills/data_engine/analyst.py` (Modify)
- `skills/data_engine/report_builder.py` (Modify)
- `skills/data_engine/__init__.py` (Modify)
