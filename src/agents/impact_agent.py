"""
Stock Impact Analysis Agent - Maps news to impacted stocks with confidence scores
"""
from typing import List, Dict, Optional
import logging

from src.config import COMPANIES, SECTORS, SUPPLY_CHAIN
from src.models.schemas import (
    StockImpact, ImpactType, ImpactAnalysisResult,
    EntityExtractionResult, NewsProcessingState
)


logger = logging.getLogger(__name__)


class StockImpactAgent:
    """
    Agent responsible for:
    1. Mapping extracted entities to stock symbols
    2. Calculating impact confidence scores
    3. Identifying cross-sector (supply chain) impacts
    
    Confidence Scoring:
    - Direct mention: 100%
    - Sector-wide impact: 60-80%
    - Regulatory impact: 30-70%
    - Supply chain impact: 40-60%
    """
    
    def __init__(self):
        self.companies = COMPANIES
        self.sectors = SECTORS
        self.supply_chain = SUPPLY_CHAIN
        
        # Build reverse lookups
        self._build_lookups()
        
        logger.info("StockImpactAgent initialized")
    
    def _build_lookups(self):
        """Build lookup dictionaries for fast mapping"""
        # Sector to companies mapping
        self.sector_to_companies: Dict[str, List[Dict]] = {}
        
        for company_name, info in self.companies.items():
            sector = info.get('sector')
            if sector:
                if sector not in self.sector_to_companies:
                    self.sector_to_companies[sector] = []
                self.sector_to_companies[sector].append({
                    'name': company_name,
                    **info
                })
        
        # Ticker to company mapping
        self.ticker_to_company: Dict[str, str] = {}
        for company_name, info in self.companies.items():
            if info.get('ticker_nse'):
                self.ticker_to_company[info['ticker_nse']] = company_name
            if info.get('ticker_bse'):
                self.ticker_to_company[info['ticker_bse']] = company_name
    
    # ================== Impact Calculation Methods ==================
    
    def map_direct_mentions(self, entities: EntityExtractionResult) -> List[StockImpact]:
        """
        Map directly mentioned companies to stock impacts.
        
        Confidence: 1.0 (100%) for direct mentions
        """
        impacts = []
        seen_symbols = set()
        
        for company_entity in entities.companies:
            company_name = company_entity.value
            company_info = self.companies.get(company_name, {})
            
            ticker = company_info.get('ticker_nse')
            if not ticker or ticker in seen_symbols:
                continue
            
            seen_symbols.add(ticker)
            
            impacts.append(StockImpact(
                symbol=company_name,
                ticker_nse=ticker,
                ticker_bse=company_info.get('ticker_bse'),
                confidence=1.0,
                impact_type=ImpactType.DIRECT,
                reasoning=f"Directly mentioned in article"
            ))
        
        return impacts
    
    def map_sector_impacts(self, entities: EntityExtractionResult, exclude_direct: Optional[List[str]] = None) -> List[StockImpact]:
        """
        Map sector-wide news to all companies in the sector.
        
        Confidence: 0.6-0.8 based on sector specificity
        """
        impacts = []
        exclude_list = exclude_direct if exclude_direct is not None else []
        
        for sector in entities.sectors:
            companies_in_sector = self.sector_to_companies.get(sector, [])
            
            for company in companies_in_sector:
                # Skip if already in direct mentions
                if company['ticker_nse'] in exclude_list:
                    continue
                
                # Calculate confidence based on sector size and news type
                base_confidence = 0.7
                
                # Adjust confidence based on sector size
                sector_size = len(companies_in_sector)
                if sector_size > 10:
                    confidence = base_confidence - 0.1
                elif sector_size < 5:
                    confidence = base_confidence + 0.1
                else:
                    confidence = base_confidence
                
                impacts.append(StockImpact(
                    symbol=company['name'],
                    ticker_nse=company.get('ticker_nse'),
                    ticker_bse=company.get('ticker_bse'),
                    confidence=round(confidence, 2),
                    impact_type=ImpactType.SECTOR,
                    reasoning=f"Part of {sector} sector mentioned in article"
                ))
        
        return impacts
    
    def map_regulatory_impacts(self, entities: EntityExtractionResult) -> List[StockImpact]:
        """
        Map regulatory news to affected sectors/companies.
        
        Confidence: 0.3-0.7 based on regulator and event type
        """
        impacts = []
        
        # Regulator to sector mapping
        regulator_sectors = {
            "RBI": ["Banking", "Financial Services"],
            "SEBI": ["Financial Services"],
            "IRDAI": ["Financial Services"],  # Insurance
            "PFRDA": ["Financial Services"],  # Pension
            "Ministry of Finance": ["Banking", "Financial Services"],
            "NCLT": []  # Case-specific
        }
        
        for regulator_entity in entities.regulators:
            regulator = regulator_entity.value
            affected_sectors = regulator_sectors.get(regulator, [])
            
            for sector in affected_sectors:
                companies = self.sector_to_companies.get(sector, [])
                
                for company in companies:
                    # Check if event affects this sector (rate changes affect banks more)
                    confidence = 0.5
                    
                    # Adjust based on events
                    for event in entities.events:
                        if event.value == "rate_change" and sector == "Banking":
                            confidence = 0.75
                        elif event.value in ["merger", "ipo", "buyback"]:
                            confidence = 0.4  # More specific to individual companies
                    
                    impacts.append(StockImpact(
                        symbol=company['name'],
                        ticker_nse=company.get('ticker_nse'),
                        ticker_bse=company.get('ticker_bse'),
                        confidence=round(confidence, 2),
                        impact_type=ImpactType.REGULATORY,
                        reasoning=f"Affected by {regulator} regulatory action"
                    ))
        
        return impacts
    
    def map_supply_chain_impacts(self, entities: EntityExtractionResult) -> List[StockImpact]:
        """
        Map supply chain/cross-sector impacts.
        
        Example: Steel price increase → Auto sector impact
        
        Confidence: 0.4-0.6
        """
        impacts = []
        
        # Check for supply chain triggers in events/sectors
        for sector in entities.sectors:
            if sector in self.supply_chain:
                affected_sectors = self.supply_chain[sector]
                
                for affected_sector in affected_sectors:
                    companies = self.sector_to_companies.get(affected_sector, [])
                    
                    for company in companies:
                        impacts.append(StockImpact(
                            symbol=company['name'],
                            ticker_nse=company.get('ticker_nse'),
                            ticker_bse=company.get('ticker_bse'),
                            confidence=0.5,
                            impact_type=ImpactType.SUPPLY_CHAIN,
                            reasoning=f"Supply chain impact: {sector} → {affected_sector}"
                        ))
        
        return impacts
    
    # ================== Main Analysis Method ==================
    
    def analyze_impact(self, entities: EntityExtractionResult) -> ImpactAnalysisResult:
        """
        Analyze full stock impact from extracted entities.
        
        Args:
            entities: Extracted entities from article
            
        Returns:
            ImpactAnalysisResult with all impacted stocks
        """
        all_impacts = []
        
        # 1. Direct mentions (highest confidence)
        direct_impacts = self.map_direct_mentions(entities)
        all_impacts.extend(direct_impacts)
        direct_symbols = [i.ticker_nse for i in direct_impacts if i.ticker_nse]
        
        # 2. Sector-wide impacts
        sector_impacts = self.map_sector_impacts(entities, exclude_direct=direct_symbols)
        all_impacts.extend(sector_impacts)
        
        # 3. Regulatory impacts
        if entities.regulators:
            reg_impacts = self.map_regulatory_impacts(entities)
            all_impacts.extend(reg_impacts)
        
        # 4. Supply chain impacts (optional, for bonus feature)
        # supply_impacts = self.map_supply_chain_impacts(entities)
        # all_impacts.extend(supply_impacts)
        
        # Deduplicate by symbol, keeping highest confidence
        deduplicated = self._deduplicate_impacts(all_impacts)
        
        # Sort by confidence
        deduplicated.sort(key=lambda x: x.confidence, reverse=True)
        
        # Generate summary
        summary = self._generate_summary(deduplicated, entities)
        
        result = ImpactAnalysisResult(
            impacted_stocks=deduplicated,
            primary_sectors=entities.sectors,
            impact_summary=summary
        )
        
        logger.info(f"Impact analysis: {len(deduplicated)} stocks affected, "
                   f"{len([i for i in deduplicated if i.confidence >= 0.8])} high-confidence")
        
        return result
    
    def _deduplicate_impacts(self, impacts: List[StockImpact]) -> List[StockImpact]:
        """Deduplicate impacts, keeping highest confidence for each symbol"""
        best_impacts: Dict[str, StockImpact] = {}
        
        for impact in impacts:
            key = impact.ticker_nse or impact.symbol
            
            if key not in best_impacts or impact.confidence > best_impacts[key].confidence:
                best_impacts[key] = impact
        
        return list(best_impacts.values())
    
    def _generate_summary(self, impacts: List[StockImpact], entities: EntityExtractionResult) -> str:
        """Generate human-readable impact summary"""
        if not impacts:
            return "No significant stock impact detected."
        
        direct = [i for i in impacts if i.impact_type == ImpactType.DIRECT]
        sector = [i for i in impacts if i.impact_type == ImpactType.SECTOR]
        regulatory = [i for i in impacts if i.impact_type == ImpactType.REGULATORY]
        
        parts = []
        
        if direct:
            stocks = [i.symbol for i in direct[:3]]
            parts.append(f"Directly impacts: {', '.join(stocks)}")
        
        if sector:
            sectors = []
            for i in sector:
                reasoning = i.reasoning or ""
                if "Part of" in reasoning:
                    parts_list = reasoning.split("Part of ")
                    if len(parts_list) > 1:
                        sector_part = parts_list[1].split(" sector")[0]
                        sectors.append(sector_part)
            sectors = list(set(sectors))
            if sectors:
                parts.append(f"Sector-wide impact on: {', '.join(sectors[:2])}")
        
        if regulatory:
            parts.append(f"Regulatory implications for {len(regulatory)} stocks")
        
        return ". ".join(parts) + "." if parts else "Impact analysis complete."
    
    # ================== LangGraph Integration ==================
    
    async def process(self, state: NewsProcessingState) -> NewsProcessingState:
        """
        Process state for LangGraph pipeline.
        """
        if not state.entities:
            logger.warning("No entities to analyze for stock impact")
            return state
        
        result = self.analyze_impact(state.entities)
        state.stock_impacts = result.impacted_stocks
        
        return state


# ================== Example Usage ==================

def demonstrate_impact_analysis():
    """Demonstrate stock impact analysis"""
    from src.agents.ner_agent import EntityExtractionAgent
    
    ner_agent = EntityExtractionAgent()
    impact_agent = StockImpactAgent()
    
    examples = [
        "HDFC Bank announces 15% dividend, board approves stock buyback",
        "RBI raises repo rate by 25bps to 6.75%, citing inflation concerns",
        "Banking sector NPAs decline to 5-year low, credit growth at 16%",
        "Reliance Industries reports Q3 profit of Rs 18,000 crore"
    ]
    
    for text in examples:
        print(f"\n{'='*60}")
        print(f"Article: {text}")
        
        # Extract entities
        entities = ner_agent.extract_all(text)
        
        # Analyze impact
        result = impact_agent.analyze_impact(entities)
        
        print(f"\nImpacted Stocks:")
        for impact in result.impacted_stocks[:5]:
            print(f"  - {impact.symbol} ({impact.ticker_nse}): "
                  f"{impact.confidence:.0%} confidence [{impact.impact_type.value}]")
            print(f"    Reason: {impact.reasoning}")
        
        print(f"\nSummary: {result.impact_summary}")


# Singleton instance
_impact_agent: Optional[StockImpactAgent] = None


def get_impact_agent() -> StockImpactAgent:
    """Get or create impact agent singleton"""
    global _impact_agent
    if _impact_agent is None:
        _impact_agent = StockImpactAgent()
    return _impact_agent
