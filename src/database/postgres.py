"""
PostgreSQL Database Models and Connection
"""
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float, 
    Boolean, DateTime, ForeignKey, JSON, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from datetime import datetime
import uuid
from typing import Optional

from src.config import settings


Base = declarative_base()


# ================== Database Models ==================

class Sector(Base):
    """Sector hierarchy table"""
    __tablename__ = "sectors"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True)
    parent_sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    companies = relationship("Company", back_populates="sector")
    parent = relationship("Sector", remote_side=[id])


class Company(Base):
    """Company master data"""
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    ticker_nse = Column(String(20), nullable=True, index=True)
    ticker_bse = Column(String(20), nullable=True)
    sector_id = Column(Integer, ForeignKey("sectors.id"), nullable=True)
    industry = Column(String(100), nullable=True)
    market_cap_category = Column(String(20), nullable=True)  # Large, Mid, Small
    aliases = Column(JSON, nullable=True)  # Alternative names
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    sector = relationship("Sector", back_populates="companies")
    entity_mentions = relationship("ArticleEntity", back_populates="company")
    stock_impacts = relationship("StockImpact", back_populates="company")
    
    # Indexes
    __table_args__ = (
        Index('idx_company_name', 'name'),
    )


class NewsArticle(Base):
    """News articles table"""
    __tablename__ = "news_articles"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    url = Column(String(500), nullable=True)
    source = Column(String(50), nullable=False, index=True)
    feed_type = Column(String(50), nullable=True)
    published_at = Column(DateTime, nullable=True, index=True)
    ingested_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Deduplication
    is_duplicate = Column(Boolean, default=False)
    cluster_id = Column(String(36), nullable=True, index=True)
    similarity_score = Column(Float, nullable=True)
    
    # Sentiment (Bonus)
    sentiment_score = Column(Float, nullable=True)
    sentiment_label = Column(String(20), nullable=True)
    
    # Vector store reference
    embedding_id = Column(String(100), nullable=True)
    
    # Relationships
    entities = relationship("ArticleEntity", back_populates="article", cascade="all, delete-orphan")
    stock_impacts = relationship("StockImpact", back_populates="article", cascade="all, delete-orphan")
    
    # Constraints and indexes
    __table_args__ = (
        UniqueConstraint('url', name='uq_article_url'),
        Index('idx_article_published', 'published_at'),
        Index('idx_article_source', 'source'),
        Index('idx_article_cluster', 'cluster_id'),
    )


class ArticleEntity(Base):
    """Extracted entities from articles"""
    __tablename__ = "article_entities"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(String(36), ForeignKey("news_articles.id", ondelete="CASCADE"), nullable=False)
    entity_type = Column(String(50), nullable=False)  # company, person, regulator, event
    entity_value = Column(String(255), nullable=False)
    normalized_value = Column(String(255), nullable=True)  # Standardized form
    confidence = Column(Float, nullable=True)
    start_pos = Column(Integer, nullable=True)
    end_pos = Column(Integer, nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    
    # Relationships
    article = relationship("NewsArticle", back_populates="entities")
    company = relationship("Company", back_populates="entity_mentions")
    
    # Indexes
    __table_args__ = (
        Index('idx_entity_type_value', 'entity_type', 'entity_value'),
        Index('idx_entity_article', 'article_id'),
    )


class StockImpact(Base):
    """Stock impact mappings"""
    __tablename__ = "stock_impacts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(String(36), ForeignKey("news_articles.id", ondelete="CASCADE"), nullable=False)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    symbol = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    impact_type = Column(String(50), nullable=False)  # direct, sector, regulatory, supply_chain
    reasoning = Column(Text, nullable=True)
    
    # Relationships
    article = relationship("NewsArticle", back_populates="stock_impacts")
    company = relationship("Company", back_populates="stock_impacts")
    
    # Indexes
    __table_args__ = (
        Index('idx_impact_symbol', 'symbol'),
        Index('idx_impact_article', 'article_id'),
    )


class NewsCluster(Base):
    """Clusters of duplicate articles"""
    __tablename__ = "news_clusters"
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    primary_article_id = Column(String(36), ForeignKey("news_articles.id"), nullable=True)
    sources = Column(JSON, nullable=True)  # List of sources
    article_count = Column(Integer, default=1)
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    consolidated_title = Column(Text, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_cluster_first_seen', 'first_seen'),
    )


class AlertSubscription(Base):
    """User alert subscriptions (Bonus feature)"""
    __tablename__ = "alert_subscriptions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(100), nullable=False, index=True)
    subscription_type = Column(String(50), nullable=False)  # company, sector, keyword
    subscription_value = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_subscription_user', 'user_id'),
        Index('idx_subscription_type_value', 'subscription_type', 'subscription_value'),
    )


# ================== Database Connection ==================

class Database:
    """Database connection manager"""
    
    def __init__(self, url: Optional[str] = None):
        self.url = url if url is not None else settings.postgres_url
        self.engine = None
        self.SessionLocal = None
    
    def connect(self):
        """Create database connection"""
        self.engine = create_engine(
            self.url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        return self.engine
    
    def create_tables(self):
        """Create all tables"""
        if not self.engine:
            self.connect()
        Base.metadata.create_all(bind=self.engine)
    
    def drop_tables(self):
        """Drop all tables (use with caution!)"""
        if not self.engine:
            self.connect()
        Base.metadata.drop_all(bind=self.engine)
    
    def get_session(self):
        """Get database session"""
        if not self.SessionLocal:
            self.connect()
        if self.SessionLocal is None:
            raise RuntimeError("Failed to initialize database session")
        return self.SessionLocal()


# Singleton instance
_database: Optional[Database] = None


def get_database() -> Database:
    """Get or create database singleton"""
    global _database
    if _database is None:
        _database = Database()
        _database.connect()
    return _database


def init_database():
    """Initialize database with tables and seed data"""
    db = get_database()
    db.create_tables()
    
    # Seed sectors
    session = db.get_session()
    try:
        from src.config import SECTORS, COMPANIES
        
        # Add sectors
        for sector_name in SECTORS.keys():
            existing = session.query(Sector).filter_by(name=sector_name).first()
            if not existing:
                session.add(Sector(name=sector_name))
        
        session.commit()
        
        # Add companies
        for company_name, info in COMPANIES.items():
            existing = session.query(Company).filter_by(name=company_name).first()
            if not existing:
                sector = session.query(Sector).filter_by(name=info['sector']).first()
                session.add(Company(
                    name=company_name,
                    ticker_nse=info.get('ticker_nse'),
                    ticker_bse=info.get('ticker_bse'),
                    sector_id=sector.id if sector else None
                ))
        
        session.commit()
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()
