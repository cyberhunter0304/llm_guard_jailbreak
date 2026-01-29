"""
PII Detection Module
Thread-safe PII detection and anonymization
"""
import logging
import threading
import re
from typing import Tuple, List, Dict
from llm_guard.vault import Vault
from llm_guard.input_scanners import Anonymize
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
    def anonymize(text: str) -> Tuple[str, List[Dict]]:
        """Detect and anonymize PII - Creates isolated instance per call"""
        try:
            # Create NEW instance for this specific request
            vault, scanner = ThreadSafePIIDetector.create_detector()
            
            sanitized_text, _, risk_score = scanner.scan(text)

            entities = []
            tokens = re.findall(r'\[([A-Z_]+)_(\d+)\]', sanitized_text)
            
            for entity_type, entity_num in tokens:
                full_token = f"[{entity_type}_{entity_num}]"
                entities.append({
                    "type": entity_type,
                    "value": "REDACTED",
                    "token": full_token
                })

            if entities:
                logger.debug(f"PII detected: {len(entities)} entities found")
            
            return sanitized_text, entities
            
        except Exception as e:
            logger.error(f"PII Anonymization failed: {str(e)}")
            # Return original text if PII detection fails
            return text, []
