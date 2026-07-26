# skills/data_engine/semantic_resolver.py
import logging
import re
import pandas as pd
from typing import Dict, List, Any, Optional
from .llm_utils import call_llm_for_json

logger = logging.getLogger('dna.data_engine.semantic_resolver')

# Standard Semantic Roles
ROLE_PRIMARY_METRIC = "PRIMARY_METRIC"
ROLE_SECONDARY_METRIC = "SECONDARY_METRIC"
ROLE_PRIMARY_DIMENSION = "PRIMARY_DIMENSION"
ROLE_SECONDARY_DIMENSION = "SECONDARY_DIMENSION"
ROLE_TEMPORAL_DIMENSION = "TEMPORAL_DIMENSION"
ROLE_TARGET_LABEL = "TARGET_LABEL"
ROLE_ENTITY_ID = "ENTITY_ID"
ROLE_OTHER = "OTHER"

# Regex Synonym Patterns (100+ variations)
PATTERNS = {
    ROLE_TARGET_LABEL: [
        r'\bchurn(ed)?\b', r'\bstatus\b', r'\bdefault(ed)?\b', r'\bconvert(ed)?\b',
        r'\bfraud\b', r'\bsurvived\b', r'\battrition\b', r'\btarget\b', r'\blabel\b',
        r'\bclass\b', r'\bresponse\b', r'\brefunded\b', r'\bcancel(led)?\b', r'\blate\b'
    ],
    ROLE_ENTITY_ID: [
        r'.*_?id\b', r'\bid_.*', r'\bguid\b', r'\bkey\b', r'\bcode\b', r'\bnum\b',
        r'\border_num(ber)?\b', r'\bcust(omer)?_num(ber)?\b', r'\bemp(loyee)?_num(ber)?\b',
        r'.*zip.*', r'.*postal.*', r'.*pincode.*'
    ],

    ROLE_TEMPORAL_DIMENSION: [
        r'.*date.*', r'.*time.*', r'.*year.*', r'.*month.*', r'.*day.*', r'\bcreated_at\b',
        r'\bupdated_at\b', r'\btimestamp\b', r'\bperiod\b', r'\bquarter\b', r'\bhire_dt\b'
    ],
    ROLE_PRIMARY_METRIC: [
        r'\bsales?\b', r'\brevenue\b', r'\bamount\b', r'\bsalary\b', r'\bspend\b',
        r'\btotal_cost\b', r'\bbalance\b', r'\bval(ue)?\b', r'\bprice\b', r'\barr\b',
        r'\bmrr\b', r'\bincome\b', r'\bturnover\b', r'\bexpenditure\b', r'\bcharges?\b',
        r'\btotal_sales?\b', r'\bgrand_total\b', r'\bpaid\b', r'\bfee\b'
    ],
    ROLE_SECONDARY_METRIC: [
        r'\bprofit\b', r'\bdiscount\b', r'\bqty\b', r'\bquantity\b', r'\bmargin\b',
        r'\brating\b', r'\bscore\b', r'\bperformance\b', r'\btenure\b', r'\bdays?\b',
        r'\btax\b', r'\bfreight\b', r'\bshipping_cost\b', r'\bunit_price\b', r'\bunit_cost\b',
        r'\bage\b', r'\bexperience\b', r'\bsatisfaction\b', r'\btickets?\b'
    ],
    ROLE_PRIMARY_DIMENSION: [
        r'\bcategory\b', r'\bdept(artment)?\b', r'\bregion\b', r'\bchannel\b',
        r'\bproduct_line\b', r'\bcontract\b', r'\bstate\b', r'\bcountry\b', r'\bplan\b',
        r'\bsegment\b', r'\bmarket\b', r'\bdivision\b', r'\bstore\b', r'\bbranch\b'
    ],
    ROLE_SECONDARY_DIMENSION: [
        r'\bsub_?category\b', r'\bjob_?role\b', r'\bcust(omer)?_?type\b', r'\bpayment_?method\b',
        r'\bgender\b', r'\bsenior_?citizen\b', r'\bship_?mode\b', r'\bpriority\b',
        r'\bdevice\b', r'\bbrowser\b', r'\bos\b', r'\beducation\b', r'\bmarital_?status\b'
    ]
}


class SemanticColumnResolver:
    """Resolves raw dataset headers into canonical analytical roles."""

    def resolve(self, schema: List[Dict[str, Any]], sample_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        """Maps each column to a semantic role and identifies primary roles."""
        col_mappings = {}
        role_buckets: Dict[str, List[str]] = {
            ROLE_PRIMARY_METRIC: [],
            ROLE_SECONDARY_METRIC: [],
            ROLE_PRIMARY_DIMENSION: [],
            ROLE_SECONDARY_DIMENSION: [],
            ROLE_TEMPORAL_DIMENSION: [],
            ROLE_TARGET_LABEL: [],
            ROLE_ENTITY_ID: [],
            ROLE_OTHER: []
        }

        total_rows = sample_df.shape[0] if sample_df is not None else 1000

        for col in schema:
            name = col['name']
            name_clean = name.lower().strip().replace(' ', '_').replace('-', '_')
            col_type = str(col.get('type', '')).lower()
            uniques = col.get('uniques', 0)
            
            # Check high-cardinality ID
            if uniques > 0 and (uniques / total_rows) > 0.9 and uniques > 10:
                role = ROLE_ENTITY_ID
            else:
                role = self._match_regex_role(name_clean, col_type, uniques)

            col_mappings[name] = role
            role_buckets[role].append(name)

        # Fallback heuristic: If no primary metric or dimension assigned, infer by type
        if not role_buckets[ROLE_PRIMARY_METRIC]:
            for col in schema:
                c_name = col['name']
                if col_mappings[c_name] == ROLE_OTHER:
                    c_type = str(col.get('type', '')).lower()
                    if any(t in c_type for t in ['int', 'double', 'float', 'decimal', 'real', 'numeric']):
                        col_mappings[c_name] = ROLE_PRIMARY_METRIC
                        role_buckets[ROLE_PRIMARY_METRIC].append(c_name)
                        break

        if not role_buckets[ROLE_PRIMARY_DIMENSION]:
            for col in schema:
                c_name = col['name']
                if col_mappings[c_name] == ROLE_OTHER:
                    uniques = col.get('uniques', 0)
                    if 2 <= uniques <= 30:
                        col_mappings[c_name] = ROLE_PRIMARY_DIMENSION
                        role_buckets[ROLE_PRIMARY_DIMENSION].append(c_name)
                        break

        # Primary vs Secondary Assignments
        primary_metric = role_buckets[ROLE_PRIMARY_METRIC][0] if role_buckets[ROLE_PRIMARY_METRIC] else None
        secondary_metrics = role_buckets[ROLE_PRIMARY_METRIC][1:] + role_buckets[ROLE_SECONDARY_METRIC]
        
        primary_dimension = role_buckets[ROLE_PRIMARY_DIMENSION][0] if role_buckets[ROLE_PRIMARY_DIMENSION] else None
        secondary_dimensions = role_buckets[ROLE_PRIMARY_DIMENSION][1:] + role_buckets[ROLE_SECONDARY_DIMENSION]
        
        temporal_dimension = role_buckets[ROLE_TEMPORAL_DIMENSION][0] if role_buckets[ROLE_TEMPORAL_DIMENSION] else None
        target_label = role_buckets[ROLE_TARGET_LABEL][0] if role_buckets[ROLE_TARGET_LABEL] else None

        result = {
            'column_mappings': col_mappings,
            'primary_metric': primary_metric,
            'secondary_metrics': secondary_metrics,
            'primary_dimension': primary_dimension,
            'secondary_dimensions': secondary_dimensions,
            'temporal_dimension': temporal_dimension,
            'target_label': target_label,
            'entity_ids': role_buckets[ROLE_ENTITY_ID]
        }

        logger.info(
            'Semantic Resolution complete: Metric=%s, Dim=%s, Temporal=%s, Target=%s',
            primary_metric, primary_dimension, temporal_dimension, target_label
        )
        return result

    def _match_regex_role(self, name_clean: str, col_type: str, uniques: int) -> str:
        """Helper to match name against regex role patterns."""
        # 1. Target Label
        for pat in PATTERNS[ROLE_TARGET_LABEL]:
            if re.search(pat, name_clean):
                return ROLE_TARGET_LABEL

        # 2. Entity ID
        for pat in PATTERNS[ROLE_ENTITY_ID]:
            if re.search(pat, name_clean):
                return ROLE_ENTITY_ID

        # 3. Temporal
        is_num = any(t in col_type for t in ['int', 'double', 'float', 'decimal', 'real', 'numeric'])
        if not is_num or 'year' in name_clean or 'date' in name_clean:
            for pat in PATTERNS[ROLE_TEMPORAL_DIMENSION]:
                if re.search(pat, name_clean):
                    return ROLE_TEMPORAL_DIMENSION

        # 4. Primary Metric
        for pat in PATTERNS[ROLE_PRIMARY_METRIC]:
            if re.search(pat, name_clean) and is_num:
                return ROLE_PRIMARY_METRIC

        # 5. Secondary Metric
        for pat in PATTERNS[ROLE_SECONDARY_METRIC]:
            if re.search(pat, name_clean) and is_num:
                return ROLE_SECONDARY_METRIC

        # 6. Primary Dimension
        for pat in PATTERNS[ROLE_PRIMARY_DIMENSION]:
            if re.search(pat, name_clean):
                return ROLE_PRIMARY_DIMENSION

        # 7. Secondary Dimension (e.g. senior_citizen, gender, payment_method)
        for pat in PATTERNS[ROLE_SECONDARY_DIMENSION]:
            if re.search(pat, name_clean):
                return ROLE_SECONDARY_DIMENSION

        # Type fallback
        if is_num:
            if uniques <= 2:
                return ROLE_SECONDARY_DIMENSION
            return ROLE_PRIMARY_METRIC if uniques > 10 else ROLE_SECONDARY_METRIC
        elif 2 <= uniques <= 50:
            return ROLE_PRIMARY_DIMENSION

        return ROLE_OTHER
