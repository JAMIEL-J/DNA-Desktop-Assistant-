# Implementation Plan: SQL-First Senior-Level Active Analyst

We will implement the SQL-First Senior-Level Active Analyst in five main steps, ensuring code output transparency, spoken voice updates, and deep target-aware profiling.

---

## Step 1: Implement TTS Text Cleaning (`pipeline/tts.py`)
Ensure that the text-to-speech engine only reads natural English sentences, stripping out markdown formatting, headers, emojis, and especially raw SQL/Python code blocks.

*   **Changes in `pipeline/tts.py`**:
    *   Add helper function `clean_text_for_tts(text: str) -> str` using regular expressions.
    *   In `speak(text)` and `speak_async(text)`:
        *   Clean the text input using `clean_text_for_tts(text)` before passing it to the Piper synthesizer.

---

## Step 2: Target Column and Positive Class Identification
Add logic to dynamically identify the "positive" value (e.g. `'Yes'`, `1`, `True`) for binary target columns.

*   **Changes in `skills/data_engine/profiler.py`**:
    *   Add a method `_determine_positive_class(self, con, table_ref, target_col: str) -> str`:
        *   Query unique values from the target column: `SELECT DISTINCT "{target_col}" FROM {table_ref} LIMIT 10`.
        *   Identify which value represents the positive outcome (e.g., casing-insensitive check for `'yes'`, `'true'`, `'1'`, `'default'`, `'churned'`, `'attrition'`).
        *   Fallback to the first non-null/non-false value.

---

## Step 3: Implement SQL-First Target Breakdowns (`skills/data_engine/profiler.py`)
Run advanced DuckDB grouping queries to calculate volume-based cross-tabulations.

*   **Changes in `skills/data_engine/profiler.py`**:
    *   Add a method `_run_target_breakdowns(self, con, table_ref, target_col: str, schema: list, row_count: int) -> dict`:
        *   Find the positive class value.
        *   Get the total count of positive events ($N_{target}$) in the dataset.
        *   For each categorical column with low cardinality (unique count between 2 and 12):
            *   Run the grouping SQL query:
                ```sql
                SELECT 
                    "{column}" AS category,
                    COUNT(*) AS total_count,
                    SUM(CASE WHEN "{target_col}" = '{positive_val}' THEN 1 ELSE 0 END) AS event_count,
                    (AVG(CASE WHEN "{target_col}" = '{positive_val}' THEN 1.0 ELSE 0.0 END) * 100) AS event_pct
                FROM {table_ref}
                GROUP BY "{column}"
                ORDER BY total_count DESC;
                ```
            *   Add calculated proportions: `% of dataset` and `% of total events` (share of the problem).
        *   For numeric columns, group by target and calculate the averages:
            ```sql
            SELECT 
                "{target_col}" AS target_status,
                AVG("{num_col}") AS mean_val
            FROM {table_ref}
            GROUP BY "{target_col}";
            ```
        *   Store everything in a structured dictionary.
    *   In `profile(self, path)`:
        *   After schema detection and strategey setup, check if a target column has been detected (we can look at findings or do a simple check on names).
        *   Run `_run_target_breakdowns` and store it in `profile_data['target_breakdowns']`.

---

## Step 4: Upgrading prompt in `skills/data_engine/analyst.py`
Incorporate the dynamic target breakdowns into the prompt and instruct the LLM to output volume-aware, senior-level findings.

*   **Changes in `skills/data_engine/analyst.py`**:
    *   In `_build_analyst_prompt(self, profile, findings, question)`:
        *   If `profile.get('target_breakdowns')` exists, format it into a readable text-list (e.g. showing category totals, rate %, and event contribution %).
        *   Add strict instructions to the prompt:
            *   Write in the persona of a Senior Director of Business Intelligence.
            *   Use numbers heavily, focusing on the highest volume drivers of the target event.
            *   Compare rates alongside absolute totals to provide business scale.

---

## Step 5: Integrating Spoken Cues and Query Logs (`skills/data_engine/__init__.py`)
Update the main analysis workflow to immediately speak progress and output formatted query logs.

*   **Changes in `skills/data_engine/__init__.py`**:
    *   Define a list of queries/files that the engine ran during profiling, and format them under a `**📊 Database Queries Run:**` markdown header.
    *   In `run_analysis`:
        *   If `mode == OutputMode.VOICE_ONLY` and the question is a general overview/summary request (e.g., matching `"summary"`, `"analyze"`, `"overview"`):
            *   Speak progress immediately: `speak_async("Running the SQL code for the dataset, sir. Analyzing the KPIs and checking for key correlations...")`.
            *   Run `DataAnalyst` in the background to generate the senior-level `executive_summary`.
            *   Construct a returned string containing:
                1. The `**📊 Database Queries Run:**` section showing the profiling SQL queries run behind the scenes.
                2. The `**💡 Business Analysis:**` section containing the LLM-generated executive summary.
            *   This return value is printed in the UI, and the TTS engine will automatically clean it and speak only the natural insights.
