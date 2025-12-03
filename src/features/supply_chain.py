"""
Supply Chain Impact Analysis

Models cross-sectoral effects:
- Auto → Steel, Rubber, Electronics
- Banking → NBFC, Insurance, Real Estate  
- IT → Software Services, Cloud, Consulting
- Pharma → Chemicals, Healthcare, Hospitals
- FMCG → Retail, Packaging, Agriculture
- Energy → Power, Refineries, Gas Distribution
"""
import logging
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ImpactDirection(str, Enum):
    """Direction of supply chain impact"""
    UPSTREAM = "upstream"      # Suppliers
    DOWNSTREAM = "downstream"  # Customers/distributors
    LATERAL = "lateral"        # Competitors/peers


class ImpactStrength(str, Enum):
    """Strength of the impact"""
    STRONG = "strong"    # >50% correlation
    MODERATE = "moderate"  # 25-50% correlation
    WEAK = "weak"        # <25% correlation


@dataclass
class SupplyChainLink:
    """Represents a link in the supply chain"""
    source_sector: str
    target_sector: str
    direction: ImpactDirection
    strength: ImpactStrength
    correlation: float  # -1 to 1
    description: str
    example_stocks: List[str]


@dataclass
class CrossSectorImpact:
    """Impact on a related sector"""
    sector: str
    direction: ImpactDirection
    strength: ImpactStrength
    impact_pct: float  # Expected % impact
    stocks: List[str]
    reasoning: str


class SupplyChainAnalyzer:
    """
    Analyzes cross-sectoral supply chain impacts.
    
    When news affects one sector, this model predicts
    spillover effects to related sectors.
    
    Example:
    - Steel prices rise → Auto sector costs increase → Bearish for auto
    - IT hiring surge → Positive for Tier-2 cities real estate
    - Banking NPA rise → Negative for NBFCs and microfinance
    """
    
    # Supply chain relationship matrix
    # Format: source_sector -> [(target, direction, strength, correlation, description)]
    SUPPLY_CHAIN = {
        "auto": [
            ("steel", ImpactDirection.UPSTREAM, ImpactStrength.STRONG, 0.65, 
             "Steel is primary raw material for auto", ["TATASTEEL", "JSWSTEEL", "SAIL"]),
            ("rubber", ImpactDirection.UPSTREAM, ImpactStrength.MODERATE, 0.45,
             "Tyres and rubber components", ["APOLLOTYRE", "MRF", "CEAT"]),
            ("electronics", ImpactDirection.UPSTREAM, ImpactStrength.MODERATE, 0.40,
             "Auto electronics and semiconductors", ["DIXON", "AMBER"]),
            ("nbfc", ImpactDirection.DOWNSTREAM, ImpactStrength.STRONG, 0.55,
             "Auto financing and leasing", ["BAJFINANCE", "CHOLA", "SHFL"]),
            ("auto_ancillary", ImpactDirection.LATERAL, ImpactStrength.STRONG, 0.70,
             "Auto component suppliers", ["MOTHERSON", "BOSCH", "BALKRISIND"]),
        ],
        "banking": [
            ("nbfc", ImpactDirection.LATERAL, ImpactStrength.STRONG, 0.60,
             "NBFCs compete and borrow from banks", ["BAJFINANCE", "CHOLA", "MUTHOOTFIN"]),
            ("insurance", ImpactDirection.LATERAL, ImpactStrength.MODERATE, 0.40,
             "Banks distribute insurance products", ["HDFCLIFE", "ICICIPRU", "SBILIFE"]),
            ("realty", ImpactDirection.DOWNSTREAM, ImpactStrength.MODERATE, 0.45,
             "Housing loans drive real estate", ["DLF", "GODREJPROP", "OBEROIRLTY"]),
            ("gold_finance", ImpactDirection.LATERAL, ImpactStrength.MODERATE, 0.35,
             "Gold loan competition", ["MUTHOOTFIN", "MANAPPURAM"]),
            ("fintech", ImpactDirection.LATERAL, ImpactStrength.MODERATE, 0.30,
             "Digital banking competition", ["PAYTM", "POLICYBZR"]),
        ],
        "it": [
            ("it_services", ImpactDirection.LATERAL, ImpactStrength.STRONG, 0.75,
             "Peer IT services companies", ["TCS", "INFY", "WIPRO", "HCLTECH"]),
            ("cloud", ImpactDirection.UPSTREAM, ImpactStrength.MODERATE, 0.45,
             "Cloud infrastructure providers", ["PERSISTENT", "COFORGE"]),
            ("staffing", ImpactDirection.UPSTREAM, ImpactStrength.MODERATE, 0.40,
             "IT staffing companies", ["TEAMLEASE", "QUESS"]),
            ("realty_commercial", ImpactDirection.DOWNSTREAM, ImpactStrength.WEAK, 0.25,
             "Tech park demand", ["EMBASSY", "MINDSPACE"]),
        ],
        "pharma": [
            ("chemicals", ImpactDirection.UPSTREAM, ImpactStrength.STRONG, 0.55,
             "API and chemical intermediates", ["PIDILITIND", "AARTIIND", "DEEPAKNITRATE"]),
            ("healthcare", ImpactDirection.DOWNSTREAM, ImpactStrength.MODERATE, 0.45,
             "Hospitals and diagnostics", ["APOLLOHOSP", "FORTIS", "METROPOLIS"]),
            ("crams", ImpactDirection.LATERAL, ImpactStrength.MODERATE, 0.50,
             "Contract research and manufacturing", ["SYNGENE", "LAURUS"]),
            ("packaging", ImpactDirection.UPSTREAM, ImpactStrength.WEAK, 0.20,
             "Pharma packaging", ["UFLEX", "HUHTAMAKI"]),
        ],
        "fmcg": [
            ("retail", ImpactDirection.DOWNSTREAM, ImpactStrength.STRONG, 0.60,
             "Retail distribution channels", ["DMART", "TRENT", "VMART"]),
            ("packaging", ImpactDirection.UPSTREAM, ImpactStrength.MODERATE, 0.40,
             "Consumer goods packaging", ["UFLEX", "EPL"]),
            ("agriculture", ImpactDirection.UPSTREAM, ImpactStrength.MODERATE, 0.35,
             "Agricultural commodities", ["ITC", "PATANJALI"]),
            ("logistics", ImpactDirection.UPSTREAM, ImpactStrength.WEAK, 0.25,
             "Supply chain and distribution", ["BLUEDART", "MAHINDRALOG"]),
        ],
        "energy": [
            ("power", ImpactDirection.DOWNSTREAM, ImpactStrength.STRONG, 0.55,
             "Power generation and utilities", ["NTPC", "POWERGRID", "TATAPOWER"]),
            ("refineries", ImpactDirection.LATERAL, ImpactStrength.STRONG, 0.65,
             "Oil refining companies", ["RELIANCE", "BPCL", "IOC"]),
            ("gas", ImpactDirection.LATERAL, ImpactStrength.MODERATE, 0.50,
             "Gas distribution", ["GAIL", "PETRONET", "IGL"]),
            ("renewables", ImpactDirection.LATERAL, ImpactStrength.MODERATE, 0.35,
             "Solar and wind energy", ["ADANIGREEN", "TATAPOWER"]),
        ],
        "metals": [
            ("mining", ImpactDirection.UPSTREAM, ImpactStrength.STRONG, 0.60,
             "Mining operations", ["COALINDIA", "NMDC", "VEDL"]),
            ("auto", ImpactDirection.DOWNSTREAM, ImpactStrength.MODERATE, 0.45,
             "Steel consumption in autos", ["TATAMOTORS", "M&M", "MARUTI"]),
            ("infrastructure", ImpactDirection.DOWNSTREAM, ImpactStrength.MODERATE, 0.50,
             "Construction steel demand", ["LT", "ULTRACEMCO"]),
            ("capital_goods", ImpactDirection.DOWNSTREAM, ImpactStrength.WEAK, 0.30,
             "Industrial equipment", ["SIEMENS", "ABB", "THERMAX"]),
        ],
        "telecom": [
            ("tower", ImpactDirection.UPSTREAM, ImpactStrength.STRONG, 0.55,
             "Telecom tower infrastructure", ["INDUSTOWER", "BHARTIARTL"]),
            ("equipment", ImpactDirection.UPSTREAM, ImpactStrength.MODERATE, 0.40,
             "Telecom equipment vendors", ["STERLITE", "HFCL"]),
            ("digital", ImpactDirection.DOWNSTREAM, ImpactStrength.MODERATE, 0.45,
             "Digital services and OTT", ["ZOMATO", "NYKAA"]),
        ],
    }
    
    # Reverse mapping for quick lookup
    REVERSE_IMPACTS: Dict[str, List[Tuple[str, SupplyChainLink]]] = {}
    
    def __init__(self):
        """Initialize and build reverse index"""
        self._build_reverse_index()
        logger.info("SupplyChainAnalyzer initialized")
    
    def _build_reverse_index(self):
        """Build reverse lookup from target to source sectors"""
        for source, links in self.SUPPLY_CHAIN.items():
            for target, direction, strength, corr, desc, stocks in links:
                if target not in self.REVERSE_IMPACTS:
                    self.REVERSE_IMPACTS[target] = []
                
                link = SupplyChainLink(
                    source_sector=source,
                    target_sector=target,
                    direction=direction,
                    strength=strength,
                    correlation=corr,
                    description=desc,
                    example_stocks=stocks
                )
                self.REVERSE_IMPACTS[target].append((source, link))
    
    def get_downstream_impacts(
        self,
        source_sector: str,
        sentiment_score: float,
        sentiment_label: str
    ) -> List[CrossSectorImpact]:
        """
        Get impacts on downstream sectors from news about source sector.
        
        Args:
            source_sector: The sector mentioned in news
            sentiment_score: Sentiment score (-1 to 1)
            sentiment_label: bullish/bearish/neutral
            
        Returns:
            List of cross-sector impacts
        """
        source_lower = source_sector.lower()
        impacts = []
        
        if source_lower not in self.SUPPLY_CHAIN:
            return impacts
        
        for target, direction, strength, corr, desc, stocks in self.SUPPLY_CHAIN[source_lower]:
            # Calculate impact based on sentiment and correlation
            if direction == ImpactDirection.UPSTREAM:
                # Upstream: inverse relationship (higher costs = negative)
                impact_pct = -sentiment_score * corr * 100
            else:
                # Downstream/Lateral: direct relationship
                impact_pct = sentiment_score * corr * 100
            
            # Strength affects magnitude
            strength_multiplier = {
                ImpactStrength.STRONG: 1.0,
                ImpactStrength.MODERATE: 0.7,
                ImpactStrength.WEAK: 0.4
            }
            impact_pct *= strength_multiplier[strength]
            
            # Generate reasoning
            if impact_pct > 0:
                reasoning = f"{sentiment_label.capitalize()} news in {source_sector} is positive for {target}: {desc}"
            elif impact_pct < 0:
                reasoning = f"{sentiment_label.capitalize()} news in {source_sector} is negative for {target}: {desc}"
            else:
                reasoning = f"News in {source_sector} has neutral impact on {target}: {desc}"
            
            impacts.append(CrossSectorImpact(
                sector=target,
                direction=direction,
                strength=strength,
                impact_pct=round(impact_pct, 2),
                stocks=stocks,
                reasoning=reasoning
            ))
        
        # Sort by absolute impact
        impacts.sort(key=lambda x: abs(x.impact_pct), reverse=True)
        
        return impacts
    
    def get_upstream_impacts(
        self,
        target_sector: str,
        sentiment_score: float,
        sentiment_label: str
    ) -> List[CrossSectorImpact]:
        """
        Get impacts on a sector from upstream news.
        
        Example: Steel price news → Impact on Auto sector
        """
        target_lower = target_sector.lower()
        impacts = []
        
        if target_lower not in self.REVERSE_IMPACTS:
            return impacts
        
        for source, link in self.REVERSE_IMPACTS[target_lower]:
            if link.direction != ImpactDirection.UPSTREAM:
                continue
            
            # Upstream impact is inverse (cost pressure)
            impact_pct = -sentiment_score * link.correlation * 100
            
            if sentiment_score > 0:
                reasoning = f"Rising {source} costs may pressure {target_sector} margins: {link.description}"
            else:
                reasoning = f"Lower {source} costs may boost {target_sector} margins: {link.description}"
            
            impacts.append(CrossSectorImpact(
                sector=source,
                direction=ImpactDirection.UPSTREAM,
                strength=link.strength,
                impact_pct=round(impact_pct, 2),
                stocks=link.example_stocks,
                reasoning=reasoning
            ))
        
        return impacts
    
    def analyze_full_chain(
        self,
        sector: str,
        sentiment_score: float,
        sentiment_label: str
    ) -> Dict[str, List[CrossSectorImpact]]:
        """
        Analyze full supply chain impact (upstream + downstream + lateral).
        
        Returns dict with keys: "upstream", "downstream", "lateral"
        """
        sector_lower = sector.lower()
        
        result = {
            "upstream": [],
            "downstream": [],
            "lateral": []
        }
        
        if sector_lower not in self.SUPPLY_CHAIN:
            return result
        
        for target, direction, strength, corr, desc, stocks in self.SUPPLY_CHAIN[sector_lower]:
            # Calculate impact
            if direction == ImpactDirection.UPSTREAM:
                impact_pct = -sentiment_score * corr * 100
            else:
                impact_pct = sentiment_score * corr * 100
            
            impact = CrossSectorImpact(
                sector=target,
                direction=direction,
                strength=strength,
                impact_pct=round(impact_pct, 2),
                stocks=stocks,
                reasoning=f"{desc} (correlation: {corr:.0%})"
            )
            
            if direction == ImpactDirection.UPSTREAM:
                result["upstream"].append(impact)
            elif direction == ImpactDirection.DOWNSTREAM:
                result["downstream"].append(impact)
            else:
                result["lateral"].append(impact)
        
        return result
    
    def get_related_stocks(
        self,
        sector: str,
        include_directions: Optional[List[ImpactDirection]] = None
    ) -> Dict[str, List[str]]:
        """
        Get all related stocks from supply chain.
        
        Returns dict: {sector_name: [stock_symbols]}
        """
        sector_lower = sector.lower()
        result = {}
        
        if sector_lower not in self.SUPPLY_CHAIN:
            return result
        
        include = include_directions or [ImpactDirection.UPSTREAM, ImpactDirection.DOWNSTREAM, ImpactDirection.LATERAL]
        
        for target, direction, _, _, _, stocks in self.SUPPLY_CHAIN[sector_lower]:
            if direction in include:
                result[target] = stocks
        
        return result


# Singleton
_analyzer: Optional[SupplyChainAnalyzer] = None


def get_supply_chain_analyzer() -> SupplyChainAnalyzer:
    """Get or create the supply chain analyzer"""
    global _analyzer
    if _analyzer is None:
        _analyzer = SupplyChainAnalyzer()
    return _analyzer
