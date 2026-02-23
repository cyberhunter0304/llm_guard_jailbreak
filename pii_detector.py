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
    def _extract_pii_patterns(text: str) -> Dict[str, List[str]]:
        """
        Extract ACTUAL PII values from original text using multiple strategies.
        This happens BEFORE anonymization destroys the values!
        
        Returns: {"ENTITY_TYPE": ["actual_value1", "actual_value2"]}
        """
        pii_values = {}
        
        logger.info(f"Starting PII extraction from: '{text}'")
        
        # Strategy 1: Use presidio analyzer if available (most accurate)
        try:
            from presidio_analyzer import AnalyzerEngine
            
            analyzer = AnalyzerEngine()
            results = analyzer.analyze(text=text, language="en")
            
            logger.info(f"Presidio found {len(results)} PII entities")
            
            for result in results:
                entity_type = result.entity_type
                start = result.start
                end = result.end
                entity_value = text[start:end]
                
                if entity_type not in pii_values:
                    pii_values[entity_type] = []
                
                pii_values[entity_type].append(entity_value)
                logger.info(f"Presidio found {entity_type}: '{entity_value}' at [{start}:{end}]")
            
            if pii_values:
                logger.info(f"✓ Successfully extracted with Presidio: {pii_values}")
                return pii_values
                
        except ImportError:
            logger.debug("Presidio not available, using fallback extraction")
        except Exception as e:
            logger.debug(f"Presidio extraction failed: {str(e)}, trying fallback")
        
        # Strategy 2: Regex and pattern-based extraction
        logger.info("Using regex pattern extraction")
        
        patterns = {
            'EMAIL_ADDRESS': (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', 'email'),
            'US_SSN_RE': (r'\b\d{3}-\d{2}-\d{4}\b', 'SSN'),
            'US_PHONE_RE': (r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b', 'phone'),
            'US_ZIPCODE': (r'\b\d{5}(?:-\d{4})?\b', 'zipcode'),
            'CREDIT_CARD': (r'\b(?:\d{4}[-\s]?){3}\d{4}\b', 'credit card'),
        }
        
        for entity_type, (pattern, desc) in patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                pii_values[entity_type] = matches
                logger.info(f"Found {len(matches)} {desc} ({entity_type}): {matches}")
        
        # Strategy 3: Extract person names (most important for "I am Jonathan" case)
        logger.info("Extracting person names...")
        names = []
        
        # Pattern: "name is [Name]" or "I am [Name]" etc.
        name_context_patterns = [
            r"(?:name\s+is|called|I\s+am|he\s+is|she\s+is|they\s+are)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
            r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)(?:\s|,|!|\.|$)",  # Start of text
        ]
        
        for pattern in name_context_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                name = match.strip()
                if len(name) > 2 and name not in names:
                    names.append(name)
                    logger.info(f"Extracted name from context: '{name}'")
        
        # Fallback: Any capitalized word > 2 chars (last resort)
        if not names:
            logger.info("No contextual names found, checking for capitalized words...")
            words = text.split()
            for word in words:
                cleaned = word.strip('.,!?;:\'"')
                if cleaned and cleaned[0].isupper() and len(cleaned) > 2:
                    # Filter common words
                    if cleaned not in {'I', 'The', 'My', 'Your', 'Our', 'Is', 'Am', 'Are', 'Have', 'Name', 'Want', 'Know'}:
                        if cleaned not in names:
                            names.append(cleaned)
                            logger.info(f"Extracted capitalized word: '{cleaned}'")
        
        if names:
            pii_values['REDACTED_PERSON'] = names
            logger.info(f"Extracted {len(names)} person names: {names}")
        
        logger.info(f"Final extracted PII: {pii_values}")
        return pii_values

    
    @staticmethod
    def anonymize(text: str) -> Tuple[str, List[Dict], Dict[str, any]]:
        """
        Detect and anonymize PII using multiple scanners
        Returns: (anonymized_text, entities_list, scanner_results)
        
        IMPORTANT: Extract actual PII VALUES from original text FIRST
        before anonymization redacts them!
        """
        entities = []
        scanner_results = {
            "secrets": {"detected": False, "is_valid": True, "risk_score": 0.0}
        }
        
        try:
            # ================================================================
            # STEP 1: EXTRACT ACTUAL PII VALUES FROM ORIGINAL TEXT FIRST
            # This MUST happen before anonymization!
            # ================================================================
            logger.info(f"Original text: '{text}'")
            pii_values_by_type = ThreadSafePIIDetector._extract_pii_patterns(text)
            logger.info(f"Extracted actual PII values BEFORE anonymization: {pii_values_by_type}")
            
            # ================================================================
            # STEP 2: Run anonymization (this will redact values)
            # ================================================================
            try:
                vault, pii_scanner = ThreadSafePIIDetector.create_detector()
                sanitized_text, is_valid_pii, risk_score_pii = pii_scanner.scan(text)
                logger.info(f"Anonymized text: '{sanitized_text}'")

                # Extract tokens from anonymized text
                # Pattern matches [ENTITY_TYPE_NUMBER]
                tokens = re.findall(r'\[([A-Z_]+)_(\d+)\]', sanitized_text)
                logger.info(f"Tokens found: {tokens}")
                
                # Match tokens to actual values we extracted
                # Track how many of each type we've processed
                entity_type_indices = {}
                
                for entity_type, entity_num_str in tokens:
                    full_token = f"[{entity_type}_{entity_num_str}]"
                    
                    # Get the actual value we extracted from original text
                    actual_value = "REDACTED"  # Default fallback
                    
                    if entity_type in pii_values_by_type and pii_values_by_type[entity_type]:
                        # Get the next value for this entity type
                        if entity_type not in entity_type_indices:
                            entity_type_indices[entity_type] = 0
                        
                        idx = entity_type_indices[entity_type]
                        values_list = pii_values_by_type[entity_type]
                        
                        if idx < len(values_list):
                            actual_value = values_list[idx]
                            entity_type_indices[entity_type] += 1
                            logger.info(f"Token {full_token} matched to extracted value: '{actual_value}'")
                        else:
                            logger.warning(f"Token {full_token} has no matching extracted value (idx={idx}, available={len(values_list)})")
                    else:
                        logger.warning(f"No extracted values for entity type {entity_type}")
                    
                    entities.append({
                        "type": entity_type,
                        "value": actual_value,  # This is the ACTUAL detected value, not REDACTED
                        "token": full_token,
                        "source": "pii"
                    })
                
                logger.info(f"Final entities with actual values: {entities}")
                    
            except Exception as e:
                logger.error(f"PII Scanner error: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                sanitized_text = text
            
            # ================================================================
            # STEP 3: Run Secrets Scanner
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
                    logger.info(f"Secrets detected (risk: {risk_score_secrets})")
                    
            except Exception as e:
                logger.error(f"Secrets Scanner failed: {str(e)}")
            
            # ================================================================
            # Deduplicate and finalize
            # ================================================================
            entities = ThreadSafePIIDetector.deduplicate_entities(entities)
            
            logger.info(f"Returning {len(entities)} PII entities to be stored in security log")
            
            return sanitized_text, entities, scanner_results
            
        except Exception as e:
            logger.error(f"PII/Secrets detection failed: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
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