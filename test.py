"""
===============================================================================
FILE: pii_detector.py (CUSTOMIZABLE PII DETECTION)
===============================================================================
PII Detection using LLM Guard with encryption integration
All PII detection configuration and customization happens here
"""

from typing import List, Dict, Tuple
from llm_guard.vault import Vault
from llm_guard.input_scanners import Anonymize
from llm_guard.input_scanners.anonymize_helpers import BERT_LARGE_NER_CONF
from backend.cipher_utils import text_encrypt, text_decrypt


class PIIDetector:
    """
    PII Detection and Encryption using LLM Guard
    
    This class handles:
    1. PII detection using llm-guard's Anonymize scanner
    2. Encryption of detected PII
    3. Decryption of responses
    """
    
    def __init__(
        self,
        preamble: str = "The following text contains encrypted sensitive information.",
        allowed_names: List[str] = None,
        hidden_names: List[str] = None,
        entity_types: List[str] = None,
        use_faker: bool = False,
        threshold: float = 0.0,
        language: str = "en"
    ):
        """
        Initialize PII Detector with LLM Guard
        
        Args:
            preamble: Text to insert before anonymized content
            allowed_names: Names that should NOT be redacted
            hidden_names: Names to always redact (transforms to [REDACTED_CUSTOM_1] format)
            entity_types: Specific PII types to detect (None = all types)
            use_faker: Replace entities with fake data instead of tokens
            threshold: Minimum confidence score for detection (0.0 to 1.0)
            language: Language code for detection (default: "en")
        """
        # Initialize the vault to store redacted data
        self.vault = Vault()
        
        # Configure the Anonymize scanner with LLM Guard
        self.scanner = Anonymize(
            vault=self.vault,
            preamble=preamble,
            allowed_names=allowed_names or [],
            hidden_names=hidden_names or [],
            entity_types=entity_types,  # None means detect all PII types
            use_faker=use_faker,
            recognizer_conf=BERT_LARGE_NER_CONF,  # Using BERT Large NER model
            threshold=threshold,
            language=language
        )
        
        self.preamble = preamble
        self.language = language
        
    def process(self, text: str) -> Tuple[str, List[Dict]]:
        """
        Detect PII and encrypt it
        
        Args:
            text: Original text with potential PII
            
        Returns:
            Tuple of (encrypted_text, list of detected PII entities)
        """
        # Step 1: Use LLM Guard to detect and anonymize PII
        sanitized_text, is_valid, risk_score = self.scanner.scan(text)
        
        # Step 2: Extract detected entities from the vault
        pii_entities = []
        
        # Get all items from the vault
        vault_items = self.vault.get()
        
        # Process each detected PII entity
        for entity_key, entity_value in vault_items.items():
            # Encrypt the original PII value
            encrypted_value = text_encrypt(entity_value)
            
            # Replace the anonymized token with encrypted value in the text
            sanitized_text = sanitized_text.replace(entity_key, encrypted_value)
            
            # Store entity information
            pii_entities.append({
                "type": self._get_entity_type(entity_key),
                "value": entity_value,
                "encrypted": encrypted_value,
                "token": entity_key
            })
        
        return sanitized_text, pii_entities
    
    def decrypt_text(self, encrypted_text: str, pii_entities: List[Dict]) -> str:
        """
        Decrypt PII in text using the entity mapping
        
        Args:
            encrypted_text: Text with encrypted PII
            pii_entities: List of PII entities with encryption mapping
            
        Returns:
            Decrypted text with original PII restored
        """
        decrypted_text = encrypted_text
        
        # Replace each encrypted value with its original value
        for entity in pii_entities:
            encrypted_value = entity["encrypted"]
            original_value = entity["value"]
            decrypted_text = decrypted_text.replace(encrypted_value, original_value)
        
        return decrypted_text
    
    def _get_entity_type(self, token: str) -> str:
        """
        Extract entity type from anonymization token
        
        Args:
            token: Anonymization token like [PERSON_1] or [EMAIL_ADDRESS_1]
            
        Returns:
            Entity type (e.g., "PERSON", "EMAIL_ADDRESS")
        """
        # Remove brackets and number suffix
        if token.startswith("[") and token.endswith("]"):
            token = token[1:-1]
            # Remove trailing number (e.g., _1, _2)
            parts = token.rsplit("_", 1)
            if len(parts) == 2 and parts[1].isdigit():
                return parts[0]
        return token
    
    def get_info(self) -> Dict:
        """
        Get information about the detector configuration
        
        Returns:
            Dictionary with detector settings
        """
        return {
            "engine": "llm-guard",
            "model": "BERT Large NER",
            "language": self.language,
            "preamble": self.preamble,
            "vault_size": len(self.vault.get())
        }
    
    def reset_vault(self):
        """
        Clear the vault (useful for testing or new sessions)
        """
        self.vault = Vault()
        self.scanner = Anonymize(
            vault=self.vault,
            preamble=self.preamble,
            recognizer_conf=BERT_LARGE_NER_CONF,
            language=self.language
        )


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == "__main__":
    # Example 1: Basic usage
    print("Example 1: Basic PII Detection")
    print("-" * 50)
    
    detector = PIIDetector()
    
    test_text = "My name is John Smith and my email is john.smith@email.com. Call me at 555-123-4567."
    
    encrypted_text, entities = detector.process(test_text)
    
    print(f"Original: {test_text}")
    print(f"Encrypted: {encrypted_text}")
    print(f"\nDetected {len(entities)} PII entities:")
    for entity in entities:
        print(f"  - {entity['type']}: {entity['value']} → {entity['encrypted']}")
    
    # Decrypt back
    decrypted = detector.decrypt_text(encrypted_text, entities)
    print(f"\nDecrypted: {decrypted}")
    
    print("\n" + "="*50)
    
    # Example 2: With allowed names
    print("\nExample 2: With Allowed Names")
    print("-" * 50)
    
    detector2 = PIIDetector(allowed_names=["John Doe"])
    
    test_text2 = "John Doe and Jane Smith work together. Contact Jane at jane@company.com"
    
    encrypted_text2, entities2 = detector2.process(test_text2)
    
    print(f"Original: {test_text2}")
    print(f"Encrypted: {encrypted_text2}")
    print(f"\nNote: 'John Doe' was not redacted (allowed name)")
    print(f"Detected {len(entities2)} PII entities:")
    for entity in entities2:
        print(f"  - {entity['type']}: {entity['value']} → {entity['encrypted']}")