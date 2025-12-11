"""
Unit tests for ML-based audit module.

Tests anomaly detection with synthetic medical bill data.
"""

import pytest
import numpy as np
import tempfile
from pathlib import Path
import sys
import os

# Add ml directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "ml"))

from audit.ml_audit import (
    MLAuditModel,
    ModelConfig,
    BillFeatureExtractor,
    AnomalyPrediction,
    TrainingMetrics,
    generate_synthetic_bill,
    generate_synthetic_dataset,
    create_pretrained_model,
    predict_anomaly,
    RetrainingPipeline,
)


@pytest.fixture
def normal_bill() -> dict:
    """Create a normal (non-anomalous) bill."""
    return {
        "document_id": 1,
        "total_amount": 284.00,
        "subtotal": 284.00,
        "tax_amount": 0.0,
        "tax_rate": 0.0,
        "discount": 0.0,
        "insurance_paid": 200.0,
        "patient_responsibility": 84.00,
        "line_items": [
            {
                "code": "99213",
                "description": "Office Visit",
                "quantity": 1,
                "unit_price": 150.00,
                "total": 150.00,
            },
            {
                "code": "85025",
                "description": "CBC",
                "quantity": 1,
                "unit_price": 45.00,
                "total": 45.00,
            },
            {
                "code": "80053",
                "description": "Metabolic Panel",
                "quantity": 1,
                "unit_price": 89.00,
                "total": 89.00,
            },
        ],
        "invoice_number": "INV-12345",
        "patient_name": "John Doe",
        "bill_date": "2024-01-15",
    }


@pytest.fixture
def anomalous_bill() -> dict:
    """Create an anomalous bill with multiple issues."""
    return {
        "document_id": 2,
        "total_amount": 1500.00,  # Doesn't match calculations
        "subtotal": 1000.00,
        "tax_amount": 200.00,  # 20% tax - unusual
        "tax_rate": 0.20,
        "discount": 0.0,
        "insurance_paid": 0.0,
        "patient_responsibility": 1500.00,
        "line_items": [
            {
                "code": "99213",
                "description": "Office Visit",
                "quantity": 1,
                "unit_price": 500.00,  # Overcharge
                "total": 500.00,
            },
            {
                "code": "85025",
                "description": "CBC",
                "quantity": 1,
                "unit_price": 250.00,  # Overcharge
                "total": 250.00,
            },
            {
                "code": "85025",
                "description": "CBC",
                "quantity": 1,
                "unit_price": 250.00,
                "total": 250.00,
            },  # Duplicate
        ],
        "invoice_number": "INV-99999",
        "patient_name": "Test Patient",
        "bill_date": "2024-01-15",
    }


@pytest.fixture
def model_config() -> ModelConfig:
    """Create test model configuration."""
    return ModelConfig(
        model_type="random_forest",
        n_estimators=10,  # Fewer for faster tests
        max_depth=5,
        random_state=42,
    )


@pytest.fixture
def trained_model(model_config: ModelConfig) -> MLAuditModel:
    """Create a trained model with synthetic data."""
    model = MLAuditModel(config=model_config)
    bills, labels = generate_synthetic_dataset(n_samples=200, random_state=42)
    model.train(bills, labels)
    return model


class TestBillFeatureExtractor:
    """Test cases for feature extraction."""

    def test_extract_features_shape(self, normal_bill: dict):
        """Test that extracted features have correct shape."""
        extractor = BillFeatureExtractor()
        features = extractor.extract_features(normal_bill)

        assert isinstance(features, np.ndarray)
        assert features.shape == (len(extractor.FEATURE_NAMES),)

    def test_extract_batch(self, normal_bill: dict, anomalous_bill: dict):
        """Test batch feature extraction."""
        extractor = BillFeatureExtractor()
        features = extractor.extract_batch([normal_bill, anomalous_bill])

        assert features.shape == (2, len(extractor.FEATURE_NAMES))

    def test_handles_missing_fields(self):
        """Test handling of bills with missing fields."""
        incomplete_bill = {
            "document_id": 1,
            "total_amount": 100.0,
        }

        extractor = BillFeatureExtractor()
        features = extractor.extract_features(incomplete_bill)

        assert not np.any(np.isnan(features))
        assert features.shape == (len(extractor.FEATURE_NAMES),)

    def test_handles_empty_line_items(self):
        """Test handling of bills with no line items."""
        bill = {
            "document_id": 1,
            "total_amount": 100.0,
            "line_items": [],
        }

        extractor = BillFeatureExtractor()
        features = extractor.extract_features(bill)

        assert not np.any(np.isnan(features))

    def test_detects_duplicates(self, anomalous_bill: dict):
        """Test duplicate detection in features."""
        extractor = BillFeatureExtractor()
        features = extractor.extract_features(anomalous_bill)

        # has_duplicates is feature index 13
        assert features[13] == 1.0

    def test_scaling(self, normal_bill: dict, anomalous_bill: dict):
        """Test feature scaling."""
        extractor = BillFeatureExtractor()
        features = extractor.extract_batch([normal_bill, anomalous_bill])

        scaled = extractor.fit_transform(features)

        # Scaled features should have ~0 mean and ~1 std
        assert abs(np.mean(scaled)) < 0.5
        assert 0.5 < np.std(scaled) < 1.5


class TestMLAuditModel:
    """Test cases for ML audit model."""

    def test_model_initialization(self, model_config: ModelConfig):
        """Test model initializes correctly."""
        model = MLAuditModel(config=model_config)

        assert model.config == model_config
        assert model.classifier is not None
        assert model._trained is False

    def test_train_returns_metrics(self, model_config: ModelConfig):
        """Test that training returns valid metrics."""
        model = MLAuditModel(config=model_config)
        bills, labels = generate_synthetic_dataset(n_samples=100, random_state=42)

        metrics = model.train(bills, labels)

        assert "accuracy" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1_score" in metrics
        assert "auc_roc" in metrics
        assert metrics["samples_trained"] > 0

    def test_train_marks_model_trained(self, model_config: ModelConfig):
        """Test that training sets trained flag."""
        model = MLAuditModel(config=model_config)
        bills, labels = generate_synthetic_dataset(n_samples=100, random_state=42)

        model.train(bills, labels)

        assert model._trained is True

    def test_predict_returns_correct_structure(self, trained_model: MLAuditModel, normal_bill: dict):
        """Test prediction returns correct structure."""
        prediction = trained_model.predict(normal_bill)

        assert "document_id" in prediction
        assert "anomaly_score" in prediction
        assert "is_anomaly" in prediction
        assert "confidence" in prediction
        assert "risk_factors" in prediction

    def test_predict_score_range(self, trained_model: MLAuditModel, normal_bill: dict):
        """Test that anomaly score is in valid range."""
        prediction = trained_model.predict(normal_bill)

        assert 0.0 <= prediction["anomaly_score"] <= 1.0
        assert 0.0 <= prediction["confidence"] <= 1.0

    def test_predict_batch(self, trained_model: MLAuditModel, normal_bill: dict, anomalous_bill: dict):
        """Test batch prediction."""
        predictions = trained_model.predict_batch([normal_bill, anomalous_bill])

        assert len(predictions) == 2
        assert all("anomaly_score" in p for p in predictions)

    def test_untrained_model_returns_default(self, model_config: ModelConfig, normal_bill: dict):
        """Test that untrained model returns safe defaults."""
        model = MLAuditModel(config=model_config)
        prediction = model.predict(normal_bill)

        assert prediction["anomaly_score"] == 0.5
        assert prediction["confidence"] == 0.0
        assert "model_not_trained" in prediction["risk_factors"]

    def test_identifies_risk_factors(self, trained_model: MLAuditModel, anomalous_bill: dict):
        """Test risk factor identification."""
        prediction = trained_model.predict(anomalous_bill)

        # Anomalous bill should have some risk factors
        assert isinstance(prediction["risk_factors"], list)

    def test_anomaly_detection_accuracy(self, model_config: ModelConfig):
        """Test that model can distinguish anomalies."""
        model = MLAuditModel(config=model_config)
        bills, labels = generate_synthetic_dataset(n_samples=500, random_state=42)

        metrics = model.train(bills, labels)

        # Model should perform reasonably well
        assert metrics["auc_roc"] > 0.6
        assert metrics["f1_score"] > 0.3


class TestModelPersistence:
    """Test cases for model save/load."""

    def test_save_and_load(self, trained_model: MLAuditModel, normal_bill: dict):
        """Test model can be saved and loaded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "model.pkl"

            trained_model.save(str(path))
            assert path.exists()

            loaded_model = MLAuditModel.load(str(path))
            assert loaded_model._trained is True

            # Predictions should match
            orig_pred = trained_model.predict(normal_bill)
            loaded_pred = loaded_model.predict(normal_bill)

            assert orig_pred["anomaly_score"] == loaded_pred["anomaly_score"]

    def test_creates_parent_directories(self, trained_model: MLAuditModel):
        """Test that save creates parent directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dirs" / "model.pkl"

            trained_model.save(str(path))
            assert path.exists()


class TestSyntheticDataGeneration:
    """Test cases for synthetic data generation."""

    def test_generate_single_bill(self):
        """Test single bill generation."""
        bill = generate_synthetic_bill(random_state=42)

        assert "document_id" in bill
        assert "total_amount" in bill
        assert "line_items" in bill
        assert len(bill["line_items"]) > 0

    def test_generate_normal_bill(self):
        """Test normal bill generation."""
        bill = generate_synthetic_bill(is_anomaly=False, random_state=42)

        # Check arithmetic is correct
        line_sum = sum(item["total"] for item in bill["line_items"])
        assert abs(line_sum - bill["subtotal"]) < 1.0

    def test_generate_anomalous_bill(self):
        """Test anomalous bill generation."""
        # Generate multiple to check anomaly features
        anomalies_found = {
            "duplicate": False,
            "arithmetic": False,
            "overcharge": False,
            "tax": False,
        }

        for i in range(50):
            bill = generate_synthetic_bill(is_anomaly=True, random_state=i)

            # Check for duplicate
            codes = [item["code"] for item in bill["line_items"]]
            if len(codes) != len(set(codes)):
                anomalies_found["duplicate"] = True

            # Check for arithmetic error
            line_sum = sum(item["total"] for item in bill["line_items"])
            if abs(line_sum - bill["subtotal"]) > 1.0:
                anomalies_found["arithmetic"] = True

            # Check for high tax
            if bill["tax_rate"] > 0.15:
                anomalies_found["tax"] = True

        # At least some anomaly types should appear
        assert sum(anomalies_found.values()) >= 1

    def test_generate_dataset(self):
        """Test dataset generation."""
        bills, labels = generate_synthetic_dataset(
            n_samples=100,
            anomaly_ratio=0.3,
            random_state=42,
        )

        assert len(bills) == 100
        assert len(labels) == 100
        assert sum(labels) == 30  # 30% anomalies

    def test_dataset_is_shuffled(self):
        """Test that generated dataset is shuffled."""
        bills, labels = generate_synthetic_dataset(
            n_samples=100,
            anomaly_ratio=0.5,
            random_state=42,
        )

        # Not all anomalies should be at the end
        first_half_anomalies = sum(labels[:50])
        assert 10 < first_half_anomalies < 40


class TestConvenienceFunctions:
    """Test cases for convenience functions."""

    def test_create_pretrained_model(self):
        """Test pretrained model creation."""
        model = create_pretrained_model()

        assert model._trained is True
        assert model.classifier is not None

    def test_predict_anomaly_function(self, normal_bill: dict):
        """Test standalone prediction function."""
        prediction = predict_anomaly(normal_bill)

        assert "anomaly_score" in prediction
        assert 0.0 <= prediction["anomaly_score"] <= 1.0


class TestRetrainingPipeline:
    """Test cases for retraining pipeline."""

    def test_pipeline_initialization(self, trained_model: MLAuditModel):
        """Test pipeline initializes correctly."""
        pipeline = RetrainingPipeline(trained_model)

        assert pipeline.model == trained_model
        assert pipeline.training_history == []

    def test_fetch_training_data_returns_synthetic(self, trained_model: MLAuditModel):
        """Test that placeholder returns synthetic data."""
        pipeline = RetrainingPipeline(trained_model)
        bills, labels = pipeline.fetch_training_data()

        assert len(bills) > 0
        assert len(labels) == len(bills)

    def test_retrain_updates_model(self, model_config: ModelConfig):
        """Test that retraining updates model."""
        model = MLAuditModel(config=model_config)
        pipeline = RetrainingPipeline(model)

        metrics = pipeline.retrain(min_samples=50)

        assert metrics is not None
        assert model._trained is True
        assert len(pipeline.training_history) == 1

    def test_retrain_skips_insufficient_data(self, trained_model: MLAuditModel):
        """Test that retraining is skipped with insufficient data."""
        pipeline = RetrainingPipeline(trained_model)

        # Require more samples than available
        metrics = pipeline.retrain(min_samples=100000)

        assert metrics is None

    def test_schedule_raises_not_implemented(self, trained_model: MLAuditModel):
        """Test that scheduling raises NotImplementedError."""
        pipeline = RetrainingPipeline(trained_model)

        with pytest.raises(NotImplementedError):
            pipeline.schedule_retraining()


class TestModelConfiguration:
    """Test cases for model configuration."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ModelConfig()

        assert config.model_type == "lightgbm"
        assert config.n_estimators == 100
        assert config.max_depth == 10
        assert config.anomaly_threshold == 0.5

    def test_custom_config(self):
        """Test custom configuration."""
        config = ModelConfig(
            model_type="random_forest",
            n_estimators=50,
            anomaly_threshold=0.7,
        )

        assert config.model_type == "random_forest"
        assert config.n_estimators == 50
        assert config.anomaly_threshold == 0.7


class TestIntegration:
    """Integration tests for full pipeline."""

    def test_full_training_and_prediction_flow(self):
        """Test complete training and prediction flow."""
        # Generate data
        bills, labels = generate_synthetic_dataset(
            n_samples=300,
            anomaly_ratio=0.2,
            random_state=42,
        )

        # Train model
        model = MLAuditModel(ModelConfig(
            model_type="random_forest",
            n_estimators=20,
            random_state=42,
        ))
        metrics = model.train(bills, labels)

        # Verify training
        assert metrics["auc_roc"] > 0.5

        # Make predictions
        test_bills = bills[:10]
        predictions = model.predict_batch(test_bills)

        assert len(predictions) == 10
        assert all(0 <= p["anomaly_score"] <= 1 for p in predictions)

    def test_model_persistence_flow(self):
        """Test complete save/load/predict flow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Train and save
            bills, labels = generate_synthetic_dataset(n_samples=200, random_state=42)
            model = MLAuditModel(ModelConfig(n_estimators=10, random_state=42))
            model.train(bills, labels)

            model_path = Path(tmpdir) / "audit_model.pkl"
            model.save(str(model_path))

            # Load and predict
            loaded = MLAuditModel.load(str(model_path))
            test_bill = bills[0]

            orig_pred = model.predict(test_bill)
            loaded_pred = loaded.predict(test_bill)

            assert orig_pred["anomaly_score"] == loaded_pred["anomaly_score"]

