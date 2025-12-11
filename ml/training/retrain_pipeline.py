"""
Retraining Pipeline for Document Parsing Models.

This module provides functionality to retrain OCR and field extraction models
using corrected synthetic data and human-in-the-loop (HITL) corrections.

Usage:
    from ml.training.retrain_pipeline import retrain_parser_model
    
    result = retrain_parser_model(
        synthetic_data_path="./data/synthetic/labels.json",
        hitl_data_path="./data/hitl/corrections.json",
        output_dir="./models/field_extractor",
    )
"""

import json
import logging
import os
import pickle
import shutil
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import hashlib

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
)
from sklearn.pipeline import Pipeline
import joblib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TrainingSample:
    """A single training sample for field extraction."""
    text_context: str  # Surrounding text/OCR output
    field_name: str  # Target field (total_amount, patient_name, etc.)
    field_value: str  # Correct field value
    source: str  # 'synthetic', 'hitl', 'production'
    confidence: float  # Original extraction confidence (for HITL data)
    document_id: Optional[str] = None


@dataclass
class ModelMetrics:
    """Metrics from model training/evaluation."""
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    per_class_metrics: Dict[str, Dict[str, float]]
    confusion_matrix: List[List[int]]
    sample_count: int
    training_time_seconds: float


@dataclass
class ModelArtifact:
    """Metadata for a trained model artifact."""
    model_id: str
    model_version: str
    model_type: str
    field_name: str
    created_at: str
    training_samples: int
    synthetic_samples: int
    hitl_samples: int
    metrics: ModelMetrics
    artifact_path: str
    config: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['metrics']['confusion_matrix'] = self.metrics.confusion_matrix
        return data


@dataclass
class RetrainingConfig:
    """Configuration for the retraining pipeline."""
    # Model settings
    model_type: str = "random_forest"  # 'random_forest', 'gradient_boosting', 'logistic_regression'
    n_estimators: int = 100
    max_depth: Optional[int] = None
    min_samples_split: int = 2
    random_state: int = 42
    
    # Training settings
    test_size: float = 0.2
    validation_size: float = 0.1
    min_samples_per_field: int = 10
    
    # Feature extraction
    max_features: int = 5000
    ngram_range: Tuple[int, int] = (1, 2)
    
    # Data augmentation
    augment_synthetic: bool = True
    synthetic_weight: float = 0.5  # Weight for synthetic vs HITL samples
    
    # Output settings
    save_training_data: bool = True
    save_feature_importance: bool = True


class FieldExtractionDataset:
    """
    Dataset manager for field extraction training data.
    
    Handles loading, preprocessing, and augmentation of training data
    from both synthetic and HITL sources.
    """
    
    def __init__(self, config: RetrainingConfig):
        """Initialize the dataset manager."""
        self.config = config
        self.samples: List[TrainingSample] = []
        self.label_encoders: Dict[str, LabelEncoder] = {}
    
    def load_synthetic_data(self, data_path: str) -> int:
        """
        Load training samples from synthetic data.
        
        Args:
            data_path: Path to synthetic data JSON file.
        
        Returns:
            Number of samples loaded.
        """
        if not os.path.exists(data_path):
            logger.warning(f"Synthetic data not found at {data_path}")
            return 0
        
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        count = 0
        for doc in data:
            document_id = doc.get('document_id', str(count))
            
            # Extract fields and their context
            for field_name in ['total_amount', 'invoice_number', 'patient_name', 'bill_date']:
                field_value = doc.get(field_name)
                if field_value:
                    # Create text context from available document text
                    context = self._create_context(doc, field_name)
                    
                    sample = TrainingSample(
                        text_context=context,
                        field_name=field_name,
                        field_value=str(field_value),
                        source='synthetic',
                        confidence=1.0,  # Synthetic data is ground truth
                        document_id=document_id,
                    )
                    self.samples.append(sample)
                    count += 1
        
        logger.info(f"Loaded {count} samples from synthetic data")
        return count
    
    def load_hitl_data(self, data_path: str) -> int:
        """
        Load training samples from HITL corrections.
        
        Args:
            data_path: Path to HITL corrections JSON file.
        
        Returns:
            Number of samples loaded.
        """
        if not os.path.exists(data_path):
            logger.warning(f"HITL data not found at {data_path}")
            return 0
        
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        count = 0
        for correction in data:
            # HITL data format: field_name, extracted_value, correct_value, original_confidence
            field_name = correction.get('field_name')
            correct_value = correction.get('correct_value') or correction.get('corrected_value')
            
            if field_name and correct_value:
                # Use extracted value as context (what OCR saw)
                context = correction.get('extracted_value', '') or ''
                
                sample = TrainingSample(
                    text_context=context,
                    field_name=field_name,
                    field_value=str(correct_value),
                    source='hitl',
                    confidence=correction.get('original_confidence', 0.5),
                    document_id=correction.get('document_id'),
                )
                self.samples.append(sample)
                count += 1
        
        logger.info(f"Loaded {count} samples from HITL corrections")
        return count
    
    def load_from_database(self, db_session) -> int:
        """
        Load training samples directly from database.
        
        Args:
            db_session: SQLAlchemy database session.
        
        Returns:
            Number of samples loaded.
        """
        try:
            from backend.app.services.review_tasks import ReviewTaskService
            
            service = ReviewTaskService(db=db_session)
            training_data = service.get_training_data()
            
            count = 0
            for item in training_data:
                sample = TrainingSample(
                    text_context=item.get('extracted_value', '') or '',
                    field_name=item['field_name'],
                    field_value=item['correct_value'],
                    source='hitl',
                    confidence=item.get('original_confidence', 0.5),
                )
                self.samples.append(sample)
                count += 1
            
            logger.info(f"Loaded {count} samples from database")
            return count
        except Exception as e:
            logger.error(f"Failed to load from database: {e}")
            return 0
    
    def _create_context(self, doc: Dict, field_name: str) -> str:
        """Create text context for a field from document data."""
        # Combine relevant document fields to create context
        context_parts = []
        
        # Add provider info
        if doc.get('provider_name'):
            context_parts.append(f"Provider: {doc['provider_name']}")
        
        # Add patient info
        if doc.get('patient_name'):
            context_parts.append(f"Patient: {doc['patient_name']}")
        
        # Add financial info
        if doc.get('subtotal'):
            context_parts.append(f"Subtotal: {doc['subtotal']}")
        if doc.get('tax'):
            context_parts.append(f"Tax: {doc['tax']}")
        if doc.get('total_amount'):
            context_parts.append(f"Total: {doc['total_amount']}")
        
        # Add date
        if doc.get('bill_date'):
            context_parts.append(f"Date: {doc['bill_date']}")
        
        # Add invoice number
        if doc.get('invoice_number'):
            context_parts.append(f"Invoice: {doc['invoice_number']}")
        
        return " | ".join(context_parts)
    
    def augment_data(self) -> int:
        """
        Augment training data with variations.
        
        Returns:
            Number of augmented samples added.
        """
        if not self.config.augment_synthetic:
            return 0
        
        original_count = len(self.samples)
        augmented_samples = []
        
        for sample in self.samples:
            if sample.source == 'synthetic':
                # Create variations of the text context
                augmented = self._create_augmentations(sample)
                augmented_samples.extend(augmented)
        
        self.samples.extend(augmented_samples)
        added = len(augmented_samples)
        
        logger.info(f"Added {added} augmented samples")
        return added
    
    def _create_augmentations(self, sample: TrainingSample) -> List[TrainingSample]:
        """Create augmented versions of a sample."""
        augmented = []
        
        # Lowercase variation
        augmented.append(TrainingSample(
            text_context=sample.text_context.lower(),
            field_name=sample.field_name,
            field_value=sample.field_value,
            source='synthetic_augmented',
            confidence=sample.confidence,
            document_id=sample.document_id,
        ))
        
        # Uppercase variation
        augmented.append(TrainingSample(
            text_context=sample.text_context.upper(),
            field_name=sample.field_name,
            field_value=sample.field_value,
            source='synthetic_augmented',
            confidence=sample.confidence,
            document_id=sample.document_id,
        ))
        
        # Remove special characters
        clean_context = ''.join(
            c if c.isalnum() or c.isspace() else ' ' 
            for c in sample.text_context
        )
        augmented.append(TrainingSample(
            text_context=clean_context,
            field_name=sample.field_name,
            field_value=sample.field_value,
            source='synthetic_augmented',
            confidence=sample.confidence,
            document_id=sample.document_id,
        ))
        
        return augmented
    
    def get_field_samples(self, field_name: str) -> List[TrainingSample]:
        """Get all samples for a specific field."""
        return [s for s in self.samples if s.field_name == field_name]
    
    def get_unique_fields(self) -> List[str]:
        """Get list of unique field names in the dataset."""
        return list(set(s.field_name for s in self.samples))
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert samples to pandas DataFrame."""
        return pd.DataFrame([
            {
                'text_context': s.text_context,
                'field_name': s.field_name,
                'field_value': s.field_value,
                'source': s.source,
                'confidence': s.confidence,
            }
            for s in self.samples
        ])
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get dataset statistics."""
        df = self.to_dataframe()
        
        return {
            'total_samples': len(self.samples),
            'synthetic_samples': len([s for s in self.samples if 'synthetic' in s.source]),
            'hitl_samples': len([s for s in self.samples if s.source == 'hitl']),
            'unique_fields': self.get_unique_fields(),
            'samples_per_field': df.groupby('field_name').size().to_dict(),
            'avg_context_length': df['text_context'].str.len().mean(),
        }


class FieldExtractionModel:
    """
    ML model for field value extraction from document text.
    
    Uses text classification to identify and extract field values
    from OCR output and document context.
    """
    
    def __init__(self, field_name: str, config: RetrainingConfig):
        """
        Initialize the field extraction model.
        
        Args:
            field_name: Name of the field this model extracts.
            config: Training configuration.
        """
        self.field_name = field_name
        self.config = config
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.classifier: Optional[Any] = None
        self.label_encoder: Optional[LabelEncoder] = None
        self.is_trained = False
        self.feature_names: Optional[List[str]] = None
    
    def _create_classifier(self):
        """Create the classifier based on config."""
        if self.config.model_type == 'random_forest':
            return RandomForestClassifier(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                min_samples_split=self.config.min_samples_split,
                random_state=self.config.random_state,
                n_jobs=-1,
            )
        elif self.config.model_type == 'gradient_boosting':
            return GradientBoostingClassifier(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth or 3,
                random_state=self.config.random_state,
            )
        elif self.config.model_type == 'logistic_regression':
            return LogisticRegression(
                max_iter=1000,
                random_state=self.config.random_state,
                n_jobs=-1,
            )
        else:
            raise ValueError(f"Unknown model type: {self.config.model_type}")
    
    def train(
        self,
        X_train: List[str],
        y_train: List[str],
        X_val: Optional[List[str]] = None,
        y_val: Optional[List[str]] = None,
    ) -> ModelMetrics:
        """
        Train the field extraction model.
        
        Args:
            X_train: Training text contexts.
            y_train: Training field values.
            X_val: Optional validation text contexts.
            y_val: Optional validation field values.
        
        Returns:
            ModelMetrics with training results.
        """
        import time
        start_time = time.time()
        
        logger.info(f"Training model for field '{self.field_name}' with {len(X_train)} samples")
        
        # Initialize vectorizer
        self.vectorizer = TfidfVectorizer(
            max_features=self.config.max_features,
            ngram_range=self.config.ngram_range,
            lowercase=True,
            strip_accents='unicode',
        )
        
        # Initialize label encoder
        self.label_encoder = LabelEncoder()
        
        # Transform text to features
        X_train_vec = self.vectorizer.fit_transform(X_train)
        self.feature_names = self.vectorizer.get_feature_names_out().tolist()
        
        # Encode labels
        y_train_enc = self.label_encoder.fit_transform(y_train)
        
        # Create and train classifier
        self.classifier = self._create_classifier()
        self.classifier.fit(X_train_vec, y_train_enc)
        
        training_time = time.time() - start_time
        
        # Evaluate on validation set if provided
        if X_val is not None and y_val is not None:
            metrics = self.evaluate(X_val, y_val)
            metrics.training_time_seconds = training_time
        else:
            # Evaluate on training set
            y_pred = self.classifier.predict(X_train_vec)
            y_pred_labels = self.label_encoder.inverse_transform(y_pred)
            metrics = self._calculate_metrics(y_train, y_pred_labels, training_time)
        
        self.is_trained = True
        
        logger.info(
            f"Model trained for '{self.field_name}': "
            f"accuracy={metrics.accuracy:.4f}, f1={metrics.f1_score:.4f}"
        )
        
        return metrics
    
    def evaluate(self, X_test: List[str], y_test: List[str]) -> ModelMetrics:
        """
        Evaluate the model on test data.
        
        Args:
            X_test: Test text contexts.
            y_test: Test field values.
        
        Returns:
            ModelMetrics with evaluation results.
        """
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call train() first.")
        
        X_test_vec = self.vectorizer.transform(X_test)
        y_pred_enc = self.classifier.predict(X_test_vec)
        y_pred = self.label_encoder.inverse_transform(y_pred_enc)
        
        return self._calculate_metrics(y_test, y_pred, 0.0)
    
    def predict(self, text_context: str) -> Tuple[str, float]:
        """
        Predict field value from text context.
        
        Args:
            text_context: Input text context.
        
        Returns:
            Tuple of (predicted_value, confidence).
        """
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call train() first.")
        
        X_vec = self.vectorizer.transform([text_context])
        
        # Get prediction
        y_pred_enc = self.classifier.predict(X_vec)
        y_pred = self.label_encoder.inverse_transform(y_pred_enc)[0]
        
        # Get confidence (probability)
        if hasattr(self.classifier, 'predict_proba'):
            proba = self.classifier.predict_proba(X_vec)[0]
            confidence = float(np.max(proba))
        else:
            confidence = 1.0
        
        return y_pred, confidence
    
    def _calculate_metrics(
        self,
        y_true: List[str],
        y_pred: List[str],
        training_time: float,
    ) -> ModelMetrics:
        """Calculate model metrics."""
        accuracy = accuracy_score(y_true, y_pred)
        precision, recall, f1, _ = precision_recall_fscore_support(
            y_true, y_pred, average='weighted', zero_division=0
        )
        
        # Per-class metrics
        class_report = classification_report(y_true, y_pred, output_dict=True, zero_division=0)
        per_class = {
            k: v for k, v in class_report.items()
            if isinstance(v, dict) and k not in ['accuracy', 'macro avg', 'weighted avg']
        }
        
        # Confusion matrix
        labels = sorted(list(set(y_true) | set(y_pred)))
        cm = confusion_matrix(y_true, y_pred, labels=labels)
        
        return ModelMetrics(
            accuracy=accuracy,
            precision=precision,
            recall=recall,
            f1_score=f1,
            per_class_metrics=per_class,
            confusion_matrix=cm.tolist(),
            sample_count=len(y_true),
            training_time_seconds=training_time,
        )
    
    def get_feature_importance(self, top_n: int = 20) -> Dict[str, float]:
        """Get top feature importances if available."""
        if not self.is_trained:
            return {}
        
        if hasattr(self.classifier, 'feature_importances_'):
            importances = self.classifier.feature_importances_
            indices = np.argsort(importances)[-top_n:][::-1]
            
            return {
                self.feature_names[i]: float(importances[i])
                for i in indices
            }
        
        return {}
    
    def save(self, path: str) -> None:
        """Save the model to disk."""
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        model_data = {
            'field_name': self.field_name,
            'vectorizer': self.vectorizer,
            'classifier': self.classifier,
            'label_encoder': self.label_encoder,
            'feature_names': self.feature_names,
            'config': asdict(self.config),
        }
        
        joblib.dump(model_data, path)
        logger.info(f"Model saved to {path}")
    
    @classmethod
    def load(cls, path: str) -> 'FieldExtractionModel':
        """Load a model from disk."""
        model_data = joblib.load(path)
        
        config = RetrainingConfig(**model_data['config'])
        model = cls(field_name=model_data['field_name'], config=config)
        
        model.vectorizer = model_data['vectorizer']
        model.classifier = model_data['classifier']
        model.label_encoder = model_data['label_encoder']
        model.feature_names = model_data['feature_names']
        model.is_trained = True
        
        logger.info(f"Model loaded from {path}")
        return model


@dataclass
class RetrainingResult:
    """Result of the retraining pipeline."""
    success: bool
    model_artifacts: List[ModelArtifact]
    total_samples: int
    synthetic_samples: int
    hitl_samples: int
    training_time_seconds: float
    output_dir: str
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'success': self.success,
            'model_artifacts': [a.to_dict() for a in self.model_artifacts],
            'total_samples': self.total_samples,
            'synthetic_samples': self.synthetic_samples,
            'hitl_samples': self.hitl_samples,
            'training_time_seconds': self.training_time_seconds,
            'output_dir': self.output_dir,
            'errors': self.errors,
        }


def retrain_parser_model(
    synthetic_data_path: Optional[str] = None,
    hitl_data_path: Optional[str] = None,
    db_session = None,
    output_dir: str = "./models/field_extractor",
    config: Optional[RetrainingConfig] = None,
    fields_to_train: Optional[List[str]] = None,
) -> RetrainingResult:
    """
    Retrain the document parser field extraction models.
    
    This function orchestrates the full retraining pipeline:
    1. Load training data from synthetic and HITL sources
    2. Preprocess and augment data
    3. Train models for each field
    4. Evaluate and save model artifacts
    
    Args:
        synthetic_data_path: Path to synthetic training data JSON.
        hitl_data_path: Path to HITL corrections JSON.
        db_session: Optional SQLAlchemy session for loading HITL data from DB.
        output_dir: Directory to save trained models.
        config: Optional training configuration.
        fields_to_train: Optional list of fields to train (default: all).
    
    Returns:
        RetrainingResult with training outcomes and model artifacts.
    """
    import time
    start_time = time.time()
    
    logger.info("=" * 60)
    logger.info("Starting Document Parser Model Retraining Pipeline")
    logger.info("=" * 60)
    
    if config is None:
        config = RetrainingConfig()
    
    # Initialize result
    result = RetrainingResult(
        success=False,
        model_artifacts=[],
        total_samples=0,
        synthetic_samples=0,
        hitl_samples=0,
        training_time_seconds=0,
        output_dir=output_dir,
        errors=[],
    )
    
    try:
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Initialize dataset
        dataset = FieldExtractionDataset(config)
        
        # Load training data
        if synthetic_data_path:
            result.synthetic_samples = dataset.load_synthetic_data(synthetic_data_path)
        
        if hitl_data_path:
            result.hitl_samples = dataset.load_hitl_data(hitl_data_path)
        
        if db_session:
            db_samples = dataset.load_from_database(db_session)
            result.hitl_samples += db_samples
        
        # Augment data
        if config.augment_synthetic:
            dataset.augment_data()
        
        result.total_samples = len(dataset.samples)
        
        if result.total_samples == 0:
            result.errors.append("No training data available")
            logger.error("No training data loaded. Aborting retraining.")
            return result
        
        # Log dataset statistics
        stats = dataset.get_statistics()
        logger.info(f"Dataset statistics: {json.dumps(stats, indent=2)}")
        
        # Save training data if configured
        if config.save_training_data:
            data_path = os.path.join(output_dir, "training_data.json")
            with open(data_path, 'w') as f:
                json.dump([asdict(s) for s in dataset.samples], f, indent=2)
            logger.info(f"Training data saved to {data_path}")
        
        # Determine fields to train
        if fields_to_train is None:
            fields_to_train = dataset.get_unique_fields()
        
        logger.info(f"Training models for fields: {fields_to_train}")
        
        # Train model for each field
        for field_name in fields_to_train:
            logger.info(f"\n{'='*40}")
            logger.info(f"Training model for field: {field_name}")
            logger.info(f"{'='*40}")
            
            try:
                # Get samples for this field
                field_samples = dataset.get_field_samples(field_name)
                
                if len(field_samples) < config.min_samples_per_field:
                    logger.warning(
                        f"Skipping field '{field_name}': only {len(field_samples)} samples "
                        f"(minimum: {config.min_samples_per_field})"
                    )
                    continue
                
                # Prepare data
                X = [s.text_context for s in field_samples]
                y = [s.field_value for s in field_samples]
                
                # Split data
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y,
                    test_size=config.test_size,
                    random_state=config.random_state,
                    stratify=None,  # Avoid stratify issues with small classes
                )
                
                # Further split for validation
                X_train, X_val, y_train, y_val = train_test_split(
                    X_train, y_train,
                    test_size=config.validation_size,
                    random_state=config.random_state,
                )
                
                logger.info(
                    f"Data split: train={len(X_train)}, val={len(X_val)}, test={len(X_test)}"
                )
                
                # Create and train model
                model = FieldExtractionModel(field_name=field_name, config=config)
                metrics = model.train(X_train, y_train, X_val, y_val)
                
                # Evaluate on test set
                test_metrics = model.evaluate(X_test, y_test)
                logger.info(
                    f"Test metrics: accuracy={test_metrics.accuracy:.4f}, "
                    f"f1={test_metrics.f1_score:.4f}"
                )
                
                # Save model
                model_version = datetime.now().strftime("%Y%m%d_%H%M%S")
                model_id = hashlib.md5(
                    f"{field_name}_{model_version}".encode()
                ).hexdigest()[:8]
                
                model_path = os.path.join(output_dir, f"{field_name}_model.joblib")
                model.save(model_path)
                
                # Save feature importance
                if config.save_feature_importance:
                    importance = model.get_feature_importance()
                    if importance:
                        importance_path = os.path.join(
                            output_dir, f"{field_name}_feature_importance.json"
                        )
                        with open(importance_path, 'w') as f:
                            json.dump(importance, f, indent=2)
                
                # Create artifact metadata
                artifact = ModelArtifact(
                    model_id=model_id,
                    model_version=model_version,
                    model_type=config.model_type,
                    field_name=field_name,
                    created_at=datetime.now().isoformat(),
                    training_samples=len(X_train),
                    synthetic_samples=len([
                        s for s in field_samples if 'synthetic' in s.source
                    ]),
                    hitl_samples=len([
                        s for s in field_samples if s.source == 'hitl'
                    ]),
                    metrics=test_metrics,
                    artifact_path=model_path,
                    config=asdict(config),
                )
                result.model_artifacts.append(artifact)
                
                logger.info(f"Model artifact created: {model_id}")
                
            except Exception as e:
                error_msg = f"Failed to train model for field '{field_name}': {e}"
                logger.error(error_msg, exc_info=True)
                result.errors.append(error_msg)
        
        # Save manifest
        manifest_path = os.path.join(output_dir, "manifest.json")
        with open(manifest_path, 'w') as f:
            json.dump(result.to_dict(), f, indent=2)
        logger.info(f"Manifest saved to {manifest_path}")
        
        result.success = len(result.model_artifacts) > 0
        result.training_time_seconds = time.time() - start_time
        
        logger.info("\n" + "=" * 60)
        logger.info("Retraining Pipeline Complete")
        logger.info(f"  Success: {result.success}")
        logger.info(f"  Models trained: {len(result.model_artifacts)}")
        logger.info(f"  Total time: {result.training_time_seconds:.2f}s")
        logger.info("=" * 60)
        
    except Exception as e:
        error_msg = f"Retraining pipeline failed: {e}"
        logger.error(error_msg, exc_info=True)
        result.errors.append(error_msg)
        result.training_time_seconds = time.time() - start_time
    
    return result


def generate_synthetic_training_data(
    num_samples: int = 100,
    output_path: str = "./data/synthetic/training_labels.json",
) -> str:
    """
    Generate synthetic training data for testing the pipeline.
    
    Args:
        num_samples: Number of samples to generate.
        output_path: Path to save the generated data.
    
    Returns:
        Path to the generated file.
    """
    import random
    from faker import Faker
    
    fake = Faker()
    random.seed(42)
    Faker.seed(42)
    
    samples = []
    
    for i in range(num_samples):
        # Generate realistic field values
        total_amount = f"${random.uniform(50, 5000):.2f}"
        invoice_number = f"INV-{random.randint(10000, 99999)}"
        patient_name = fake.name()
        bill_date = fake.date_this_year().strftime("%m/%d/%Y")
        
        sample = {
            "document_id": f"doc_{i:05d}",
            "total_amount": total_amount,
            "invoice_number": invoice_number,
            "patient_name": patient_name,
            "bill_date": bill_date,
            "provider_name": f"{fake.city()} Medical Center",
            "subtotal": f"${random.uniform(40, 4500):.2f}",
            "tax": f"${random.uniform(0, 500):.2f}",
        }
        samples.append(sample)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(samples, f, indent=2)
    
    logger.info(f"Generated {num_samples} synthetic samples at {output_path}")
    return output_path


def generate_hitl_training_data(
    num_samples: int = 50,
    output_path: str = "./data/hitl/corrections.json",
) -> str:
    """
    Generate simulated HITL correction data for testing.
    
    Args:
        num_samples: Number of samples to generate.
        output_path: Path to save the generated data.
    
    Returns:
        Path to the generated file.
    """
    import random
    from faker import Faker
    
    fake = Faker()
    random.seed(123)
    Faker.seed(123)
    
    corrections = []
    
    field_types = ['total_amount', 'invoice_number', 'patient_name', 'bill_date']
    
    for i in range(num_samples):
        field_name = random.choice(field_types)
        
        # Simulate OCR errors and corrections
        if field_name == 'total_amount':
            correct_value = f"${random.uniform(50, 5000):.2f}"
            # Simulate OCR error
            extracted_value = correct_value.replace('$', 'S').replace('.', ',')
        elif field_name == 'invoice_number':
            correct_value = f"INV-{random.randint(10000, 99999)}"
            extracted_value = correct_value.replace('I', '1').replace('V', 'U')
        elif field_name == 'patient_name':
            correct_value = fake.name()
            # Simulate typo
            extracted_value = correct_value[:-1] + random.choice('abcde')
        else:
            correct_value = fake.date_this_year().strftime("%m/%d/%Y")
            extracted_value = correct_value.replace('/', '-')
        
        correction = {
            "document_id": f"doc_{i:05d}",
            "field_name": field_name,
            "extracted_value": extracted_value,
            "correct_value": correct_value,
            "original_confidence": random.uniform(0.3, 0.7),
        }
        corrections.append(correction)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(corrections, f, indent=2)
    
    logger.info(f"Generated {num_samples} HITL corrections at {output_path}")
    return output_path


if __name__ == "__main__":
    """Test run with synthetic data."""
    import tempfile
    
    print("=" * 60)
    print("Running Retraining Pipeline Test")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate test data
        synthetic_path = os.path.join(temp_dir, "synthetic", "labels.json")
        hitl_path = os.path.join(temp_dir, "hitl", "corrections.json")
        output_dir = os.path.join(temp_dir, "models")
        
        generate_synthetic_training_data(num_samples=100, output_path=synthetic_path)
        generate_hitl_training_data(num_samples=50, output_path=hitl_path)
        
        # Run retraining
        result = retrain_parser_model(
            synthetic_data_path=synthetic_path,
            hitl_data_path=hitl_path,
            output_dir=output_dir,
            config=RetrainingConfig(
                model_type='random_forest',
                n_estimators=50,
                min_samples_per_field=5,
            ),
        )
        
        print("\n" + "=" * 60)
        print("Test Results")
        print("=" * 60)
        print(f"Success: {result.success}")
        print(f"Models trained: {len(result.model_artifacts)}")
        print(f"Total samples: {result.total_samples}")
        print(f"Training time: {result.training_time_seconds:.2f}s")
        
        if result.model_artifacts:
            print("\nModel Artifacts:")
            for artifact in result.model_artifacts:
                print(f"  - {artifact.field_name}: accuracy={artifact.metrics.accuracy:.4f}")
        
        if result.errors:
            print("\nErrors:")
            for error in result.errors:
                print(f"  - {error}")

