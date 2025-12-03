"""
Configuration settings for the Financial News Intelligence System
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # LLM Configuration
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    
    # Model Selection (groq is fastest for real-time trading)
    llm_provider: str = "groq"  # groq | openai | anthropic
    groq_model: str = "llama-3.3-70b-versatile"  # Fast inference
    openai_model: str = "gpt-4o-mini"
    anthropic_model: str = "claude-3-haiku-20240307"  # Fast Claude model
    
    # RAG Configuration
    rag_enabled: bool = True
    rag_max_context_docs: int = 5
    rag_temperature: float = 0.3
    
    # LangSmith / LangChain Tracing
    langchain_tracing_v2: Optional[str] = None
    langchain_api_key: Optional[str] = None
    langchain_project: Optional[str] = None
    langsmith_endpoint: Optional[str] = None
    
    # Database Configuration
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "financial_news"
    postgres_user: str = "postgres"
    postgres_password: str = ""
    
    # ChromaDB Configuration
    chroma_persist_dir: str = "./chroma_db"
    
    # Embedding Configuration
    embedding_model: str = "all-mpnet-base-v2"
    
    # Deduplication Configuration
    # Lowered from 0.85 to 0.70 for better duplicate detection
    # Semantic similarity of 0.70+ indicates likely duplicate
    # This catches paraphrased articles (same event, different wording)
    dedup_threshold: float = 0.70
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # Scheduler Configuration
    rss_fetch_interval_minutes: int = 5
    nse_fetch_interval_minutes: int = 15
    
    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def postgres_async_url(self) -> str:
        """Get async PostgreSQL connection URL"""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# RSS Feed Configuration
RSS_FEEDS = {
    "moneycontrol": {
        "news": "https://www.moneycontrol.com/rss/latestnews.xml",
        "markets": "https://www.moneycontrol.com/rss/marketreports.xml",
        "stocks": "https://www.moneycontrol.com/rss/buzzingstocks.xml"
    },
    "economic_times": {
        "markets": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "stocks": "https://economictimes.indiatimes.com/markets/stocks/rssfeeds/2146842.cms",
    },
    "business_standard": {
        "markets": "https://www.business-standard.com/rss/markets-106.rss",
        "companies": "https://www.business-standard.com/rss/companies-101.rss"
    },
    "livemint": {
        "markets": "https://www.livemint.com/rss/markets"
    },
    "financial_express": {
        "market": "https://www.financialexpress.com/market/feed/",
    }
}


# Indian Financial Regulators
REGULATORS = [
    "RBI", "Reserve Bank of India", "Reserve Bank",
    "SEBI", "Securities and Exchange Board",
    "IRDAI", "Insurance Regulatory",
    "PFRDA", "Pension Fund Regulatory",
    "Ministry of Finance", "Finance Ministry",
    "NCLT", "National Company Law Tribunal"
]


# Sector Classification
SECTORS = {
    "Banking": ["bank", "banking", "credit", "loan", "deposit", "npa"],
    "Financial Services": ["nbfc", "mutual fund", "insurance", "fintech"],
    "IT": ["software", "technology", "digital", "cloud", "saas"],
    "Pharma": ["pharma", "drug", "medicine", "healthcare", "hospital"],
    "Auto": ["automobile", "vehicle", "car", "ev", "electric vehicle"],
    "FMCG": ["consumer", "fmcg", "retail", "food", "beverage"],
    "Energy": ["oil", "gas", "power", "energy", "renewable", "solar"],
    "Metals": ["steel", "metal", "mining", "aluminium", "copper"],
    "Telecom": ["telecom", "5g", "spectrum", "mobile", "broadband"],
    "Real Estate": ["real estate", "property", "housing", "realty"],
    "Infrastructure": ["infrastructure", "construction", "roads", "railways"]
}


# Major Indian Companies (NSE Nifty 50 + key others)
COMPANIES = {
    "HDFC Bank": {"ticker_nse": "HDFCBANK", "ticker_bse": "500180", "sector": "Banking"},
    "ICICI Bank": {"ticker_nse": "ICICIBANK", "ticker_bse": "532174", "sector": "Banking"},
    "State Bank of India": {"ticker_nse": "SBIN", "ticker_bse": "500112", "sector": "Banking"},
    "SBI": {"ticker_nse": "SBIN", "ticker_bse": "500112", "sector": "Banking"},
    "Kotak Mahindra Bank": {"ticker_nse": "KOTAKBANK", "ticker_bse": "500247", "sector": "Banking"},
    "Axis Bank": {"ticker_nse": "AXISBANK", "ticker_bse": "532215", "sector": "Banking"},
    "Reliance Industries": {"ticker_nse": "RELIANCE", "ticker_bse": "500325", "sector": "Energy"},
    "Reliance": {"ticker_nse": "RELIANCE", "ticker_bse": "500325", "sector": "Energy"},
    "TCS": {"ticker_nse": "TCS", "ticker_bse": "532540", "sector": "IT"},
    "Tata Consultancy Services": {"ticker_nse": "TCS", "ticker_bse": "532540", "sector": "IT"},
    "Infosys": {"ticker_nse": "INFY", "ticker_bse": "500209", "sector": "IT"},
    "Wipro": {"ticker_nse": "WIPRO", "ticker_bse": "507685", "sector": "IT"},
    "HCL Technologies": {"ticker_nse": "HCLTECH", "ticker_bse": "532281", "sector": "IT"},
    "Bharti Airtel": {"ticker_nse": "BHARTIARTL", "ticker_bse": "532454", "sector": "Telecom"},
    "Airtel": {"ticker_nse": "BHARTIARTL", "ticker_bse": "532454", "sector": "Telecom"},
    "Hindustan Unilever": {"ticker_nse": "HINDUNILVR", "ticker_bse": "500696", "sector": "FMCG"},
    "HUL": {"ticker_nse": "HINDUNILVR", "ticker_bse": "500696", "sector": "FMCG"},
    "ITC": {"ticker_nse": "ITC", "ticker_bse": "500875", "sector": "FMCG"},
    "Bajaj Finance": {"ticker_nse": "BAJFINANCE", "ticker_bse": "500034", "sector": "Financial Services"},
    "Maruti Suzuki": {"ticker_nse": "MARUTI", "ticker_bse": "532500", "sector": "Auto"},
    "Tata Motors": {"ticker_nse": "TATAMOTORS", "ticker_bse": "500570", "sector": "Auto"},
    "Sun Pharma": {"ticker_nse": "SUNPHARMA", "ticker_bse": "524715", "sector": "Pharma"},
    "Dr Reddy's": {"ticker_nse": "DRREDDY", "ticker_bse": "500124", "sector": "Pharma"},
    "Tata Steel": {"ticker_nse": "TATASTEEL", "ticker_bse": "500470", "sector": "Metals"},
    "JSW Steel": {"ticker_nse": "JSWSTEEL", "ticker_bse": "500228", "sector": "Metals"},
    "NTPC": {"ticker_nse": "NTPC", "ticker_bse": "532555", "sector": "Energy"},
    "Power Grid": {"ticker_nse": "POWERGRID", "ticker_bse": "532898", "sector": "Energy"},
    "L&T": {"ticker_nse": "LT", "ticker_bse": "500510", "sector": "Infrastructure"},
    "Larsen & Toubro": {"ticker_nse": "LT", "ticker_bse": "500510", "sector": "Infrastructure"},
    "Asian Paints": {"ticker_nse": "ASIANPAINT", "ticker_bse": "500820", "sector": "FMCG"},
    "Titan": {"ticker_nse": "TITAN", "ticker_bse": "500114", "sector": "FMCG"},
    "Adani Enterprises": {"ticker_nse": "ADANIENT", "ticker_bse": "512599", "sector": "Infrastructure"},
    "Adani Ports": {"ticker_nse": "ADANIPORTS", "ticker_bse": "532921", "sector": "Infrastructure"},
}


# Supply Chain Relationships (for bonus challenge)
SUPPLY_CHAIN = {
    "Steel": ["Auto", "Infrastructure", "Real Estate"],
    "Crude Oil": ["Energy", "Paints", "Aviation", "Chemicals"],
    "Interest Rates": ["Banking", "Financial Services", "Real Estate", "Auto"],
    "Rupee": ["IT", "Pharma", "FMCG"],  # Export-oriented sectors
    "Monsoon": ["FMCG", "Auto"],  # Rural demand driven
}


# Global settings instance
settings = Settings()
