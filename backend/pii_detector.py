"""
PII Detection Module
Thread-safe PII detection and anonymization with Secrets detection
"""
import logging
import threading
import re
from typing import Tuple, List, Dict
from llm_guard.vault import Vault
from llm_guard.input_scanners import Anonymize, Secrets
from llm_guard.input_scanners.anonymize_helpers import BERT_LARGE_NER_CONF
from config import SCANNER_CONFIG

logger = logging.getLogger(__name__)


class ThreadSafePIIDetector:
    """
    Thread-Safe PII Detector with proper model initialization
    """
    
    # Class-level model cache to avoid re-downloading
    _model_cache = {}
    _cache_lock = threading.Lock()
    
    @staticmethod
    def _ensure_model_loaded():
        """Ensure BERT model is properly loaded (once per process)"""
        with ThreadSafePIIDetector._cache_lock:
            if 'bert_loaded' not in ThreadSafePIIDetector._model_cache:
                try:
                    import torch
                    from transformers import AutoTokenizer, AutoModelForTokenClassification
                    
                    model_name = BERT_LARGE_NER_CONF.get('DEFAULT_MODEL_NAME', 'dslim/bert-base-NER')
                    
                    # Force download and load with actual weights
                    logger.info(f"Loading BERT model: {model_name}")
                    tokenizer = AutoTokenizer.from_pretrained(model_name)
                    model = AutoModelForTokenClassification.from_pretrained(
                        model_name,
                        torch_dtype=torch.float32,  # Use float32 instead of meta
                        low_cpu_mem_usage=False      # Disable lazy loading
                    )
                    
                    # Move to CPU and ensure weights are loaded
                    model = model.to('cpu')
                    model.eval()
                    
                    ThreadSafePIIDetector._model_cache['bert_loaded'] = True
                    ThreadSafePIIDetector._model_cache['model'] = model
                    ThreadSafePIIDetector._model_cache['tokenizer'] = tokenizer
                    
                    logger.info("✓ BERT model loaded successfully")
                    
                except Exception as e:
                    logger.error(f"Failed to load BERT model: {str(e)}")
                    ThreadSafePIIDetector._model_cache['bert_loaded'] = False
                    raise
    
    @staticmethod
    def create_detector(
        preamble: str = "The following text contains sensitive information.",
        threshold: float = None,
        language: str = "en"
    ):
        """Create a fresh PII detector instance with shared model"""
        if threshold is None:
            threshold = SCANNER_CONFIG["pii_threshold"]
            
        # Ensure model is loaded first
        ThreadSafePIIDetector._ensure_model_loaded()
        
        vault = Vault()
        scanner = Anonymize(
            vault=vault,
            preamble=preamble,
            allowed_names=[],
            hidden_names=[],
            entity_types=None,
            use_faker=False,
            recognizer_conf=BERT_LARGE_NER_CONF,
            threshold=threshold,
            language=language
        )
        return vault, scanner
    
    @staticmethod
    def anonymize(text: str) -> Tuple[str, List[Dict], Dict[str, any]]:
        """
        Detect and anonymize PII using multiple scanners
        Returns: (anonymized_text, entities_list, scanner_results)
        
        Runs two scanners in sequence:
        1. PII/Anonymize - Detects and anonymizes names, emails, SSN, etc.
        2. Secrets - Detects API keys, passwords, tokens
        """
        entities = []
        scanner_results = {
            "secrets": {"detected": False, "is_valid": True, "risk_score": 0.0}
        }
        
        try:
            # ================================================================
            # SCANNER 1: PII/Anonymize Scanner
            # ================================================================
            try:
                vault, pii_scanner = ThreadSafePIIDetector.create_detector()
                sanitized_text, is_valid_pii, risk_score_pii = pii_scanner.scan(text)

                # Extract entities from anonymized text
                tokens = re.findall(r'\[([A-Z_]+)_(\d+)\]', sanitized_text)
                
                # Use a set to track unique tokens to avoid duplicates
                seen_tokens = set()
                for entity_type, entity_num in tokens:
                    full_token = f"[{entity_type}_{entity_num}]"
                    # Only add if we haven't seen this token before
                    if full_token not in seen_tokens:
                        seen_tokens.add(full_token)
                        entities.append({
                            "type": entity_type,
                            "value": "REDACTED",
                            "token": full_token,
                            "source": "pii"
                        })
                
                if entities:
                    logger.info(f"PII Scanner: Found {len(entities)} unique entities")
                    
            except Exception as e:
                logger.error(f"PII Scanner failed: {str(e)}")
                sanitized_text = text
            
            # ================================================================
            # SCANNER 2: Secrets Scanner
            # ================================================================
            try:
                secrets_scanner = Secrets(redact_mode="all")
                _, is_valid_secrets, risk_score_secrets = secrets_scanner.scan(text)
                secrets_detected = not is_valid_secrets
                
                scanner_results["secrets"] = {
                    "detected": secrets_detected,
                    "is_valid": is_valid_secrets,
                    "risk_score": float(risk_score_secrets)
                }
                
                if secrets_detected:
                    logger.info(f"Secrets Scanner: Detected secrets (risk: {risk_score_secrets})")
                    
            except Exception as e:
                logger.error(f"Secrets Scanner failed: {str(e)}")
            
            # ================================================================
            # Deduplicate entities from all scanners
            # ================================================================
            entities = ThreadSafePIIDetector.deduplicate_entities(entities)
            
            if entities:
                logger.info(f"Total unique PII entities detected: {len(entities)}")
            
            return sanitized_text, entities, scanner_results
            
        except Exception as e:
            logger.error(f"PII/Secrets detection failed: {str(e)}")
            # Return original text if detection fails
            return text, [], scanner_results
    
    @staticmethod
    def deduplicate_entities(entities: List[Dict]) -> List[Dict]:
        """
        Deduplicate PII entities based on token
        Used when multiple scanners detect the same entities
        
        Args:
            entities: List of entity dictionaries with 'token' field
            
        Returns:
            Deduplicated list of entities
        """
        if not entities:
            return []
        
        seen_tokens = set()
        deduplicated = []
        
        for entity in entities:
            entity_token = entity.get("token", "")
            # Only add if we haven't seen this token before
            if entity_token and entity_token not in seen_tokens:
                seen_tokens.add(entity_token)
                deduplicated.append(entity)
        
        if len(entities) != len(deduplicated):
            logger.debug(f"Deduplicated PII entities: {len(entities)} -> {len(deduplicated)}")
        
        return deduplicated