"""
Pricing Intelligence Service.

Clean, simple architecture:
1. Official rates loaded from JSON files (CGHS/PMJAY)
2. Crowdsourced data collected from user bills (stored in DB)
3. Hospital scoring based on collected data

Data Sources:
- data/indian_rates/cghs_rates_2024.json - Official CGHS rates
- data/indian_rates/pmjay_packages_2024.json - Official PMJAY packages
- Database tables - Crowdsourced from user bill uploads
"""

import json
import logging
import re
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Tuple, Dict
from pathlib import Path

from sqlalchemy import func, desc
from sqlalchemy.orm import Session

# Fuzzy matching - use rapidfuzz if available, else difflib
try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    from difflib import SequenceMatcher
    RAPIDFUZZ_AVAILABLE = False
    
    class FuzzFallback:
        @staticmethod
        def WRatio(s1: str, s2: str) -> float:
            """Weighted ratio - best for partial matching."""
            # Simple implementation using SequenceMatcher
            ratio = SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
            # Also check if s1 is contained in s2 or vice versa
            if s1.lower() in s2.lower() or s2.lower() in s1.lower():
                ratio = max(ratio, 0.9)
            return ratio * 100
    
    fuzz = FuzzFallback()

from app.models.pricing import (
    Hospital, Procedure, PricePoint, PriceContribution,
    HospitalType, CityTier, PriceSource
)
from app.schemas.pricing import (
    PriceLookupResponse, PriceRange, BenchmarkPrice, MarketPrice,
    ProcedureSearchResult, HospitalScore,
    PriceContributionCreate, PriceContributionResponse,
    DatabaseStats, HospitalTypeEnum, CityTierEnum
)

logger = logging.getLogger(__name__)

# Path to rate files
DATA_DIR = Path(__file__).parent.parent.parent.parent / "data" / "indian_rates"

# City classifications
METRO_CITIES = {
    "delhi", "new delhi", "mumbai", "bombay", "bangalore", "bengaluru",
    "chennai", "madras", "kolkata", "calcutta", "hyderabad", "pune",
    "ahmedabad", "gurgaon", "gurugram", "noida", "ghaziabad"
}

TIER_1_CITIES = {
    "jaipur", "lucknow", "kanpur", "nagpur", "indore", "bhopal",
    "patna", "ludhiana", "agra", "nashik", "varanasi", "chandigarh",
    "coimbatore", "madurai", "kochi", "visakhapatnam", "bhubaneswar"
}


class PricingService:
    """
    Pricing intelligence service.
    
    Loads official rates from JSON files, combines with crowdsourced DB data.
    """
    
    def __init__(self):
        self._cghs_data: Optional[dict] = None
        self._pmjay_data: Optional[dict] = None
        self._procedure_index: Optional[dict] = None
    
    # ============================================
    # Load Official Rates from JSON
    # ============================================
    
    def _load_cghs_data(self) -> dict:
        """Load CGHS rates from JSON file."""
        if self._cghs_data is None:
            filepath = DATA_DIR / "cghs_rates_2024.json"
            if filepath.exists():
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        self._cghs_data = json.load(f)
                    logger.info(f"Loaded CGHS rates from {filepath}")
                except Exception as e:
                    logger.warning(f"Error loading CGHS data: {e}")
                    self._cghs_data = {}
            else:
                logger.warning(f"CGHS file not found: {filepath}")
                self._cghs_data = {}
        return self._cghs_data
    
    def _load_pmjay_data(self) -> dict:
        """Load PMJAY packages from JSON file."""
        if self._pmjay_data is None:
            filepath = DATA_DIR / "pmjay_packages_2024.json"
            if filepath.exists():
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        self._pmjay_data = json.load(f)
                    logger.info(f"Loaded PMJAY packages from {filepath}")
                except Exception as e:
                    logger.warning(f"Error loading PMJAY data: {e}")
                    self._pmjay_data = {}
            else:
                logger.warning(f"PMJAY file not found: {filepath}")
                self._pmjay_data = {}
        return self._pmjay_data
    
    def _build_procedure_index(self) -> dict:
        """Build searchable index from JSON files."""
        if self._procedure_index is not None:
            return self._procedure_index
        
        index = {}
        cghs = self._load_cghs_data()
        pmjay = self._load_pmjay_data()
        
        # Index CGHS procedures
        for category, subcategories in cghs.items():
            if category == "meta":
                continue
            if isinstance(subcategories, dict):
                for subcat, items in subcategories.items():
                    if isinstance(items, dict):
                        if "rate" in items:
                            # Direct item
                            key = f"cghs_{category}_{subcat}".lower()
                            index[key] = {
                                "name": subcat.replace("_", " ").title(),
                                "description": items.get("description", subcat),
                                "cghs_rate": items.get("rate"),
                                "max_private": items.get("max_private"),
                                "source": "CGHS",
                                "category": category,
                            }
                        else:
                            # Nested items
                            for item_key, item_data in items.items():
                                if isinstance(item_data, dict) and "rate" in item_data:
                                    key = f"cghs_{category}_{subcat}_{item_key}".lower()
                                    index[key] = {
                                        "name": item_key.replace("_", " ").title(),
                                        "description": item_data.get("description", item_key),
                                        "cghs_rate": item_data.get("rate"),
                                        "max_private": item_data.get("max_private"),
                                        "source": "CGHS",
                                        "category": f"{category}/{subcat}",
                                    }
        
        # Index PMJAY packages
        packages = pmjay.get("packages", {})
        for category, procedures in packages.items():
            if isinstance(procedures, dict):
                for proc_key, proc_data in procedures.items():
                    if isinstance(proc_data, dict) and "package_rate" in proc_data:
                        key = f"pmjay_{category}_{proc_key}".lower()
                        # Check if already exists from CGHS
                        existing = None
                        for k, v in index.items():
                            if proc_key.lower() in k:
                                existing = k
                                break
                        
                        if existing:
                            index[existing]["pmjay_rate"] = proc_data.get("package_rate")
                        else:
                            index[key] = {
                                "name": proc_key.replace("_", " ").title(),
                                "description": proc_data.get("description", proc_key),
                                "pmjay_rate": proc_data.get("package_rate"),
                                "source": "PMJAY",
                                "category": category,
                            }
        
        self._procedure_index = index
        logger.info(f"Built procedure index: {len(index)} procedures")
        return index
    
    # ============================================
    # Price Lookup
    # ============================================
    
    def lookup_price(
        self,
        procedure_name: str,
        db: Optional[Session] = None,
        city: Optional[str] = None,
        hospital_name: Optional[str] = None,
        hospital_type: Optional[HospitalType] = None,
    ) -> Optional[PriceLookupResponse]:
        """
        Look up price for a procedure.
        
        1. First searches official rates (CGHS/PMJAY from JSON)
        2. Then adds crowdsourced market data from DB (if available)
        """
        if not procedure_name:
            return None
        
        # Search official rates
        index = self._build_procedure_index()
        matched, confidence, proc_data = self._fuzzy_match(procedure_name, index)
        
        if not matched:
            return None
        
        # Build benchmarks from official sources
        benchmarks = []
        if proc_data.get("cghs_rate"):
            benchmarks.append(BenchmarkPrice(
                source="CGHS",
                rate=proc_data["cghs_rate"],
                description="Central Government Health Scheme rate",
                effective_date="2024-01-01"
            ))
        if proc_data.get("pmjay_rate"):
            benchmarks.append(BenchmarkPrice(
                source="PMJAY",
                rate=proc_data["pmjay_rate"],
                description="Ayushman Bharat package rate",
                effective_date="2024-01-01"
            ))
        
        # Get crowdsourced market data if DB available
        market_prices = []
        data_points = 0
        if db:
            market_prices = self._get_market_prices(db, matched, city, hospital_type)
            data_points = self._count_price_points(db, matched)
        
        # Calculate fair price range
        base_rate = proc_data.get("pmjay_rate") or proc_data.get("cghs_rate") or 0
        max_private = proc_data.get("max_private", base_rate * 3 if base_rate else 0)
        
        fair_price_range = PriceRange(
            low=float(base_rate) if base_rate else 0,
            median=float((base_rate + max_private) / 2) if base_rate else float(max_private / 2),
            high=float(max_private) if max_private else 0,
            currency="INR"
        )
        
        return PriceLookupResponse(
            procedure_name=procedure_name,
            matched_procedure=matched,
            match_confidence=confidence,
            category=proc_data.get("category", "unknown"),
            benchmarks=benchmarks,
            market_prices=market_prices,
            fair_price_range=fair_price_range,
            data_points=data_points,
            last_updated=datetime.now(timezone.utc)
        )
    
    def _fuzzy_match(
        self,
        query: str,
        index: dict,
        threshold: int = 60
    ) -> Tuple[Optional[str], float, Optional[dict]]:
        """Fuzzy match procedure name."""
        if not index:
            return None, 0.0, None
        
        search_items = [
            (key, data.get("description", data.get("name", key)), data)
            for key, data in index.items()
        ]
        descriptions = [item[1] for item in search_items]
        descriptions_lower = [d.lower() for d in descriptions]
        
        if RAPIDFUZZ_AVAILABLE:
            result = process.extractOne(
                query.lower(),
                descriptions_lower,
                scorer=fuzz.WRatio,  # WRatio handles partial matches better
                score_cutoff=threshold,
            )
            if result:
                matched_desc_lower, score, idx = result
                # Return original case description
                return descriptions[idx], score / 100.0, search_items[idx][2]
        else:
            best_match = None
            best_score = 0
            best_data = None
            query_lower = query.lower()
            
            for idx, (key, desc, data) in enumerate(search_items):
                score = fuzz.WRatio(query_lower, desc.lower())
                if score > best_score and score >= threshold:
                    best_score = score
                    best_match = desc
                    best_data = data
            
            if best_match:
                return best_match, best_score / 100.0, best_data
        
        return None, 0.0, None
    
    def _get_market_prices(
        self,
        db: Session,
        procedure_name: str,
        city: Optional[str] = None,
        hospital_type: Optional[HospitalType] = None
    ) -> List[MarketPrice]:
        """Get crowdsourced market prices from DB."""
        # Find procedure in DB
        normalized = self._normalize_name(procedure_name)
        proc = db.query(Procedure).filter(
            Procedure.normalized_name == normalized
        ).first()
        
        if not proc:
            return []
        
        # Query price points
        query = db.query(
            PricePoint.hospital_type,
            PricePoint.city_tier,
            func.avg(PricePoint.charged_amount).label('avg_price'),
            func.min(PricePoint.charged_amount).label('min_price'),
            func.max(PricePoint.charged_amount).label('max_price'),
            func.count(PricePoint.id).label('count'),
        ).filter(
            PricePoint.procedure_id == proc.id,
            PricePoint.is_outlier == False
        )
        
        if city:
            query = query.filter(func.lower(PricePoint.city) == city.lower())
        if hospital_type:
            query = query.filter(PricePoint.hospital_type == hospital_type)
        
        results = query.group_by(
            PricePoint.hospital_type,
            PricePoint.city_tier
        ).all()
        
        market_prices = []
        for row in results:
            if row.count >= 3:  # Minimum 3 data points for confidence
                market_prices.append(MarketPrice(
                    hospital_type=HospitalTypeEnum(row.hospital_type.value) if row.hospital_type else HospitalTypeEnum.UNKNOWN,
                    city_tier=CityTierEnum(row.city_tier.value) if row.city_tier else CityTierEnum.UNKNOWN,
                    price_range=PriceRange(
                        low=float(row.min_price),
                        median=float(row.avg_price),
                        high=float(row.max_price),
                        currency="INR"
                    ),
                    sample_size=row.count,
                    confidence=min(0.9, 0.5 + (row.count * 0.05)),
                    last_updated=datetime.now(timezone.utc)
                ))
        
        return market_prices
    
    def _count_price_points(self, db: Session, procedure_name: str) -> int:
        """Count crowdsourced price points."""
        normalized = self._normalize_name(procedure_name)
        proc = db.query(Procedure).filter(
            Procedure.normalized_name == normalized
        ).first()
        
        if not proc:
            return 0
        return db.query(PricePoint).filter(PricePoint.procedure_id == proc.id).count()
    
    # ============================================
    # Procedure Search
    # ============================================
    
    def search_procedures(
        self,
        query: str,
        db: Optional[Session] = None,
        limit: int = 20
    ) -> List[ProcedureSearchResult]:
        """Search procedures from official rates."""
        results = []
        index = self._build_procedure_index()
        
        search_items = [
            (key, data.get("description", data.get("name", key)), data)
            for key, data in index.items()
        ]
        descriptions = [item[1] for item in search_items]
        descriptions_lower = [d.lower() for d in descriptions]
        
        if RAPIDFUZZ_AVAILABLE:
            matches = process.extract(
                query.lower(),
                descriptions_lower,
                scorer=fuzz.WRatio,  # WRatio handles partial matches better
                limit=limit,
            )
        else:
            query_lower = query.lower()
            scored = []
            for idx, desc in enumerate(descriptions):
                score = fuzz.WRatio(query_lower, desc.lower())
                scored.append((desc, score, idx))
            scored.sort(key=lambda x: x[1], reverse=True)
            matches = scored[:limit]
        
        for desc_lower, score, idx in matches:
            if score < 40:
                continue
            key, desc_original, data = search_items[idx]
            
            # Check DB for additional data
            price_point_count = 0
            market_median = None
            proc_id = 0
            
            if db:
                normalized = self._normalize_name(desc_original)
                db_proc = db.query(Procedure).filter(
                    Procedure.normalized_name == normalized
                ).first()
                if db_proc:
                    proc_id = db_proc.id
                    price_point_count = db_proc.price_point_count or 0
                    market_median = db_proc.market_median
            
            results.append(ProcedureSearchResult(
                id=proc_id,
                name=desc_original,  # Use original case
                category=data.get("category", "unknown"),
                cghs_rate=data.get("cghs_rate"),
                pmjay_rate=data.get("pmjay_rate"),
                market_median=market_median,
                price_point_count=price_point_count,
                match_score=score / 100.0
            ))
        
        return results
    
    # ============================================
    # Hospital Scoring
    # ============================================
    
    def calculate_hospital_score(
        self,
        db: Session,
        hospital_id: int
    ) -> Optional[HospitalScore]:
        """Calculate hospital score from crowdsourced data."""
        hospital = db.query(Hospital).filter(Hospital.id == hospital_id).first()
        if not hospital:
            return None
        
        # Get price points for this hospital
        price_points = db.query(PricePoint).filter(
            PricePoint.hospital_id == hospital_id,
            PricePoint.is_outlier == False
        ).all()
        
        if len(price_points) < 3:
            return HospitalScore(
                pricing_score=50.0,
                transparency_score=50.0,
                overall_score=50.0
            )
        
        # Calculate pricing score (how close to CGHS)
        overcharge_percentages = [
            pp.cghs_comparison for pp in price_points 
            if pp.cghs_comparison is not None
        ]
        
        if overcharge_percentages:
            avg_overcharge = sum(overcharge_percentages) / len(overcharge_percentages)
            pricing_score = max(0, min(100, 100 - (avg_overcharge / 3)))
        else:
            pricing_score = 50.0
        
        # Calculate transparency score (consistency)
        proc_prices: Dict[int, List[float]] = {}
        for pp in price_points:
            if pp.procedure_id not in proc_prices:
                proc_prices[pp.procedure_id] = []
            proc_prices[pp.procedure_id].append(pp.charged_amount)
        
        variances = []
        for prices in proc_prices.values():
            if len(prices) >= 2:
                mean = sum(prices) / len(prices)
                if mean > 0:
                    variance = sum((p - mean) ** 2 for p in prices) / len(prices)
                    cv = (variance ** 0.5) / mean
                    variances.append(cv)
        
        if variances:
            avg_cv = sum(variances) / len(variances)
            transparency_score = max(0, min(100, 100 - (avg_cv * 200)))
        else:
            transparency_score = 50.0
        
        overall_score = (pricing_score * 0.6) + (transparency_score * 0.4)
        
        return HospitalScore(
            pricing_score=round(pricing_score, 1),
            transparency_score=round(transparency_score, 1),
            overall_score=round(overall_score, 1)
        )
    
    # ============================================
    # Price Contributions (Crowdsourcing)
    # ============================================
    
    def add_price_contribution(
        self,
        db: Session,
        contribution: PriceContributionCreate,
        user_id: Optional[int] = None
    ) -> PriceContributionResponse:
        """Add a price contribution from user bill."""
        # Find or create procedure
        proc = self._find_or_create_procedure(db, contribution.procedure_name)
        
        # Find or create hospital
        hospital = None
        if contribution.hospital_name and contribution.city:
            hospital = self._find_or_create_hospital(
                db,
                contribution.hospital_name,
                contribution.city,
                contribution.state,
                contribution.hospital_type
            )
        
        # Calculate comparisons vs official rates
        cghs_comparison = None
        pmjay_comparison = None
        
        if proc.cghs_rate:
            cghs_comparison = ((contribution.charged_amount - proc.cghs_rate) / proc.cghs_rate) * 100
        if proc.pmjay_package_rate:
            pmjay_comparison = ((contribution.charged_amount - proc.pmjay_package_rate) / proc.pmjay_package_rate) * 100
        
        # Create price point
        city_tier = self._detect_city_tier(contribution.city) if contribution.city else CityTier.UNKNOWN
        
        price_point = PricePoint(
            procedure_id=proc.id,
            hospital_id=hospital.id if hospital else None,
            charged_amount=contribution.charged_amount,
            currency="INR",
            city=contribution.city,
            state=contribution.state,
            hospital_type=HospitalType(contribution.hospital_type.value) if contribution.hospital_type else None,
            city_tier=city_tier,
            source=PriceSource.USER_BILL,
            source_document_id=contribution.source_document_id,
            contributing_user_id=user_id,
            observation_date=contribution.observation_date or datetime.now(timezone.utc),
            confidence=0.7 if contribution.is_verified else 0.5,
            is_verified=contribution.is_verified,
            cghs_comparison=cghs_comparison,
            pmjay_comparison=pmjay_comparison,
        )
        
        db.add(price_point)
        
        # Update counts
        proc.price_point_count = (proc.price_point_count or 0) + 1
        proc.last_price_update = datetime.now(timezone.utc)
        
        if hospital:
            hospital.total_bills_analyzed = (hospital.total_bills_analyzed or 0) + 1
            hospital.total_procedures_priced = (hospital.total_procedures_priced or 0) + 1
        
        db.commit()
        
        # Build response
        comparison = {}
        if cghs_comparison is not None:
            comparison["vs_cghs"] = f"{cghs_comparison:+.1f}%"
        if pmjay_comparison is not None:
            comparison["vs_pmjay"] = f"{pmjay_comparison:+.1f}%"
        
        return PriceContributionResponse(
            success=True,
            price_point_id=price_point.id,
            procedure_matched=proc.name,
            hospital_matched=hospital.name if hospital else None,
            comparison=comparison if comparison else None,
            points_earned=10,
            message="Thank you for contributing pricing data!"
        )
    
    def _find_or_create_procedure(self, db: Session, procedure_name: str) -> Procedure:
        """Find or create procedure in DB."""
        # First try to fuzzy match against official rates to get a clean name
        index = self._build_procedure_index()
        matched, confidence, data = self._fuzzy_match(procedure_name, index)
        
        # Use matched name if high confidence, otherwise use original
        clean_name = matched if matched and confidence >= 60 else procedure_name
        normalized = self._normalize_name(clean_name)
        
        # Check if we already have this procedure
        proc = db.query(Procedure).filter(
            Procedure.normalized_name == normalized
        ).first()
        
        if proc:
            return proc
        
        # Create new procedure with clean names
        proc = Procedure(
            name=clean_name,
            normalized_name=normalized,
            description=data.get("description") if data else procedure_name,
            category=data.get("category", "unknown") if data else "unknown",
            cghs_rate=data.get("cghs_rate") if data else None,
            cghs_max_private=data.get("max_private") if data else None,
            pmjay_package_rate=data.get("pmjay_rate") if data else None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        db.add(proc)
        db.flush()
        return proc
    
    def _find_or_create_hospital(
        self,
        db: Session,
        hospital_name: str,
        city: str,
        state: Optional[str] = None,
        hospital_type: Optional[HospitalTypeEnum] = None
    ) -> Hospital:
        """Find or create hospital in DB."""
        normalized = self._normalize_name(hospital_name)
        
        hospital = db.query(Hospital).filter(
            Hospital.normalized_name == normalized,
            func.lower(Hospital.city) == city.lower()
        ).first()
        
        if hospital:
            return hospital
        
        city_tier = self._detect_city_tier(city)
        
        hospital = Hospital(
            name=hospital_name,
            normalized_name=normalized,
            city=city,
            state=state or "Unknown",
            hospital_type=HospitalType(hospital_type.value) if hospital_type else HospitalType.PRIVATE,
            city_tier=city_tier,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        db.add(hospital)
        db.flush()
        return hospital
    
    def _normalize_name(self, name: str) -> str:
        """Normalize name for matching."""
        normalized = re.sub(r'[^\w\s]', '', name.lower())
        return ' '.join(normalized.split())
    
    def _detect_city_tier(self, city: str) -> CityTier:
        """Detect city tier."""
        if not city:
            return CityTier.UNKNOWN
        city_lower = city.lower().strip()
        if city_lower in METRO_CITIES:
            return CityTier.METRO
        if city_lower in TIER_1_CITIES:
            return CityTier.TIER_1
        return CityTier.TIER_2
    
    # ============================================
    # Process Bill for Pricing Data
    # ============================================
    
    def process_bill_for_pricing(
        self,
        db: Session,
        document_id: int,
        user_id: int,
        extracted_data: dict
    ) -> int:
        """
        Extract pricing data from analyzed bill.
        Called after bill OCR/analysis to populate crowdsourced DB.
        """
        hospital_name = extracted_data.get("hospital", {}).get("name")
        city = extracted_data.get("hospital", {}).get("city")
        state = extracted_data.get("hospital", {}).get("state")
        
        line_items = extracted_data.get("line_items", [])
        added = 0
        
        for item in line_items:
            if not item.get("description") or not item.get("amount"):
                continue
            
            try:
                contribution = PriceContributionCreate(
                    procedure_name=item["description"],
                    charged_amount=float(item["amount"]),
                    hospital_name=hospital_name,
                    city=city,
                    state=state,
                    source_document_id=document_id,
                    observation_date=datetime.now(timezone.utc)
                )
                
                self.add_price_contribution(db, contribution, user_id)
                added += 1
            except Exception as e:
                logger.warning(f"Failed to add price point: {e}")
        
        return added
    
    # ============================================
    # Database Stats
    # ============================================
    
    def get_database_stats(self, db: Optional[Session]) -> DatabaseStats:
        """Get pricing database statistics."""
        # Count from JSON files (always available)
        index = self._build_procedure_index()
        cghs_count = sum(1 for v in index.values() if v.get("cghs_rate"))
        pmjay_count = sum(1 for v in index.values() if v.get("pmjay_rate"))
        
        # Default values for when DB not available
        total_price_points = 0
        total_hospitals = 0
        total_procedures = 0
        cities = 0
        states = 0
        latest = None
        last_7 = 0
        last_30 = 0
        verified_pct = 0.0
        
        # Count from DB if available
        if db:
            total_price_points = db.query(PricePoint).count()
            total_hospitals = db.query(Hospital).count()
            total_procedures = db.query(Procedure).count()
            
            cities = db.query(func.distinct(PricePoint.city)).filter(
                PricePoint.city.isnot(None)
            ).count()
            states = db.query(func.distinct(PricePoint.state)).filter(
                PricePoint.state.isnot(None)
            ).count()
            
            latest = db.query(func.max(PricePoint.created_at)).scalar()
            
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            month_ago = datetime.now(timezone.utc) - timedelta(days=30)
            
            last_7 = db.query(PricePoint).filter(PricePoint.created_at >= week_ago).count()
            last_30 = db.query(PricePoint).filter(PricePoint.created_at >= month_ago).count()
            
            verified = db.query(PricePoint).filter(PricePoint.is_verified == True).count()
            verified_pct = (verified / total_price_points * 100) if total_price_points > 0 else 0
        
        return DatabaseStats(
            total_price_points=total_price_points,
            total_hospitals=total_hospitals,
            total_procedures=total_procedures,
            cghs_procedures=cghs_count,
            pmjay_packages=pmjay_count,
            crowdsourced_points=total_price_points,
            cities_covered=cities,
            states_covered=states,
            latest_contribution=latest,
            contributions_last_7_days=last_7,
            contributions_last_30_days=last_30,
            verified_percentage=round(verified_pct, 1)
        )


# Singleton instance
pricing_service = PricingService()
