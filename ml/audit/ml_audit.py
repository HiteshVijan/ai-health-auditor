"""
Machine Learning-based audit module for medical bill anomaly detection.

Uses trained classifiers to predict anomaly scores for parsed bills,
complementing rule-based auditing with pattern-based detection.
"""

import logging
import pickle
import json
from pathlib import Path
from typing import Optional, TypedDict
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger(__name__)

# Try to import ML libraries
try:
    import lightgbm as lgb
    HAS_LIGHTGBM = True
except ImportError:
    HAS_LIGHTGBM = False
    logger.warning("LightGBM not available, falling back to RandomForest")

from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score,
    precision_score,
    recall_score,
    f1_score,
)


class AnomalyPrediction(TypedDict):
    """Type definition for anomaly prediction result."""

    document_id: int
    anomaly_score: float
    is_anomaly: bool
    confidence: float
    risk_factors: list[str]


class TrainingMetrics(TypedDict):
    """Type definition for training metrics."""

    accuracy: float
    precision: float
    recall: float
    f1_score: float
    auc_roc: float
    samples_trained: int


@dataclass
class ModelConfig:
    """Configuration for ML model training."""

    model_type: str = "lightgbm"  # "lightgbm" or "random_forest"
    n_estimators: int = 100
    max_depth: int = 10
    learning_rate: float = 0.1
    random_state: int = 42
    anomaly_threshold: float = 0.5
    
    # Feature engineering settings
    use_isolation_forest: bool = True
    isolation_contamination: float = 0.1


class BillFeatureExtractor:
    """
    Extracts numerical features from parsed bill data.
    
    Transforms raw bill JSON into feature vectors suitable
    for ML model input.
    """
    
    # Feature names for interpretability
    FEATURE_NAMES = [
        "total_amount",
        "subtotal",
        "tax_amount",
        "tax_rate",
        "discount",
        "insurance_paid",
        "num_line_items",
        "avg_item_price",
        "max_item_price",
        "min_item_price",
        "price_std",
        "total_quantity",
        "avg_quantity",
        "has_duplicates",
        "arithmetic_diff",
        "price_to_subtotal_ratio",
        "tax_to_subtotal_ratio",
        "discount_ratio",
        "insurance_coverage_ratio",
    ]
    
    def __init__(self):
        """Initialize the feature extractor."""
        self.scaler = StandardScaler()
        self._fitted = False
    
    def extract_features(self, bill: dict) -> np.ndarray:
        """
        Extract feature vector from a parsed bill.
        
        Args:
            bill: Parsed bill dictionary.
            
        Returns:
            np.ndarray: Feature vector of shape (n_features,).
        """
        features = []
        
        # Amount features
        total = self._safe_float(bill.get("total_amount"), 0)
        subtotal = self._safe_float(bill.get("subtotal"), total)
        tax = self._safe_float(bill.get("tax_amount"), 0)
        tax_rate = self._safe_float(bill.get("tax_rate"), 0)
        discount = self._safe_float(bill.get("discount"), 0)
        insurance = self._safe_float(bill.get("insurance_paid"), 0)
        
        features.extend([total, subtotal, tax, tax_rate, discount, insurance])
        
        # Line item features
        line_items = bill.get("line_items", [])
        num_items = len(line_items)
        
        if num_items > 0:
            prices = [self._safe_float(item.get("total"), 0) for item in line_items]
            quantities = [self._safe_float(item.get("quantity"), 1) for item in line_items]
            
            avg_price = np.mean(prices)
            max_price = np.max(prices)
            min_price = np.min(prices)
            price_std = np.std(prices) if len(prices) > 1 else 0
            total_qty = sum(quantities)
            avg_qty = np.mean(quantities)
        else:
            avg_price = max_price = min_price = price_std = 0
            total_qty = avg_qty = 0
        
        features.extend([
            num_items,
            avg_price,
            max_price,
            min_price,
            price_std,
            total_qty,
            avg_qty,
        ])
        
        # Derived features
        has_duplicates = self._check_duplicates(line_items)
        arithmetic_diff = self._calc_arithmetic_diff(line_items, subtotal)
        
        # Ratios (with safe division)
        price_ratio = max_price / subtotal if subtotal > 0 else 0
        tax_ratio = tax / subtotal if subtotal > 0 else 0
        discount_ratio = discount / subtotal if subtotal > 0 else 0
        insurance_ratio = insurance / total if total > 0 else 0
        
        features.extend([
            float(has_duplicates),
            arithmetic_diff,
            price_ratio,
            tax_ratio,
            discount_ratio,
            insurance_ratio,
        ])
        
        return np.array(features, dtype=np.float32)
    
    def extract_batch(self, bills: list[dict]) -> np.ndarray:
        """
        Extract features from multiple bills.
        
        Args:
            bills: List of parsed bill dictionaries.
            
        Returns:
            np.ndarray: Feature matrix of shape (n_bills, n_features).
        """
        return np.array([self.extract_features(bill) for bill in bills])
    
    def fit_transform(self, features: np.ndarray) -> np.ndarray:
        """
        Fit scaler and transform features.
        
        Args:
            features: Raw feature matrix.
            
        Returns:
            np.ndarray: Scaled feature matrix.
        """
        self._fitted = True
        return self.scaler.fit_transform(features)
    
    def transform(self, features: np.ndarray) -> np.ndarray:
        """
        Transform features using fitted scaler.
        
        Args:
            features: Raw feature matrix.
            
        Returns:
            np.ndarray: Scaled feature matrix.
        """
        if not self._fitted:
            logger.warning("Scaler not fitted, returning raw features")
            return features
        return self.scaler.transform(features)
    
    def _safe_float(self, value, default: float = 0) -> float:
        """Safely convert value to float."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def _check_duplicates(self, line_items: list) -> bool:
        """Check for duplicate line items."""
        if not line_items:
            return False
        
        seen = set()
        for item in line_items:
            key = (
                item.get("code", ""),
                item.get("description", "").lower().strip(),
            )
            if key in seen:
                return True
            seen.add(key)
        return False
    
    def _calc_arithmetic_diff(self, line_items: list, subtotal: float) -> float:
        """Calculate difference between line item sum and subtotal."""
        if not line_items:
            return 0
        
        item_sum = sum(
            self._safe_float(item.get("total"), 0)
            for item in line_items
        )
        return abs(item_sum - subtotal)


class MLAuditModel:
    """
    Machine learning model for bill anomaly detection.
    
    Combines supervised classification with unsupervised anomaly
    detection for robust predictions.
    """
    
    def __init__(self, config: Optional[ModelConfig] = None):
        """
        Initialize the ML audit model.
        
        Args:
            config: Model configuration. Uses defaults if None.
        """
        self.config = config or ModelConfig()
        self.feature_extractor = BillFeatureExtractor()
        self.classifier = None
        self.isolation_forest = None
        self._trained = False
        
        self._initialize_models()
    
    def _initialize_models(self) -> None:
        """Initialize ML models based on config."""
        if self.config.model_type == "lightgbm" and HAS_LIGHTGBM:
            self.classifier = lgb.LGBMClassifier(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                learning_rate=self.config.learning_rate,
                random_state=self.config.random_state,
                verbose=-1,
            )
        else:
            self.classifier = RandomForestClassifier(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                random_state=self.config.random_state,
                n_jobs=-1,
            )
        
        if self.config.use_isolation_forest:
            self.isolation_forest = IsolationForest(
                contamination=self.config.isolation_contamination,
                random_state=self.config.random_state,
                n_jobs=-1,
            )
    
    def train(
        self,
        bills: list[dict],
        labels: list[int],
        validation_split: float = 0.2,
    ) -> TrainingMetrics:
        """
        Train the model on labeled bill data.
        
        Args:
            bills: List of parsed bill dictionaries.
            labels: Binary labels (1 = anomaly, 0 = normal).
            validation_split: Fraction of data for validation.
            
        Returns:
            TrainingMetrics: Training and validation metrics.
        """
        logger.info(f"Training ML audit model on {len(bills)} samples")
        
        # Extract and scale features
        X = self.feature_extractor.extract_batch(bills)
        X_scaled = self.feature_extractor.fit_transform(X)
        y = np.array(labels)
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X_scaled, y,
            test_size=validation_split,
            random_state=self.config.random_state,
            stratify=y,
        )
        
        # Train classifier
        self.classifier.fit(X_train, y_train)
        
        # Train isolation forest on all data (unsupervised)
        if self.isolation_forest:
            self.isolation_forest.fit(X_scaled)
        
        self._trained = True
        
        # Evaluate
        y_pred = self.classifier.predict(X_val)
        y_prob = self.classifier.predict_proba(X_val)[:, 1]
        
        metrics = TrainingMetrics(
            accuracy=float(np.mean(y_pred == y_val)),
            precision=float(precision_score(y_val, y_pred, zero_division=0)),
            recall=float(recall_score(y_val, y_pred, zero_division=0)),
            f1_score=float(f1_score(y_val, y_pred, zero_division=0)),
            auc_roc=float(roc_auc_score(y_val, y_prob)),
            samples_trained=len(X_train),
        )
        
        logger.info(
            f"Training complete: AUC={metrics['auc_roc']:.3f}, "
            f"F1={metrics['f1_score']:.3f}"
        )
        
        return metrics
    
    def predict(self, bill: dict) -> AnomalyPrediction:
        """
        Predict anomaly score for a single bill.
        
        Args:
            bill: Parsed bill dictionary.
            
        Returns:
            AnomalyPrediction: Prediction with score and risk factors.
        """
        if not self._trained:
            logger.warning("Model not trained, using default predictions")
            return self._default_prediction(bill)
        
        # Extract features
        features = self.feature_extractor.extract_features(bill)
        features_scaled = self.feature_extractor.transform(
            features.reshape(1, -1)
        )
        
        # Get classifier probability
        proba = self.classifier.predict_proba(features_scaled)[0]
        anomaly_prob = proba[1] if len(proba) > 1 else proba[0]
        
        # Combine with isolation forest if available
        if self.isolation_forest:
            iso_score = -self.isolation_forest.score_samples(features_scaled)[0]
            # Normalize to [0, 1] range (roughly)
            iso_score = min(max((iso_score + 0.5), 0), 1)
            # Average the two scores
            anomaly_score = (anomaly_prob + iso_score) / 2
        else:
            anomaly_score = anomaly_prob
        
        # Determine risk factors
        risk_factors = self._identify_risk_factors(bill, features)
        
        return AnomalyPrediction(
            document_id=bill.get("document_id", 0),
            anomaly_score=round(float(anomaly_score), 4),
            is_anomaly=anomaly_score >= self.config.anomaly_threshold,
            confidence=round(float(abs(anomaly_score - 0.5) * 2), 4),
            risk_factors=risk_factors,
        )
    
    def predict_batch(self, bills: list[dict]) -> list[AnomalyPrediction]:
        """
        Predict anomaly scores for multiple bills.
        
        Args:
            bills: List of parsed bill dictionaries.
            
        Returns:
            list[AnomalyPrediction]: Predictions for each bill.
        """
        return [self.predict(bill) for bill in bills]
    
    def _identify_risk_factors(
        self,
        bill: dict,
        features: np.ndarray,
    ) -> list[str]:
        """
        Identify specific risk factors contributing to anomaly score.
        
        Args:
            bill: Original bill data.
            features: Extracted feature vector.
            
        Returns:
            list[str]: List of identified risk factors.
        """
        risk_factors = []
        
        # Check feature values against thresholds
        feature_names = self.feature_extractor.FEATURE_NAMES
        
        # High total amount
        if features[0] > 5000:
            risk_factors.append("high_total_amount")
        
        # Arithmetic difference
        if features[14] > 1:  # arithmetic_diff
            risk_factors.append("arithmetic_mismatch")
        
        # Has duplicates
        if features[13] > 0.5:  # has_duplicates
            risk_factors.append("duplicate_charges")
        
        # High price variance
        if features[10] > features[7] * 0.5:  # price_std > avg_price * 0.5
            risk_factors.append("high_price_variance")
        
        # Unusual tax ratio
        if features[16] > 0.15:  # tax_ratio > 15%
            risk_factors.append("unusual_tax_rate")
        
        # Low insurance coverage
        total = features[0]
        insurance = features[5]
        if total > 1000 and insurance / total < 0.5 if total > 0 else False:
            risk_factors.append("low_insurance_coverage")
        
        return risk_factors
    
    def _default_prediction(self, bill: dict) -> AnomalyPrediction:
        """Return default prediction for untrained model."""
        return AnomalyPrediction(
            document_id=bill.get("document_id", 0),
            anomaly_score=0.5,
            is_anomaly=False,
            confidence=0.0,
            risk_factors=["model_not_trained"],
        )
    
    def save(self, path: str) -> None:
        """
        Save model to disk.
        
        Args:
            path: Path to save model file.
        """
        model_data = {
            "config": self.config,
            "classifier": self.classifier,
            "isolation_forest": self.isolation_forest,
            "feature_extractor": self.feature_extractor,
            "trained": self._trained,
        }
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(model_data, f)
        
        logger.info(f"Model saved to {path}")
    
    @classmethod
    def load(cls, path: str) -> "MLAuditModel":
        """
        Load model from disk.
        
        Args:
            path: Path to model file.
            
        Returns:
            MLAuditModel: Loaded model instance.
        """
        with open(path, "rb") as f:
            model_data = pickle.load(f)
        
        model = cls(config=model_data["config"])
        model.classifier = model_data["classifier"]
        model.isolation_forest = model_data["isolation_forest"]
        model.feature_extractor = model_data["feature_extractor"]
        model._trained = model_data["trained"]
        
        logger.info(f"Model loaded from {path}")
        return model


# =============================================================================
# Synthetic Data Generation (for initial training)
# =============================================================================

def generate_synthetic_bill(
    is_anomaly: bool = False,
    random_state: Optional[int] = None,
) -> dict:
    """
    Generate a synthetic medical bill for training.
    
    Args:
        is_anomaly: Whether to generate an anomalous bill.
        random_state: Random seed for reproducibility.
        
    Returns:
        dict: Synthetic parsed bill.
    """
    rng = np.random.RandomState(random_state)
    
    # Base parameters
    num_items = rng.randint(1, 8)
    
    # Generate line items
    line_items = []
    codes = ["99213", "99214", "85025", "80053", "71046", "81001"]
    descriptions = [
        "Office Visit",
        "Extended Visit",
        "CBC",
        "Metabolic Panel",
        "Chest X-Ray",
        "Urinalysis",
    ]
    
    for i in range(num_items):
        code_idx = rng.randint(0, len(codes))
        base_price = rng.uniform(50, 300)
        quantity = rng.randint(1, 3)
        
        if is_anomaly and rng.random() < 0.3:
            # Introduce overcharge
            base_price *= rng.uniform(1.5, 3.0)
        
        item_total = base_price * quantity
        
        if is_anomaly and rng.random() < 0.2:
            # Introduce arithmetic error
            item_total *= rng.uniform(0.8, 1.2)
        
        line_items.append({
            "code": codes[code_idx % len(codes)],
            "description": descriptions[code_idx % len(descriptions)],
            "quantity": quantity,
            "unit_price": round(base_price, 2),
            "total": round(item_total, 2),
        })
    
    # Add duplicate if anomaly
    if is_anomaly and rng.random() < 0.25 and line_items:
        duplicate = line_items[0].copy()
        line_items.append(duplicate)
    
    # Calculate totals
    subtotal = sum(item["total"] for item in line_items)
    
    tax_rate = rng.uniform(0, 0.08)
    if is_anomaly and rng.random() < 0.2:
        tax_rate = rng.uniform(0.15, 0.25)  # Unusual tax
    
    tax_amount = subtotal * tax_rate
    discount = subtotal * rng.uniform(0, 0.1) if rng.random() < 0.3 else 0
    insurance = subtotal * rng.uniform(0.5, 0.9) if rng.random() < 0.7 else 0
    
    total = subtotal + tax_amount - discount - insurance
    
    if is_anomaly and rng.random() < 0.2:
        # Introduce total mismatch
        total *= rng.uniform(0.9, 1.1)
    
    bill = {
        "document_id": rng.randint(1, 100000),
        "total_amount": round(max(total, 0), 2),
        "subtotal": round(subtotal, 2),
        "tax_amount": round(tax_amount, 2),
        "tax_rate": round(tax_rate, 4),
        "discount": round(discount, 2),
        "insurance_paid": round(insurance, 2),
        "patient_responsibility": round(max(total, 0), 2),
        "line_items": line_items,
        "invoice_number": f"INV-{rng.randint(10000, 99999)}",
        "patient_name": "Synthetic Patient",
        "bill_date": "2024-01-15",
    }
    
    return bill


def generate_synthetic_dataset(
    n_samples: int = 1000,
    anomaly_ratio: float = 0.2,
    random_state: int = 42,
) -> tuple[list[dict], list[int]]:
    """
    Generate a synthetic dataset for model training.
    
    Args:
        n_samples: Total number of samples to generate.
        anomaly_ratio: Fraction of samples that are anomalies.
        random_state: Random seed for reproducibility.
        
    Returns:
        tuple: (bills, labels) where labels are 1 for anomaly, 0 for normal.
    """
    rng = np.random.RandomState(random_state)
    
    n_anomalies = int(n_samples * anomaly_ratio)
    n_normal = n_samples - n_anomalies
    
    bills = []
    labels = []
    
    # Generate normal bills
    for i in range(n_normal):
        bills.append(generate_synthetic_bill(
            is_anomaly=False,
            random_state=rng.randint(0, 1000000),
        ))
        labels.append(0)
    
    # Generate anomalous bills
    for i in range(n_anomalies):
        bills.append(generate_synthetic_bill(
            is_anomaly=True,
            random_state=rng.randint(0, 1000000),
        ))
        labels.append(1)
    
    # Shuffle
    indices = rng.permutation(n_samples)
    bills = [bills[i] for i in indices]
    labels = [labels[i] for i in indices]
    
    logger.info(
        f"Generated {n_samples} synthetic bills "
        f"({n_anomalies} anomalies, {n_normal} normal)"
    )
    
    return bills, labels


# =============================================================================
# Placeholder for Production Retraining
# =============================================================================

class RetrainingPipeline:
    """
    Placeholder for production model retraining.
    
    TODO: Implement with real data sources when available:
    - Connect to production database
    - Fetch labeled bills from review tasks
    - Implement incremental training
    - Add model versioning
    - Implement A/B testing
    """
    
    def __init__(self, model: MLAuditModel):
        """Initialize retraining pipeline."""
        self.model = model
        self.training_history: list[TrainingMetrics] = []
    
    def fetch_training_data(self) -> tuple[list[dict], list[int]]:
        """
        Fetch labeled training data from production.
        
        TODO: Implement database connection and query:
        - Fetch documents with completed review tasks
        - Use corrected values as ground truth
        - Filter for high-confidence labels
        
        Returns:
            tuple: (bills, labels)
        """
        # Placeholder: return synthetic data
        logger.warning("Using synthetic data - implement production data fetch")
        return generate_synthetic_dataset(n_samples=500)
    
    def retrain(
        self,
        min_samples: int = 100,
        validation_split: float = 0.2,
    ) -> Optional[TrainingMetrics]:
        """
        Retrain model with new data.
        
        TODO: Add production features:
        - Model versioning
        - Rollback capability
        - A/B testing
        - Performance monitoring
        
        Args:
            min_samples: Minimum samples required for retraining.
            validation_split: Validation data fraction.
            
        Returns:
            Optional[TrainingMetrics]: Metrics if trained, None if skipped.
        """
        bills, labels = self.fetch_training_data()
        
        if len(bills) < min_samples:
            logger.warning(
                f"Insufficient data for retraining: {len(bills)} < {min_samples}"
            )
            return None
        
        metrics = self.model.train(bills, labels, validation_split)
        self.training_history.append(metrics)
        
        return metrics
    
    def schedule_retraining(
        self,
        interval_hours: int = 24,
    ) -> None:
        """
        Schedule periodic retraining.
        
        TODO: Implement with Celery beat or similar:
        - Schedule periodic retraining tasks
        - Implement smart triggering (data drift detection)
        - Add alerting for performance degradation
        
        Args:
            interval_hours: Hours between retraining runs.
        """
        # Placeholder
        logger.info(f"Retraining scheduled every {interval_hours} hours")
        raise NotImplementedError("Implement with Celery beat scheduler")


# =============================================================================
# Convenience Functions
# =============================================================================

def create_pretrained_model() -> MLAuditModel:
    """
    Create a model pre-trained on synthetic data.
    
    Useful for initial deployment before real data is available.
    
    Returns:
        MLAuditModel: Pre-trained model instance.
    """
    model = MLAuditModel()
    bills, labels = generate_synthetic_dataset(n_samples=1000)
    model.train(bills, labels)
    return model


def predict_anomaly(bill: dict, model: Optional[MLAuditModel] = None) -> AnomalyPrediction:
    """
    Convenience function to predict anomaly for a single bill.
    
    Args:
        bill: Parsed bill dictionary.
        model: Optional pre-loaded model. Creates new if None.
        
    Returns:
        AnomalyPrediction: Prediction result.
    """
    if model is None:
        model = create_pretrained_model()
    
    return model.predict(bill)

