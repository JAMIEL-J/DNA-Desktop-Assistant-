# skills/data_engine/output_router.py
from enum import Enum
import logging

logger = logging.getLogger('dna.data_engine.output_router')


class OutputMode(Enum):
    VOICE_ONLY = "voice"
    DEEP_REPORT = "report"
    EXPORT = "export"


class OutputRouter:
    """Classifies user intent into voice, deep report, or export modes."""

    DEEP_KEYWORDS = [
        'analyze', 'analysis', 'profile', 'investigate', 'why', 'patterns',
        'report', 'dashboard', 'deep dive', 'explore', 'summarize', 'overview',
        'what is happening', 'find out', 'breakdown'
    ]
    EXPORT_KEYWORDS = [
        'export', 'save', 'download', 'to csv', 'to excel'
    ]

    def classify(self, question: str) -> OutputMode:
        """Classify a question to determine output mode."""
        try:
            q = question.lower().strip()
            if any(kw in q for kw in self.EXPORT_KEYWORDS):
                logger.info('Classified query "%s" as EXPORT', question)
                return OutputMode.EXPORT
            if any(kw in q for kw in self.DEEP_KEYWORDS):
                logger.info('Classified query "%s" as DEEP_REPORT', question)
                return OutputMode.DEEP_REPORT
            logger.info('Classified query "%s" as VOICE_ONLY', question)
            return OutputMode.VOICE_ONLY
        except Exception as e:
            logger.error('OutputRouter classification failed: %s', e, exc_info=True)
            return OutputMode.VOICE_ONLY
