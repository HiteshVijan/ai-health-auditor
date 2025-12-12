"""
Pricing Intelligence Models.

Models for crowdsourced pricing data, hospital profiles, and price contributions.
This forms the foundation of the "Data Moat" - the more bills processed,
the better the pricing intelligence becomes.
"""

from datetime import datetime, timezone
from typing import Optional
import enum

from sqlalchemy import (
    String, Integer, Float, ForeignKey, Text, Boolean,
    Enum, DateTime, UniqueConstraint, Index, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IDMixin, TimestampMixin


class HospitalType(str, enum.Enum):
    """Types of hospitals in India."""
    GOVERNMENT = "government"
    CGHS_EMPANELED = "cghs_empaneled"
    PRIVATE = "private"
    CORPORATE = "corporate"
    NABH_ACCREDITED = "nabh_accredited"
    TRUST = "trust"
    UNKNOWN = "unknown"


class CityTier(str, enum.Enum):
    """City tiers for pricing adjustment."""
    METRO = "metro"           # Delhi, Mumbai, Bangalore, Chennai, Kolkata, Hyderabad
    TIER_1 = "tier_1"         # State capitals, major cities
    TIER_2 = "tier_2"         # Smaller cities
    TIER_3 = "tier_3"         # Towns
    UNKNOWN = "unknown"


class PriceSource(str, enum.Enum):
    """Source of pricing data."""
    CGHS = "cghs"                   # Government CGHS rates
    PMJAY = "pmjay"                 # Ayushman Bharat rates
    USER_BILL = "user_bill"         # From user-uploaded bills
    HOSPITAL_WEBSITE = "hospital_website"
    INSURANCE_CLAIM = "insurance_claim"
    SURVEY = "survey"
    SCRAPED = "scraped"
    MANUAL = "manual"


class Hospital(Base, IDMixin, TimestampMixin):
    """
    Hospital profile for pricing intelligence.
    
    Aggregates pricing data and calculates hospital scores.
    """
    __tablename__ = "hospitals"
    
    # Basic Info
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    aliases: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array of alternative names
    
    # Location
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Classification
    hospital_type: Mapped[Optional[HospitalType]] = mapped_column(
        Enum(HospitalType),
        default=HospitalType.PRIVATE,
        nullable=True,
        index=True,
    )
    city_tier: Mapped[Optional[CityTier]] = mapped_column(
        Enum(CityTier),
        default=CityTier.TIER_2,
        nullable=True,
        index=True,
    )
    
    # Accreditations
    is_cghs_empaneled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_nabh_accredited: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_pmjay_empaneled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    
    # Aggregated Scores (updated periodically)
    pricing_score: Mapped[float] = mapped_column(Float, default=50.0)  # 0-100, lower = more expensive
    transparency_score: Mapped[float] = mapped_column(Float, default=50.0)  # 0-100
    overall_score: Mapped[float] = mapped_column(Float, default=50.0)  # 0-100
    
    # Statistics
    total_bills_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    total_procedures_priced: Mapped[int] = mapped_column(Integer, default=0)
    avg_overcharge_percent: Mapped[float] = mapped_column(Float, default=0.0)
    
    # Metadata
    gstin: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Verification
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    price_points = relationship("PricePoint", back_populates="hospital")
    
    __table_args__ = (
        UniqueConstraint('normalized_name', 'city', name='uq_hospital_name_city'),
        Index('ix_hospital_location', 'city', 'state'),
        Index('ix_hospital_scores', 'pricing_score', 'overall_score'),
    )
    
    def __repr__(self) -> str:
        return f"<Hospital(id={self.id}, name={self.name}, city={self.city})>"


class Procedure(Base, IDMixin, TimestampMixin):
    """
    Master procedure catalog.
    
    Normalized procedure names with mappings to CGHS/PMJAY codes.
    """
    __tablename__ = "procedures"
    
    # Procedure identification
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Categorization
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)  # e.g., cardiology, orthopedics
    subcategory: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    
    # Code mappings
    cghs_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    pmjay_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    cpt_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # For US market
    icd10_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    
    # Official rates
    cghs_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cghs_max_private: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    pmjay_package_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Aggregated market data (updated periodically)
    market_low: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    market_median: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    market_high: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    market_p25: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 25th percentile
    market_p75: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 75th percentile
    
    # Data quality
    price_point_count: Mapped[int] = mapped_column(Integer, default=0)
    last_price_update: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Aliases for fuzzy matching
    aliases: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array
    
    # Relationships
    price_points = relationship("PricePoint", back_populates="procedure")
    
    __table_args__ = (
        Index('ix_procedure_category', 'category', 'subcategory'),
        Index('ix_procedure_codes', 'cghs_code', 'pmjay_code'),
    )
    
    def __repr__(self) -> str:
        return f"<Procedure(id={self.id}, name={self.name})>"


class PricePoint(Base, IDMixin, TimestampMixin):
    """
    Individual price observation.
    
    Each row represents a single price observation from a bill, claim, or survey.
    This is the core of the crowdsourced pricing database.
    """
    __tablename__ = "price_points"
    
    # Core data
    procedure_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("procedures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hospital_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("hospitals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # Price information
    charged_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR", nullable=False)
    
    # Context
    city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    hospital_type: Mapped[Optional[HospitalType]] = mapped_column(Enum(HospitalType), nullable=True)
    city_tier: Mapped[Optional[CityTier]] = mapped_column(Enum(CityTier), nullable=True)
    
    # Source tracking
    source: Mapped[PriceSource] = mapped_column(
        Enum(PriceSource),
        default=PriceSource.USER_BILL,
        nullable=False,
        index=True,
    )
    source_document_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    contributing_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Date of the bill/observation
    observation_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    
    # Data quality
    confidence: Mapped[float] = mapped_column(Float, default=0.5)  # 0-1
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_outlier: Mapped[bool] = mapped_column(Boolean, default=False)  # Flagged by analysis
    
    # Comparison to benchmarks
    cghs_comparison: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # % vs CGHS
    pmjay_comparison: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # % vs PMJAY
    market_comparison: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # % vs market median
    
    # Relationships
    procedure = relationship("Procedure", back_populates="price_points")
    hospital = relationship("Hospital", back_populates="price_points")
    
    __table_args__ = (
        Index('ix_price_point_procedure_hospital', 'procedure_id', 'hospital_id'),
        Index('ix_price_point_location', 'city', 'state'),
        Index('ix_price_point_source_date', 'source', 'observation_date'),
    )
    
    def __repr__(self) -> str:
        return f"<PricePoint(id={self.id}, amount={self.charged_amount})>"


class HospitalScore(Base, IDMixin, TimestampMixin):
    """
    Historical hospital scoring records.
    
    Tracks hospital scores over time for trend analysis.
    """
    __tablename__ = "hospital_scores"
    
    hospital_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("hospitals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    
    # Scoring period
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Scores
    pricing_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100
    transparency_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100
    consistency_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100
    overall_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100
    
    # Statistics for this period
    bills_analyzed: Mapped[int] = mapped_column(Integer, default=0)
    procedures_priced: Mapped[int] = mapped_column(Integer, default=0)
    avg_overcharge_percent: Mapped[float] = mapped_column(Float, default=0.0)
    overcharge_frequency: Mapped[float] = mapped_column(Float, default=0.0)  # % of bills overcharged
    
    # Score breakdown (JSON)
    score_breakdown: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    
    __table_args__ = (
        Index('ix_hospital_score_period', 'hospital_id', 'period_start', 'period_end'),
    )
    
    def __repr__(self) -> str:
        return f"<HospitalScore(hospital_id={self.hospital_id}, score={self.overall_score})>"


class PriceContribution(Base, IDMixin, TimestampMixin):
    """
    Tracks user contributions to pricing database.
    
    Used for gamification and data quality tracking.
    """
    __tablename__ = "price_contributions"
    
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    
    # Contribution stats
    price_points_added: Mapped[int] = mapped_column(Integer, default=0)
    hospitals_added: Mapped[int] = mapped_column(Integer, default=0)
    procedures_added: Mapped[int] = mapped_column(Integer, default=0)
    
    # Quality metrics
    verified_count: Mapped[int] = mapped_column(Integer, default=0)  # How many were verified
    accuracy_score: Mapped[float] = mapped_column(Float, default=0.5)  # 0-1
    
    # Recognition
    contribution_type: Mapped[str] = mapped_column(String(50), default="bill_upload")
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    
    def __repr__(self) -> str:
        return f"<PriceContribution(user_id={self.user_id}, points={self.price_points_added})>"

