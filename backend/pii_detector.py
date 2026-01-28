"""
===============================================================================
FILE: pii_detector.py (DETECTION ONLY)
===============================================================================
PII Detection using LLM Guard (NO encryption / decryption)
All PII detection configuration and customization happens here
"""

from typing import List, Dict, Tuple
import logging
from llm_guard.vault import Vault
from llm_guard.input_scanners import Anonymize
from llm_guard.input_scanners.anonymize_helpers import BERT_LARGE_NER_CONF

logger = logging.getLogger(__name__)


class PIIDetector:
    """
    PII Detection using LLM Guard (Detection + Anonymization only)

    This class handles:
    1. PII detection
    2. Token-based anonymization
    3. Structured extraction of detected entities
    """

    def __init__(
        self,
        preamble: str = "The following text contains sensitive information.",
        allowed_names: List[str] = None,
        hidden_names: List[str] = None,
        entity_types: List[str] = None,
        use_faker: bool = False,
        threshold: float = 0.0,
        language: str = "en"
    ):
        self.vault = Vault()

        self.scanner = Anonymize(
            vault=self.vault,
            preamble=preamble,
            allowed_names=allowed_names or [],
            hidden_names=hidden_names or [],
            entity_types=entity_types,
            use_faker=use_faker,
            recognizer_conf=BERT_LARGE_NER_CONF,
            threshold=threshold,
            language=language
        )

        self.preamble = preamble
        self.language = language
        self.threshold = threshold

    def detect_pii(self, text: str) -> Tuple[List[Dict], float]:
        """
        Detect PII without modifying the input text.

        Returns:
            (pii_entities, risk_score)
        """
        try:
            self.reset_vault()

            _, _, risk_score = self.scanner.scan(text)

            pii_entities = []
            for token, value in self.vault.get().items():
                start = text.find(value)
                context = (
                    text[max(0, start - 50): start + len(value) + 50]
                    if start != -1 else value
                )

                pii_entities.append({
                    "type": self._get_entity_type(token),
                    "value": value,
                    "context": context,
                    "token": token
                })

            risk_value = float(risk_score) if risk_score is not None else 0.0
            return pii_entities, risk_value

        except Exception as e:
            logger.error(f"PII detection failed: {str(e)}")
            return [], 0.0

    def anonymize(self, text: str) -> Tuple[str, List[Dict]]:
        """
        Detect and anonymize PII using tokens like [EMAIL_ADDRESS_1].

        Returns:
            (sanitized_text, detected_entities)
        """
        sanitized_text, _, _ = self.scanner.scan(text)

        entities = []
        for token, value in self.vault.get().items():
            entities.append({
                "type": self._get_entity_type(token),
                "value": value,
                "token": token
            })

        return sanitized_text, entities

    def _get_entity_type(self, token: str) -> str:
        """
        Extract entity type from anonymization token.
        """
        if token.startswith("[") and token.endswith("]"):
            token = token[1:-1]
            parts = token.rsplit("_", 1)
            if len(parts) == 2 and parts[1].isdigit():
                return parts[0]
        return token

    def get_info(self) -> Dict:
        return {
            "engine": "llm-guard",
            "model": "BERT Large NER",
            "language": self.language,
            "preamble": self.preamble,
            "vault_size": len(self.vault.get())
        }

    def reset_vault(self):
        """
        Clears vault and reinitializes scanner (important per-request).
        """
        self.vault = Vault()
        self.scanner = Anonymize(
            vault=self.vault,
            preamble=self.preamble,
            recognizer_conf=BERT_LARGE_NER_CONF,
            threshold=self.threshold,
            language=self.language
        )
