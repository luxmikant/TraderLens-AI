"""
Multi-lingual Support for Indian Financial News

Supports:
1. Hindi (हिंदी) - Most common after English
2. Marathi (मराठी) - Maharashtra business news
3. Tamil (தமிழ்) - South Indian business centers
4. Telugu (తెలుగు) - AP/Telangana markets
5. Gujarati (ગુજરાતી) - Strong trading community
6. Bengali (বাংলা) - Eastern markets

Uses:
- Google Translate API (or IndicTrans2 for offline)
- Language detection
- Regional entity recognition
- Cross-lingual embeddings
"""
import logging
import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class SupportedLanguage(str, Enum):
    """Supported Indian languages"""
    ENGLISH = "en"
    HINDI = "hi"
    MARATHI = "mr"
    TAMIL = "ta"
    TELUGU = "te"
    GUJARATI = "gu"
    BENGALI = "bn"
    KANNADA = "kn"
    MALAYALAM = "ml"


@dataclass
class TranslationResult:
    """Result of translation"""
    original_text: str
    translated_text: str
    source_lang: SupportedLanguage
    target_lang: SupportedLanguage
    confidence: float
    entities_preserved: List[str]  # Entities kept in original form


@dataclass 
class LanguageDetectionResult:
    """Result of language detection"""
    text: str
    detected_lang: SupportedLanguage
    confidence: float
    is_mixed: bool  # True if multiple languages detected


class MultilingualProcessor:
    """
    Processes multi-lingual Indian financial news.
    
    Features:
    1. Automatic language detection
    2. Translation to English for processing
    3. Entity preservation (company names stay in original)
    4. Regional financial term mapping
    5. Cross-lingual search
    
    Usage:
        processor = MultilingualProcessor()
        
        # Detect language
        result = processor.detect_language("आरबीआई ने ब्याज दरों में वृद्धि की")
        print(result.detected_lang)  # SupportedLanguage.HINDI
        
        # Translate for processing
        translated = processor.translate_to_english(hindi_text)
        print(translated.translated_text)
    """
    
    # Unicode ranges for language detection
    LANGUAGE_RANGES = {
        SupportedLanguage.HINDI: (0x0900, 0x097F),      # Devanagari
        SupportedLanguage.MARATHI: (0x0900, 0x097F),    # Also Devanagari
        SupportedLanguage.TAMIL: (0x0B80, 0x0BFF),
        SupportedLanguage.TELUGU: (0x0C00, 0x0C7F),
        SupportedLanguage.GUJARATI: (0x0A80, 0x0AFF),
        SupportedLanguage.BENGALI: (0x0980, 0x09FF),
        SupportedLanguage.KANNADA: (0x0C80, 0x0CFF),
        SupportedLanguage.MALAYALAM: (0x0D00, 0x0D7F),
    }
    
    # Common financial terms in regional languages
    # Format: {lang: {term_in_lang: english_term}}
    FINANCIAL_TERMS = {
        SupportedLanguage.HINDI: {
            "शेयर": "share",
            "बाजार": "market",
            "मुनाफा": "profit",
            "नुकसान": "loss",
            "ब्याज": "interest",
            "दर": "rate",
            "निवेश": "investment",
            "कंपनी": "company",
            "बैंक": "bank",
            "रिजर्व बैंक": "Reserve Bank",
            "सेबी": "SEBI",
            "आईपीओ": "IPO",
            "लाभांश": "dividend",
            "बोनस": "bonus",
            "तिमाही": "quarterly",
            "वार्षिक": "annual",
            "राजस्व": "revenue",
            "आय": "income",
            "खर्च": "expense",
            "कर्ज": "debt",
        },
        SupportedLanguage.MARATHI: {
            "भांडवल": "capital",
            "बाजार": "market", 
            "नफा": "profit",
            "तोटा": "loss",
            "गुंतवणूक": "investment",
            "व्याज": "interest",
        },
        SupportedLanguage.TAMIL: {
            "பங்கு": "share",
            "சந்தை": "market",
            "லாபம்": "profit",
            "நட்டம்": "loss",
            "வட்டி": "interest",
            "முதலீடு": "investment",
        },
        SupportedLanguage.TELUGU: {
            "షేర్": "share",
            "మార్కెట్": "market",
            "లాభం": "profit",
            "నష్టం": "loss",
            "వడ్డీ": "interest",
        },
        SupportedLanguage.GUJARATI: {
            "શેર": "share",
            "બજાર": "market",
            "નફો": "profit",
            "ખોટ": "loss",
            "વ્યાજ": "interest",
            "રોકાણ": "investment",
        },
        SupportedLanguage.BENGALI: {
            "শেয়ার": "share",
            "বাজার": "market",
            "লাভ": "profit",
            "ক্ষতি": "loss",
            "সুদ": "interest",
            "বিনিয়োগ": "investment",
        },
    }
    
    # Regional company name mappings
    REGIONAL_ENTITIES = {
        SupportedLanguage.HINDI: {
            "रिलायंस": "Reliance",
            "टाटा": "Tata",
            "इंफोसिस": "Infosys",
            "एचडीएफसी": "HDFC",
            "आईसीआईसीआई": "ICICI",
            "एसबीआई": "SBI",
            "भारती": "Bharti",
            "विप्रो": "Wipro",
            "टीसीएस": "TCS",
            "आरबीआई": "RBI",
            "सेबी": "SEBI",
        },
        SupportedLanguage.GUJARATI: {
            "રિલાયન્સ": "Reliance",
            "ટાટા": "Tata",
            "અદાણી": "Adani",
        },
    }
    
    def __init__(self, use_api: bool = False, api_key: Optional[str] = None):
        """
        Initialize multilingual processor.
        
        Args:
            use_api: Use external API for translation (Google/Azure)
            api_key: API key for translation service
        """
        self.use_api = use_api
        self.api_key = api_key
        self._translator = None
        
        logger.info(f"MultilingualProcessor initialized (API: {use_api})")
    
    def detect_language(self, text: str) -> LanguageDetectionResult:
        """
        Detect the language of input text.
        
        Uses Unicode range analysis for Indian languages.
        """
        if not text or not text.strip():
            return LanguageDetectionResult(
                text=text,
                detected_lang=SupportedLanguage.ENGLISH,
                confidence=0.5,
                is_mixed=False
            )
        
        # Count characters in each language range
        lang_counts = {lang: 0 for lang in SupportedLanguage}
        lang_counts[SupportedLanguage.ENGLISH] = 0
        
        for char in text:
            code_point = ord(char)
            
            # Check each language range
            matched = False
            for lang, (start, end) in self.LANGUAGE_RANGES.items():
                if start <= code_point <= end:
                    lang_counts[lang] += 1
                    matched = True
                    break
            
            # If ASCII letter, count as English
            if not matched and char.isalpha() and code_point < 128:
                lang_counts[SupportedLanguage.ENGLISH] += 1
        
        # Find dominant language
        total_chars = sum(lang_counts.values())
        if total_chars == 0:
            return LanguageDetectionResult(
                text=text,
                detected_lang=SupportedLanguage.ENGLISH,
                confidence=0.5,
                is_mixed=False
            )
        
        max_lang = max(lang_counts, key=lambda x: lang_counts.get(x, 0))
        max_count = lang_counts[max_lang]
        confidence = max_count / total_chars if total_chars > 0 else 0.5
        
        # Check if mixed (multiple languages with >20% each)
        is_mixed = sum(1 for c in lang_counts.values() if c > total_chars * 0.2) > 1
        
        # Special case: Hindi and Marathi use same script
        # Use keyword detection if confidence is high
        if max_lang in [SupportedLanguage.HINDI, SupportedLanguage.MARATHI]:
            if self._has_marathi_keywords(text):
                max_lang = SupportedLanguage.MARATHI
        
        return LanguageDetectionResult(
            text=text,
            detected_lang=max_lang,
            confidence=confidence,
            is_mixed=is_mixed
        )
    
    def _has_marathi_keywords(self, text: str) -> bool:
        """Check for Marathi-specific keywords"""
        marathi_markers = ["आहे", "असे", "होते", "केले", "म्हणाले"]
        return any(marker in text for marker in marathi_markers)
    
    def translate_to_english(
        self, 
        text: str,
        source_lang: Optional[SupportedLanguage] = None,
        preserve_entities: bool = True
    ) -> TranslationResult:
        """
        Translate text to English for processing.
        
        Args:
            text: Text to translate
            source_lang: Source language (auto-detect if None)
            preserve_entities: Keep entity names in original form
            
        Returns:
            TranslationResult with translated text
        """
        # Detect language if not provided
        if source_lang is None:
            detection = self.detect_language(text)
            source_lang = detection.detected_lang
        
        # If already English, return as-is
        if source_lang == SupportedLanguage.ENGLISH:
            return TranslationResult(
                original_text=text,
                translated_text=text,
                source_lang=source_lang,
                target_lang=SupportedLanguage.ENGLISH,
                confidence=1.0,
                entities_preserved=[]
            )
        
        # Extract and preserve entities
        preserved_entities = []
        processed_text = text
        
        if preserve_entities and source_lang in self.REGIONAL_ENTITIES:
            for regional, english in self.REGIONAL_ENTITIES[source_lang].items():
                if regional in processed_text:
                    preserved_entities.append(english)
                    processed_text = processed_text.replace(regional, f"__{english}__")
        
        # Translate financial terms
        if source_lang in self.FINANCIAL_TERMS:
            for term, english in self.FINANCIAL_TERMS[source_lang].items():
                processed_text = processed_text.replace(term, english)
        
        # If using API, call external translation
        if self.use_api and self.api_key:
            translated = self._translate_with_api(processed_text, source_lang)
        else:
            # Basic fallback: just term replacement (entities + financial terms)
            translated = processed_text
        
        # Restore preserved entities
        for entity in preserved_entities:
            translated = translated.replace(f"__{entity}__", entity)
        
        return TranslationResult(
            original_text=text,
            translated_text=translated,
            source_lang=source_lang,
            target_lang=SupportedLanguage.ENGLISH,
            confidence=0.8 if self.use_api else 0.5,
            entities_preserved=preserved_entities
        )
    
    def _translate_with_api(
        self, 
        text: str, 
        source_lang: SupportedLanguage
    ) -> str:
        """Call external translation API"""
        try:
            # Try Google Translate
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(
                source=source_lang.value,
                target='en'
            )
            return translator.translate(text)
        except ImportError:
            logger.warning("deep_translator not installed, using term replacement only")
            return text
        except Exception as e:
            logger.error(f"Translation API error: {e}")
            return text
    
    def extract_entities_multilingual(
        self,
        text: str,
        source_lang: Optional[SupportedLanguage] = None
    ) -> List[Dict[str, Any]]:
        """
        Extract entities from multilingual text.
        
        Returns entities with both original and English forms.
        """
        if source_lang is None:
            detection = self.detect_language(text)
            source_lang = detection.detected_lang
        
        entities = []
        
        # Check regional entity mappings
        if source_lang in self.REGIONAL_ENTITIES:
            for regional, english in self.REGIONAL_ENTITIES[source_lang].items():
                if regional in text:
                    entities.append({
                        "original": regional,
                        "english": english,
                        "language": source_lang.value,
                        "type": "company" if english in ["Reliance", "Tata", "Infosys", "HDFC", "ICICI", "SBI", "TCS", "Wipro"] else "regulator"
                    })
        
        return entities
    
    def normalize_query(
        self,
        query: str,
        target_lang: SupportedLanguage = SupportedLanguage.ENGLISH
    ) -> str:
        """
        Normalize a search query to target language.
        
        Useful for cross-lingual search.
        """
        detection = self.detect_language(query)
        
        if detection.detected_lang == target_lang:
            return query
        
        translation = self.translate_to_english(query, detection.detected_lang)
        return translation.translated_text
    
    def get_supported_languages(self) -> List[Dict[str, str]]:
        """Get list of supported languages with their codes"""
        return [
            {"code": lang.value, "name": lang.name, "native": native}
            for lang, native in [
                (SupportedLanguage.ENGLISH, "English"),
                (SupportedLanguage.HINDI, "हिंदी"),
                (SupportedLanguage.MARATHI, "मराठी"),
                (SupportedLanguage.TAMIL, "தமிழ்"),
                (SupportedLanguage.TELUGU, "తెలుగు"),
                (SupportedLanguage.GUJARATI, "ગુજરાતી"),
                (SupportedLanguage.BENGALI, "বাংলা"),
                (SupportedLanguage.KANNADA, "ಕನ್ನಡ"),
                (SupportedLanguage.MALAYALAM, "മലയാളം"),
            ]
        ]


# Singleton
_processor: Optional[MultilingualProcessor] = None


def get_multilingual_processor(use_api: bool = False) -> MultilingualProcessor:
    """Get or create the multilingual processor"""
    global _processor
    if _processor is None:
        _processor = MultilingualProcessor(use_api=use_api)
    return _processor
