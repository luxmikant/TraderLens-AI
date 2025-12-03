"""
Entity Extraction Agent - Extracts structured entities from financial news
"""
import re
from typing import List, Dict, Optional, Tuple
import logging

from src.config import COMPANIES, SECTORS, REGULATORS
from src.models.schemas import (
    ExtractedEntity, EntityExtractionResult, EntityType,
    NewsProcessingState
)


logger = logging.getLogger(__name__)


class EntityExtractionAgent:
    """
    Agent responsible for:
    1. Extracting named entities (Companies, People, Regulators)
    2. Classifying sectors from content
    3. Detecting financial events
    
    Uses hybrid approach:
    - Rule-based extraction for known entities (companies, regulators)
    - Pattern matching for financial terms
    - Optional: spaCy NER for general entities
    
    Target: ≥90% entity extraction precision
    """
    
    def __init__(self, use_spacy: bool = False):
        """
        Initialize the entity extraction agent.
        
        Args:
            use_spacy: Whether to use spaCy for NER (requires spacy model)
        """
        self.companies = COMPANIES
        self.sectors = SECTORS
        self.regulators = REGULATORS
        
        # Build lookup patterns
        self._build_patterns()
        
        # Optional spaCy NER
        self.nlp = None
        if use_spacy:
            self._init_spacy()
        
        logger.info("EntityExtractionAgent initialized")
    
    def _build_patterns(self):
        """Build regex patterns for entity extraction"""
        # Company name patterns (sorted by length for greedy matching)
        company_names = sorted(self.companies.keys(), key=len, reverse=True)
        self.company_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(name) for name in company_names) + r')\b',
            re.IGNORECASE
        )
        
        # Regulator patterns
        self.regulator_pattern = re.compile(
            r'\b(' + '|'.join(re.escape(reg) for reg in self.regulators) + r')\b',
            re.IGNORECASE
        )
        
        # Stock ticker patterns (NSE: HDFCBANK, BSE: 500180)
        self.ticker_pattern = re.compile(
            r'\b([A-Z]{2,15})\b(?=\s*(?:stock|share|scrip|equity))|'
            r'\bNSE[:\s]+([A-Z]{2,15})\b|'
            r'\bBSE[:\s]+(\d{5,6})\b',
            re.IGNORECASE
        )
        
        # Financial event patterns
        self.event_patterns = {
            "dividend": re.compile(r'\b(dividend|interim dividend|final dividend)\b', re.I),
            "buyback": re.compile(r'\b(buyback|buy\s*back|share repurchase)\b', re.I),
            "merger": re.compile(r'\b(merger|acquisition|M&A|takeover|amalgamation)\b', re.I),
            "ipo": re.compile(r'\b(IPO|initial public offering|public issue)\b', re.I),
            "earnings": re.compile(r'\b(earnings|quarterly results|Q[1-4] results|annual results)\b', re.I),
            "rate_change": re.compile(r'\b(repo rate|interest rate|rate hike|rate cut|basis points|bps)\b', re.I),
            "board_meeting": re.compile(r'\b(board meeting|board of directors)\b', re.I),
            "stock_split": re.compile(r'\b(stock split|share split|bonus issue)\b', re.I),
            "rights_issue": re.compile(r'\b(rights issue|preferential issue|QIP)\b', re.I),
        }
        
        # Person name patterns (basic - CEO, MD, Chairman, etc.)
        self.person_title_pattern = re.compile(
            r'(?:CEO|MD|Chairman|CFO|Director|President|Founder)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
            re.IGNORECASE
        )
        
        # Percentage patterns
        self.percentage_pattern = re.compile(r'(\d+(?:\.\d+)?)\s*%')
        
        # Money patterns
        self.money_pattern = re.compile(
            r'(?:Rs\.?|INR|₹)\s*(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:crore|lakh|million|billion)?',
            re.IGNORECASE
        )
    
    def _init_spacy(self):
        """Initialize spaCy NER model"""
        try:
            import spacy
            self.nlp = spacy.load("en_core_web_sm")
            logger.info("spaCy NER model loaded")
        except Exception as e:
            logger.warning(f"Could not load spaCy: {e}")
            self.nlp = None
    
    # ================== Entity Extraction Methods ==================
    
    def extract_companies(self, text: str) -> List[ExtractedEntity]:
        """Extract company mentions from text"""
        entities = []
        seen = set()
        
        for match in self.company_pattern.finditer(text):
            company_name = match.group(1)
            
            # Normalize company name
            normalized = self._normalize_company_name(company_name)
            if normalized in seen:
                continue
            seen.add(normalized)
            
            company_info = self.companies.get(normalized, {})
            
            entities.append(ExtractedEntity(
                entity_type=EntityType.COMPANY,
                value=normalized,
                confidence=1.0,
                start_pos=match.start(),
                end_pos=match.end(),
                metadata={
                    "ticker_nse": company_info.get("ticker_nse"),
                    "ticker_bse": company_info.get("ticker_bse"),
                    "sector": company_info.get("sector")
                }
            ))
        
        return entities
    
    def extract_regulators(self, text: str) -> List[ExtractedEntity]:
        """Extract regulator mentions from text"""
        entities = []
        seen = set()
        
        for match in self.regulator_pattern.finditer(text):
            regulator = match.group(1)
            normalized = self._normalize_regulator(regulator)
            
            if normalized in seen:
                continue
            seen.add(normalized)
            
            entities.append(ExtractedEntity(
                entity_type=EntityType.REGULATOR,
                value=normalized,
                confidence=1.0,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        
        return entities
    
    def extract_events(self, text: str) -> List[ExtractedEntity]:
        """Extract financial events from text"""
        entities = []
        
        for event_type, pattern in self.event_patterns.items():
            matches = pattern.findall(text)
            if matches:
                entities.append(ExtractedEntity(
                    entity_type=EntityType.EVENT,
                    value=event_type,
                    confidence=0.9,
                    metadata={"matches": matches[:3]}  # Keep first 3 matches
                ))
        
        return entities
    
    def extract_people(self, text: str) -> List[ExtractedEntity]:
        """Extract person names from text"""
        entities = []
        
        # Extract people with titles
        for match in self.person_title_pattern.finditer(text):
            name = match.group(1).strip()
            entities.append(ExtractedEntity(
                entity_type=EntityType.PERSON,
                value=name,
                confidence=0.85,
                start_pos=match.start(),
                end_pos=match.end()
            ))
        
        # Use spaCy if available
        if self.nlp:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    entities.append(ExtractedEntity(
                        entity_type=EntityType.PERSON,
                        value=ent.text,
                        confidence=0.8,
                        start_pos=ent.start_char,
                        end_pos=ent.end_char
                    ))
        
        return entities
    
    def classify_sectors(self, text: str) -> List[str]:
        """Classify sectors based on text content"""
        text_lower = text.lower()
        detected_sectors = []
        
        for sector, keywords in self.sectors.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    if sector not in detected_sectors:
                        detected_sectors.append(sector)
                    break
        
        # Also get sectors from detected companies
        companies = self.extract_companies(text)
        for company in companies:
            if company.metadata and company.metadata.get("sector"):
                sector = company.metadata["sector"]
                if sector not in detected_sectors:
                    detected_sectors.append(sector)
        
        return detected_sectors
    
    def _normalize_company_name(self, name: str) -> str:
        """Normalize company name to canonical form"""
        name = name.strip()
        
        # Check exact match first
        if name in self.companies:
            return name
        
        # Check case-insensitive
        for canonical in self.companies:
            if canonical.lower() == name.lower():
                return canonical
        
        return name
    
    def _normalize_regulator(self, regulator: str) -> str:
        """Normalize regulator name"""
        regulator = regulator.strip().upper()
        
        mappings = {
            "RESERVE BANK OF INDIA": "RBI",
            "RESERVE BANK": "RBI",
            "SECURITIES AND EXCHANGE BOARD": "SEBI",
            "INSURANCE REGULATORY": "IRDAI",
            "PENSION FUND REGULATORY": "PFRDA",
            "MINISTRY OF FINANCE": "Ministry of Finance",
            "FINANCE MINISTRY": "Ministry of Finance",
            "NATIONAL COMPANY LAW TRIBUNAL": "NCLT"
        }
        
        return mappings.get(regulator, regulator)
    
    # ================== Main Extraction Method ==================
    
    def extract_all(self, text: str) -> EntityExtractionResult:
        """
        Extract all entities from text.
        
        Args:
            text: Article text (title + content)
            
        Returns:
            EntityExtractionResult with all extracted entities
        """
        companies = self.extract_companies(text)
        regulators = self.extract_regulators(text)
        events = self.extract_events(text)
        people = self.extract_people(text)
        sectors = self.classify_sectors(text)
        
        # Combine all entities
        all_entities = companies + regulators + events + people
        
        result = EntityExtractionResult(
            companies=companies,
            people=people,
            regulators=regulators,
            sectors=sectors,
            events=events,
            raw_entities=all_entities
        )
        
        logger.debug(f"Extracted: {len(companies)} companies, {len(regulators)} regulators, "
                    f"{len(sectors)} sectors, {len(events)} events, {len(people)} people")
        
        return result
    
    # ================== LangGraph Integration ==================
    
    async def process(self, state: NewsProcessingState) -> NewsProcessingState:
        """
        Process state for LangGraph pipeline.
        """
        content = state.normalized_content or f"{state.raw_news.title}\n\n{state.raw_news.content}"
        
        # Extract entities
        state.entities = self.extract_all(content)
        
        return state
    
    def extract_from_query(self, query: str) -> EntityExtractionResult:
        """
        Extract entities from a user query.
        Used for context-aware query expansion.
        """
        return self.extract_all(query)


# ================== Example Usage ==================

def demonstrate_extraction():
    """Demonstrate entity extraction with example articles"""
    agent = EntityExtractionAgent()
    
    examples = [
        "HDFC Bank announces 15% dividend, board approves stock buyback. CEO Sashidhar Jagdishan expressed confidence.",
        "RBI raises repo rate by 25bps to 6.75%, citing inflation concerns. The Reserve Bank's MPC voted 5-1.",
        "Reliance Industries Q3 results: Net profit up 12% to Rs 18,000 crore. Mukesh Ambani announced new investments.",
        "Banking sector NPAs decline to 5-year low. ICICI Bank, SBI, Kotak show improvement.",
    ]
    
    for text in examples:
        print(f"\n{'='*60}")
        print(f"Text: {text[:80]}...")
        result = agent.extract_all(text)
        
        print(f"\nCompanies: {[e.value for e in result.companies]}")
        print(f"Regulators: {[e.value for e in result.regulators]}")
        print(f"Sectors: {result.sectors}")
        print(f"Events: {[e.value for e in result.events]}")
        print(f"People: {[e.value for e in result.people]}")


# Singleton instance
_ner_agent: Optional[EntityExtractionAgent] = None


def get_ner_agent() -> EntityExtractionAgent:
    """Get or create NER agent singleton"""
    global _ner_agent
    if _ner_agent is None:
        _ner_agent = EntityExtractionAgent()
    return _ner_agent
