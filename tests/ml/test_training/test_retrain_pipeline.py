"""
Unit tests for retrain_pipeline.py module.
"""

import json
import os
import tempfile
import shutil
from pathlib import Path

import pytest
import numpy as np

from ml.training.retrain_pipeline import (
    TrainingSample,
    ModelMetrics,
    ModelArtifact,
    RetrainingConfig,
    FieldExtractionDataset,
    FieldExtractionModel,
    RetrainingResult,
    retrain_parser_model,
    generate_synthetic_training_data,
    generate_hitl_training_data,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test output."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_config():
    """Create a sample training configuration."""
    return RetrainingConfig(
        model_type='random_forest',
        n_estimators=10,
        min_samples_per_field=3,
        test_size=0.2,
        validation_size=0.1,
        augment_synthetic=False,
    )


@pytest.fixture
def synthetic_data_path(temp_dir):
    """Generate synthetic training data."""
    path = os.path.join(temp_dir, "synthetic", "labels.json")
    generate_synthetic_training_data(num_samples=50, output_path=path)
    return path


@pytest.fixture
def hitl_data_path(temp_dir):
    """Generate HITL correction data."""
    path = os.path.join(temp_dir, "hitl", "corrections.json")
    generate_hitl_training_data(num_samples=30, output_path=path)
    return path


class TestTrainingSample:
    """Tests for TrainingSample dataclass."""
    
    def test_create_training_sample(self):
        """Should create a valid training sample."""
        sample = TrainingSample(
            text_context="Total Amount: $1,234.56",
            field_name="total_amount",
            field_value="$1,234.56",
            source="synthetic",
            confidence=1.0,
            document_id="doc_001",
        )
        
        assert sample.field_name == "total_amount"
        assert sample.field_value == "$1,234.56"
        assert sample.source == "synthetic"


class TestRetrainingConfig:
    """Tests for RetrainingConfig dataclass."""
    
    def test_default_config(self):
        """Should have sensible defaults."""
        config = RetrainingConfig()
        
        assert config.model_type == "random_forest"
        assert config.n_estimators == 100
        assert config.test_size == 0.2
        assert config.min_samples_per_field == 10
    
    def test_custom_config(self):
        """Should allow custom configuration."""
        config = RetrainingConfig(
            model_type="gradient_boosting",
            n_estimators=50,
            max_depth=5,
        )
        
        assert config.model_type == "gradient_boosting"
        assert config.n_estimators == 50
        assert config.max_depth == 5


class TestFieldExtractionDataset:
    """Tests for FieldExtractionDataset class."""
    
    def test_load_synthetic_data(self, sample_config, synthetic_data_path):
        """Should load synthetic training data."""
        dataset = FieldExtractionDataset(sample_config)
        count = dataset.load_synthetic_data(synthetic_data_path)
        
        assert count > 0
        assert len(dataset.samples) == count
    
    def test_load_hitl_data(self, sample_config, hitl_data_path):
        """Should load HITL correction data."""
        dataset = FieldExtractionDataset(sample_config)
        count = dataset.load_hitl_data(hitl_data_path)
        
        assert count > 0
        assert len(dataset.samples) == count
    
    def test_load_nonexistent_file(self, sample_config):
        """Should handle missing files gracefully."""
        dataset = FieldExtractionDataset(sample_config)
        count = dataset.load_synthetic_data("/nonexistent/path.json")
        
        assert count == 0
    
    def test_get_unique_fields(self, sample_config, synthetic_data_path):
        """Should return unique field names."""
        dataset = FieldExtractionDataset(sample_config)
        dataset.load_synthetic_data(synthetic_data_path)
        
        fields = dataset.get_unique_fields()
        
        assert 'total_amount' in fields
        assert 'patient_name' in fields
    
    def test_get_field_samples(self, sample_config, synthetic_data_path):
        """Should filter samples by field name."""
        dataset = FieldExtractionDataset(sample_config)
        dataset.load_synthetic_data(synthetic_data_path)
        
        samples = dataset.get_field_samples('total_amount')
        
        assert len(samples) > 0
        assert all(s.field_name == 'total_amount' for s in samples)
    
    def test_to_dataframe(self, sample_config, synthetic_data_path):
        """Should convert to pandas DataFrame."""
        dataset = FieldExtractionDataset(sample_config)
        dataset.load_synthetic_data(synthetic_data_path)
        
        df = dataset.to_dataframe()
        
        assert len(df) == len(dataset.samples)
        assert 'text_context' in df.columns
        assert 'field_name' in df.columns
    
    def test_get_statistics(self, sample_config, synthetic_data_path, hitl_data_path):
        """Should calculate dataset statistics."""
        dataset = FieldExtractionDataset(sample_config)
        dataset.load_synthetic_data(synthetic_data_path)
        dataset.load_hitl_data(hitl_data_path)
        
        stats = dataset.get_statistics()
        
        assert stats['total_samples'] > 0
        assert 'synthetic_samples' in stats
        assert 'hitl_samples' in stats
        assert 'unique_fields' in stats
    
    def test_augment_data(self, synthetic_data_path):
        """Should augment training data."""
        config = RetrainingConfig(augment_synthetic=True)
        dataset = FieldExtractionDataset(config)
        
        original_count = dataset.load_synthetic_data(synthetic_data_path)
        augmented_count = dataset.augment_data()
        
        assert augmented_count > 0
        assert len(dataset.samples) > original_count


class TestFieldExtractionModel:
    """Tests for FieldExtractionModel class."""
    
    @pytest.fixture
    def training_data(self):
        """Generate training data for model tests."""
        X = [
            "Total Amount: $100.00",
            "Total Due: $200.00",
            "Amount: $150.50",
            "Total: $300.00",
            "Balance Due: $250.00",
            "Total Amount: $175.00",
            "Amount Due: $125.00",
            "Total: $400.00",
        ]
        y = [
            "$100.00",
            "$200.00",
            "$150.50",
            "$300.00",
            "$250.00",
            "$175.00",
            "$125.00",
            "$400.00",
        ]
        return X, y
    
    def test_train_model(self, sample_config, training_data):
        """Should train the model successfully."""
        X, y = training_data
        
        model = FieldExtractionModel(field_name="total_amount", config=sample_config)
        metrics = model.train(X, y)
        
        assert model.is_trained
        assert isinstance(metrics, ModelMetrics)
        assert metrics.sample_count == len(X)
    
    def test_predict(self, sample_config, training_data):
        """Should make predictions after training."""
        X, y = training_data
        
        model = FieldExtractionModel(field_name="total_amount", config=sample_config)
        model.train(X, y)
        
        prediction, confidence = model.predict("Total Amount: $500.00")
        
        assert prediction is not None
        assert 0 <= confidence <= 1
    
    def test_predict_untrained(self, sample_config):
        """Should raise error when predicting before training."""
        model = FieldExtractionModel(field_name="total_amount", config=sample_config)
        
        with pytest.raises(RuntimeError, match="not trained"):
            model.predict("Some text")
    
    def test_evaluate(self, sample_config, training_data):
        """Should evaluate model on test data."""
        X, y = training_data
        X_train, X_test = X[:6], X[6:]
        y_train, y_test = y[:6], y[6:]
        
        model = FieldExtractionModel(field_name="total_amount", config=sample_config)
        model.train(X_train, y_train)
        
        metrics = model.evaluate(X_test, y_test)
        
        assert isinstance(metrics, ModelMetrics)
        assert 0 <= metrics.accuracy <= 1
    
    def test_save_and_load(self, sample_config, training_data, temp_dir):
        """Should save and load model correctly."""
        X, y = training_data
        
        model = FieldExtractionModel(field_name="total_amount", config=sample_config)
        model.train(X, y)
        
        # Save
        model_path = os.path.join(temp_dir, "test_model.joblib")
        model.save(model_path)
        
        assert os.path.exists(model_path)
        
        # Load
        loaded_model = FieldExtractionModel.load(model_path)
        
        assert loaded_model.is_trained
        assert loaded_model.field_name == "total_amount"
        
        # Should produce same predictions
        pred1, _ = model.predict("Total: $999.00")
        pred2, _ = loaded_model.predict("Total: $999.00")
        
        assert pred1 == pred2
    
    def test_get_feature_importance(self, sample_config, training_data):
        """Should return feature importances for random forest."""
        X, y = training_data
        
        model = FieldExtractionModel(field_name="total_amount", config=sample_config)
        model.train(X, y)
        
        importance = model.get_feature_importance(top_n=5)
        
        assert isinstance(importance, dict)
        # Random forest should have feature importances
        assert len(importance) > 0
    
    def test_different_model_types(self, training_data):
        """Should support different model types."""
        X, y = training_data
        
        for model_type in ['random_forest', 'logistic_regression']:
            config = RetrainingConfig(model_type=model_type, n_estimators=10)
            model = FieldExtractionModel(field_name="total_amount", config=config)
            metrics = model.train(X, y)
            
            assert model.is_trained
            assert metrics.accuracy > 0


class TestGenerateSyntheticData:
    """Tests for synthetic data generation."""
    
    def test_generate_synthetic_data(self, temp_dir):
        """Should generate synthetic training data."""
        path = os.path.join(temp_dir, "synthetic.json")
        result_path = generate_synthetic_training_data(
            num_samples=10,
            output_path=path,
        )
        
        assert os.path.exists(result_path)
        
        with open(result_path, 'r') as f:
            data = json.load(f)
        
        assert len(data) == 10
        assert all('total_amount' in d for d in data)
        assert all('patient_name' in d for d in data)


class TestGenerateHitlData:
    """Tests for HITL data generation."""
    
    def test_generate_hitl_data(self, temp_dir):
        """Should generate HITL correction data."""
        path = os.path.join(temp_dir, "hitl.json")
        result_path = generate_hitl_training_data(
            num_samples=10,
            output_path=path,
        )
        
        assert os.path.exists(result_path)
        
        with open(result_path, 'r') as f:
            data = json.load(f)
        
        assert len(data) == 10
        assert all('field_name' in d for d in data)
        assert all('correct_value' in d for d in data)
        assert all('extracted_value' in d for d in data)


class TestRetrainParserModel:
    """Tests for the main retraining function."""
    
    def test_retrain_with_synthetic_data(self, temp_dir, synthetic_data_path):
        """Should train models with synthetic data only."""
        output_dir = os.path.join(temp_dir, "models")
        
        result = retrain_parser_model(
            synthetic_data_path=synthetic_data_path,
            output_dir=output_dir,
            config=RetrainingConfig(
                n_estimators=10,
                min_samples_per_field=3,
            ),
        )
        
        assert result.success
        assert result.synthetic_samples > 0
        assert len(result.model_artifacts) > 0
    
    def test_retrain_with_hitl_data(self, temp_dir, hitl_data_path):
        """Should train models with HITL data only."""
        output_dir = os.path.join(temp_dir, "models")
        
        result = retrain_parser_model(
            hitl_data_path=hitl_data_path,
            output_dir=output_dir,
            config=RetrainingConfig(
                n_estimators=10,
                min_samples_per_field=3,
            ),
        )
        
        assert result.success
        assert result.hitl_samples > 0
        assert len(result.model_artifacts) > 0
    
    def test_retrain_with_combined_data(
        self, temp_dir, synthetic_data_path, hitl_data_path
    ):
        """Should train models with both data sources."""
        output_dir = os.path.join(temp_dir, "models")
        
        result = retrain_parser_model(
            synthetic_data_path=synthetic_data_path,
            hitl_data_path=hitl_data_path,
            output_dir=output_dir,
            config=RetrainingConfig(
                n_estimators=10,
                min_samples_per_field=3,
            ),
        )
        
        assert result.success
        assert result.synthetic_samples > 0
        assert result.hitl_samples > 0
        assert result.total_samples >= result.synthetic_samples + result.hitl_samples
    
    def test_retrain_saves_artifacts(self, temp_dir, synthetic_data_path):
        """Should save model artifacts and manifest."""
        output_dir = os.path.join(temp_dir, "models")
        
        result = retrain_parser_model(
            synthetic_data_path=synthetic_data_path,
            output_dir=output_dir,
            config=RetrainingConfig(
                n_estimators=10,
                min_samples_per_field=3,
            ),
        )
        
        # Check manifest exists
        manifest_path = os.path.join(output_dir, "manifest.json")
        assert os.path.exists(manifest_path)
        
        # Check model files exist
        for artifact in result.model_artifacts:
            assert os.path.exists(artifact.artifact_path)
    
    def test_retrain_no_data(self, temp_dir):
        """Should handle no data gracefully."""
        output_dir = os.path.join(temp_dir, "models")
        
        result = retrain_parser_model(
            synthetic_data_path="/nonexistent/path.json",
            output_dir=output_dir,
        )
        
        assert not result.success
        assert "No training data" in result.errors[0]
    
    def test_retrain_specific_fields(self, temp_dir, synthetic_data_path):
        """Should train only specified fields."""
        output_dir = os.path.join(temp_dir, "models")
        
        result = retrain_parser_model(
            synthetic_data_path=synthetic_data_path,
            output_dir=output_dir,
            fields_to_train=['total_amount', 'patient_name'],
            config=RetrainingConfig(
                n_estimators=10,
                min_samples_per_field=3,
            ),
        )
        
        assert result.success
        field_names = [a.field_name for a in result.model_artifacts]
        assert 'total_amount' in field_names or 'patient_name' in field_names
    
    def test_model_artifact_metrics(self, temp_dir, synthetic_data_path):
        """Should include metrics in model artifacts."""
        output_dir = os.path.join(temp_dir, "models")
        
        result = retrain_parser_model(
            synthetic_data_path=synthetic_data_path,
            output_dir=output_dir,
            config=RetrainingConfig(
                n_estimators=10,
                min_samples_per_field=3,
            ),
        )
        
        assert result.success
        
        for artifact in result.model_artifacts:
            assert artifact.metrics is not None
            assert 0 <= artifact.metrics.accuracy <= 1
            assert artifact.metrics.sample_count > 0
    
    def test_retrain_saves_training_data(self, temp_dir, synthetic_data_path):
        """Should save training data when configured."""
        output_dir = os.path.join(temp_dir, "models")
        
        result = retrain_parser_model(
            synthetic_data_path=synthetic_data_path,
            output_dir=output_dir,
            config=RetrainingConfig(
                n_estimators=10,
                min_samples_per_field=3,
                save_training_data=True,
            ),
        )
        
        training_data_path = os.path.join(output_dir, "training_data.json")
        assert os.path.exists(training_data_path)


class TestIntegration:
    """Integration tests for the full pipeline."""
    
    def test_full_pipeline_with_synthetic_data(self, temp_dir):
        """Test complete pipeline from data generation to model inference."""
        # Generate data
        synthetic_path = os.path.join(temp_dir, "synthetic", "labels.json")
        hitl_path = os.path.join(temp_dir, "hitl", "corrections.json")
        output_dir = os.path.join(temp_dir, "models")
        
        generate_synthetic_training_data(num_samples=100, output_path=synthetic_path)
        generate_hitl_training_data(num_samples=50, output_path=hitl_path)
        
        # Train models
        result = retrain_parser_model(
            synthetic_data_path=synthetic_path,
            hitl_data_path=hitl_path,
            output_dir=output_dir,
            config=RetrainingConfig(
                model_type='random_forest',
                n_estimators=20,
                min_samples_per_field=5,
            ),
        )
        
        assert result.success
        assert len(result.model_artifacts) > 0
        
        # Load and use a trained model
        if result.model_artifacts:
            artifact = result.model_artifacts[0]
            model = FieldExtractionModel.load(artifact.artifact_path)
            
            prediction, confidence = model.predict("Total Amount: $1,500.00")
            
            assert prediction is not None
            assert confidence > 0
        
        print(f"\n✅ Full pipeline test passed")
        print(f"   Models trained: {len(result.model_artifacts)}")
        print(f"   Total samples: {result.total_samples}")
        print(f"   Training time: {result.training_time_seconds:.2f}s")

