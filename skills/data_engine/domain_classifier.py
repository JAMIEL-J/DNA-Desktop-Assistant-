# skills/data_engine/domain_classifier.py
import logging
from typing import Dict, Any, List
from .llm_utils import call_llm_for_json

logger = logging.getLogger('dna.data_engine.domain_classifier')

DOMAIN_SALES = "sales"
DOMAIN_FINANCE = "finance"
DOMAIN_CHURN = "churn"
DOMAIN_HR = "hr"
DOMAIN_MARKETING = "marketing"
DOMAIN_OPERATIONS = "operations"
DOMAIN_GENERAL = "general"

DOMAIN_NAMES = {
    DOMAIN_SALES: "Sales & E-Commerce",
    DOMAIN_FINANCE: "Finance & Accounting",
    DOMAIN_CHURN: "Customer Churn & Retention",
    DOMAIN_HR: "HR & People Analytics",
    DOMAIN_MARKETING: "Marketing & Campaigns",
    DOMAIN_OPERATIONS: "Operations & Logistics",
    DOMAIN_GENERAL: "General Business Analytics"
}

KEYWORDS = {
    DOMAIN_CHURN: {'churn', 'tenure', 'contract', 'monthlycharges', 'totalcharges', 'paperlessbilling', 'paymentmethod', 'seniorcitizen', 'techsupport', 'streamingtv'},
    DOMAIN_SALES: {'sales', 'revenue', 'order', 'orders', 'profit', 'discount', 'quantity', 'category', 'sub_category', 'product', 'region', 'segment', 'customer'},
    DOMAIN_FINANCE: {'amount', 'balance', 'credit', 'debit', 'transaction', 'account', 'risk', 'loss', 'expense', 'tax', 'fee', 'loan', 'principal', 'interest'},
    DOMAIN_HR: {'employee', 'emp', 'salary', 'department', 'dept', 'job_role', 'role', 'performance', 'satisfaction', 'hire_date', 'rating', 'work_life'},
    DOMAIN_MARKETING: {'campaign', 'clicks', 'impressions', 'conversions', 'spend', 'lead', 'ctr', 'cpc', 'cpa', 'channel', 'ad_group'},
    DOMAIN_OPERATIONS: {'ship_mode', 'carrier', 'warehouse', 'inventory', 'stock', 'delivery', 'lead_time', 'supplier', 'weight', 'shipping'}
}


class DomainClassifier:
    """Classifies dataset into business domain based on column signatures & semantics."""

    def classify(self, schema: List[Dict[str, Any]], semantics: Dict[str, Any]) -> Dict[str, Any]:
        """Classify domain with signature scoring and optional LLM fallback."""
        col_names = [col['name'].lower().replace(' ', '_').replace('-', '_') for col in schema]
        all_text = " ".join(col_names)

        scores = {d: 0.0 for d in KEYWORDS}

        # 1. Signature Keyword Match
        for domain, kw_set in KEYWORDS.items():
            for kw in kw_set:
                if kw in all_text:
                    scores[domain] += 1.0

        # Boost target label if detected
        target = semantics.get('target_label')
        if target:
            t_lower = target.lower()
            if 'churn' in t_lower or 'status' in t_lower or 'attrition' in t_lower:
                scores[DOMAIN_CHURN] += 3.0
            elif 'default' in t_lower or 'fraud' in t_lower:
                scores[DOMAIN_FINANCE] += 3.0

        best_domain = max(scores, key=lambda k: scores[k])
        max_score = scores[best_domain]

        # Calculate confidence
        total_score = sum(scores.values())
        confidence = (max_score / total_score) if total_score > 0 else 0.0

        # Check if fallback to General or LLM is needed
        if max_score < 2.0 or confidence < 0.35:
            logger.info('Low confidence (%.2f) domain match. Falling back to General / LLM classifier.', confidence)
            llm_domain = self._llm_classify_domain(schema)
            if llm_domain in DOMAIN_NAMES:
                best_domain = llm_domain
                confidence = 0.85
            else:
                best_domain = DOMAIN_GENERAL
                confidence = 0.50

        domain_name = DOMAIN_NAMES.get(best_domain, DOMAIN_NAMES[DOMAIN_GENERAL])

        logger.info('Domain Classified: %s (%s) with confidence %.2f', best_domain, domain_name, confidence)

        return {
            'domain': best_domain,
            'domain_name': domain_name,
            'confidence': float(confidence),
            'scores': scores
        }

    def _llm_classify_domain(self, schema: List[Dict[str, Any]]) -> str:
        """Lightweight LLM fallback for ambiguous schemas."""
        schema_summary = ", ".join([f"{col['name']} ({col.get('type', '')})" for col in schema[:15]])
        prompt = (
            f"Classify the following dataset schema into exactly one of these domains: "
            f"['sales', 'finance', 'churn', 'hr', 'marketing', 'operations', 'general'].\n\n"
            f"Schema: {schema_summary}\n\n"
            f"Return JSON format: {{\"domain\": \"<chosen_domain>\"}}"
        )
        try:
            res = call_llm_for_json(prompt, schema={"type": "OBJECT", "properties": {"domain": {"type": "STRING"}}})
            if res and res.get('domain'):
                return res['domain'].lower().strip()
        except Exception as e:
            logger.warning('LLM domain classification failed: %s', e)
        return DOMAIN_GENERAL
