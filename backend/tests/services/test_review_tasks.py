"""
Unit tests for review_tasks.py module.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, call
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.db.base import Base
from app.models.document import Document, DocumentStatus
from app.models.parsed_field import ParsedField
from app.models.review_task import ReviewTask, ReviewTaskStatus
from app.models.user import User
from app.services.review_tasks import (
    ReviewTaskService,
    ReviewTaskSummary,
    ReviewTaskDetail,
    CorrectionResult,
    TaskNotFoundError,
    TaskAlreadyCompletedError,
)


@pytest.fixture
def db_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def db_session(db_engine):
    """Create a new database session for testing."""
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def sample_user(db_session):
    """Create a sample user for testing."""
    user = User(
        email="reviewer@example.com",
        username="reviewer",
        hashed_password="hashed_password",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def sample_document(db_session, sample_user):
    """Create a sample document for testing."""
    document = Document(
        user_id=sample_user.id,
        file_name="test_bill.pdf",
        file_key="uploads/test_bill.pdf",
        content_type="application/pdf",
        file_size=1024,
        status=DocumentStatus.COMPLETED,
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


@pytest.fixture
def sample_parsed_fields(db_session, sample_document):
    """Create sample parsed fields for testing."""
    fields = [
        ParsedField(
            document_id=sample_document.id,
            field_name="total_amount",
            field_value="$1,234.56",
            confidence=0.95,
            source="regex",
        ),
        ParsedField(
            document_id=sample_document.id,
            field_name="patient_name",
            field_value="John Doe",
            confidence=0.72,
            source="ocr",
        ),
        ParsedField(
            document_id=sample_document.id,
            field_name="invoice_number",
            field_value="INV-2024",
            confidence=0.55,
            source="fuzzy",
        ),
        ParsedField(
            document_id=sample_document.id,
            field_name="bill_date",
            field_value="01/15/2024",
            confidence=0.40,
            source="regex",
        ),
    ]
    
    for field in fields:
        db_session.add(field)
    
    db_session.commit()
    
    for field in fields:
        db_session.refresh(field)
    
    return fields


@pytest.fixture
def sample_review_tasks(db_session, sample_document, sample_parsed_fields):
    """Create sample review tasks for testing."""
    tasks = []
    
    for field in sample_parsed_fields:
        if field.confidence < 0.75:
            task = ReviewTask(
                document_id=sample_document.id,
                field_name=field.field_name,
                extracted_value=field.field_value,
                confidence=field.confidence,
                status=ReviewTaskStatus.PENDING,
            )
            db_session.add(task)
            tasks.append(task)
    
    db_session.commit()
    
    for task in tasks:
        db_session.refresh(task)
    
    return tasks


@pytest.fixture
def review_service(db_session):
    """Create a ReviewTaskService instance for testing."""
    return ReviewTaskService(db=db_session, retrain_threshold=5)


class TestReviewTaskServiceSummary:
    """Tests for get_summary method."""
    
    def test_get_summary_empty(self, review_service):
        """Summary should show zeros when no tasks exist."""
        summary = review_service.get_summary()
        
        assert isinstance(summary, ReviewTaskSummary)
        assert summary.total_pending == 0
        assert summary.total_in_progress == 0
        assert summary.total_completed == 0
        assert summary.total_rejected == 0
    
    def test_get_summary_with_tasks(self, review_service, sample_review_tasks):
        """Summary should reflect task counts correctly."""
        summary = review_service.get_summary()
        
        assert summary.total_pending == len(sample_review_tasks)
        assert summary.total_in_progress == 0
        assert summary.total_completed == 0
    
    def test_retrain_threshold(self, review_service):
        """Summary should include retrain threshold info."""
        summary = review_service.get_summary()
        
        assert summary.retrain_threshold == 5
        assert summary.retrain_needed == False


class TestListLowConfidenceFields:
    """Tests for list_low_confidence_fields method."""
    
    def test_list_low_confidence_fields(self, review_service, sample_parsed_fields):
        """Should return fields below confidence threshold."""
        fields = review_service.list_low_confidence_fields(confidence_threshold=0.75)
        
        # Should find 3 fields with confidence < 0.75
        assert len(fields) == 3
        
        # Should be ordered by confidence ascending
        confidences = [f["confidence"] for f in fields]
        assert confidences == sorted(confidences)
    
    def test_list_low_confidence_fields_custom_threshold(self, review_service, sample_parsed_fields):
        """Should respect custom confidence threshold."""
        fields = review_service.list_low_confidence_fields(confidence_threshold=0.50)
        
        # Only 1 field has confidence < 0.50
        assert len(fields) == 1
        assert fields[0]["field_name"] == "bill_date"
    
    def test_list_low_confidence_fields_respects_limit(self, review_service, sample_parsed_fields):
        """Should respect limit parameter."""
        fields = review_service.list_low_confidence_fields(
            confidence_threshold=0.75,
            limit=2,
        )
        
        assert len(fields) == 2


class TestListPendingTasks:
    """Tests for list_pending_tasks method."""
    
    def test_list_pending_tasks(self, review_service, sample_review_tasks):
        """Should return pending review tasks."""
        tasks = review_service.list_pending_tasks()
        
        assert len(tasks) == len(sample_review_tasks)
        assert all(isinstance(t, ReviewTaskDetail) for t in tasks)
    
    def test_list_pending_tasks_filter_by_document(
        self, review_service, sample_review_tasks, sample_document
    ):
        """Should filter by document ID."""
        tasks = review_service.list_pending_tasks(document_id=sample_document.id)
        
        assert len(tasks) == len(sample_review_tasks)
        assert all(t.document_id == sample_document.id for t in tasks)
    
    def test_list_pending_tasks_filter_by_field_name(
        self, review_service, sample_review_tasks
    ):
        """Should filter by field name."""
        tasks = review_service.list_pending_tasks(field_name="patient_name")
        
        assert len(tasks) == 1
        assert tasks[0].field_name == "patient_name"
    
    def test_list_pending_tasks_pagination(self, review_service, sample_review_tasks):
        """Should support pagination."""
        tasks_page1 = review_service.list_pending_tasks(limit=2, offset=0)
        tasks_page2 = review_service.list_pending_tasks(limit=2, offset=2)
        
        assert len(tasks_page1) == 2
        assert len(tasks_page2) == 1  # Only 3 tasks total
        
        # No overlap
        page1_ids = {t.id for t in tasks_page1}
        page2_ids = {t.id for t in tasks_page2}
        assert page1_ids.isdisjoint(page2_ids)


class TestGetTask:
    """Tests for get_task method."""
    
    def test_get_task_success(self, review_service, sample_review_tasks):
        """Should return task details."""
        task_id = sample_review_tasks[0].id
        task = review_service.get_task(task_id)
        
        assert isinstance(task, ReviewTaskDetail)
        assert task.id == task_id
    
    def test_get_task_not_found(self, review_service):
        """Should raise error for non-existent task."""
        with pytest.raises(TaskNotFoundError):
            review_service.get_task(99999)


class TestAssignTask:
    """Tests for assign_task method."""
    
    def test_assign_task_success(
        self, review_service, sample_review_tasks, sample_user
    ):
        """Should assign task to user."""
        task_id = sample_review_tasks[0].id
        
        result = review_service.assign_task(
            task_id=task_id,
            user_id=sample_user.id,
            assigner_id=sample_user.id,
        )
        
        assert result.assigned_to_user_id == sample_user.id
        assert result.status == ReviewTaskStatus.IN_PROGRESS.value
    
    def test_assign_task_not_found(self, review_service, sample_user):
        """Should raise error for non-existent task."""
        with pytest.raises(TaskNotFoundError):
            review_service.assign_task(
                task_id=99999,
                user_id=sample_user.id,
                assigner_id=sample_user.id,
            )


class TestSubmitCorrection:
    """Tests for submit_correction method."""
    
    def test_submit_correction_approve(
        self, review_service, sample_review_tasks, sample_user, db_session
    ):
        """Should approve correction and update parsed field."""
        task = sample_review_tasks[0]
        
        result = review_service.submit_correction(
            task_id=task.id,
            corrected_value="Jane Smith",
            reviewer_id=sample_user.id,
            reviewer_notes="Fixed typo",
            approve=True,
        )
        
        assert result.success == True
        assert result.corrected_value == "Jane Smith"
        
        # Verify task status updated
        updated_task = review_service.get_task(task.id)
        assert updated_task.status == ReviewTaskStatus.COMPLETED.value
        
        # Verify parsed field updated
        parsed_field = db_session.query(ParsedField).filter(
            ParsedField.document_id == task.document_id,
            ParsedField.field_name == task.field_name,
        ).first()
        
        assert parsed_field.field_value == "Jane Smith"
        assert parsed_field.confidence == 1.0
        assert parsed_field.source == "human_review"
    
    def test_submit_correction_reject(
        self, review_service, sample_review_tasks, sample_user
    ):
        """Should reject correction without updating parsed field."""
        task = sample_review_tasks[0]
        original_value = task.extracted_value
        
        result = review_service.submit_correction(
            task_id=task.id,
            corrected_value="rejected_value",
            reviewer_id=sample_user.id,
            approve=False,
        )
        
        # Task should be rejected
        updated_task = review_service.get_task(task.id)
        assert updated_task.status == ReviewTaskStatus.REJECTED.value
    
    def test_submit_correction_already_completed(
        self, review_service, sample_review_tasks, sample_user
    ):
        """Should raise error for already completed task."""
        task = sample_review_tasks[0]
        
        # Complete the task first
        review_service.submit_correction(
            task_id=task.id,
            corrected_value="value1",
            reviewer_id=sample_user.id,
            approve=True,
        )
        
        # Try to submit again
        with pytest.raises(TaskAlreadyCompletedError):
            review_service.submit_correction(
                task_id=task.id,
                corrected_value="value2",
                reviewer_id=sample_user.id,
                approve=True,
            )
    
    def test_submit_correction_triggers_retrain(
        self, db_session, sample_document, sample_user
    ):
        """Should trigger retraining when threshold reached."""
        retrain_callback = MagicMock()
        
        service = ReviewTaskService(
            db=db_session,
            retrain_threshold=2,
            retrain_callback=retrain_callback,
        )
        
        # Create review tasks
        for i in range(3):
            field = ParsedField(
                document_id=sample_document.id,
                field_name=f"field_{i}",
                field_value=f"value_{i}",
                confidence=0.5,
                source="test",
            )
            db_session.add(field)
            
            task = ReviewTask(
                document_id=sample_document.id,
                field_name=f"field_{i}",
                extracted_value=f"value_{i}",
                confidence=0.5,
                status=ReviewTaskStatus.PENDING,
            )
            db_session.add(task)
        
        db_session.commit()
        
        # Get tasks
        tasks = service.list_pending_tasks()
        
        # Submit corrections
        for i, task in enumerate(tasks):
            result = service.submit_correction(
                task_id=task.id,
                corrected_value=f"corrected_{i}",
                reviewer_id=sample_user.id,
                approve=True,
            )
            
            # Retrain should be triggered after 2nd correction
            if i >= 1:
                assert retrain_callback.called


class TestBulkApprove:
    """Tests for bulk_approve method."""
    
    def test_bulk_approve_success(
        self, review_service, sample_review_tasks, sample_user
    ):
        """Should bulk approve multiple tasks."""
        task_ids = [t.id for t in sample_review_tasks[:2]]
        
        results = review_service.bulk_approve(
            task_ids=task_ids,
            reviewer_id=sample_user.id,
        )
        
        assert len(results) == 2
        assert all(r.success for r in results)
    
    def test_bulk_approve_partial_failure(
        self, review_service, sample_review_tasks, sample_user
    ):
        """Should handle partial failures in bulk approve."""
        task_ids = [sample_review_tasks[0].id, 99999]  # One valid, one invalid
        
        results = review_service.bulk_approve(
            task_ids=task_ids,
            reviewer_id=sample_user.id,
        )
        
        assert len(results) == 2
        assert results[0].success == True
        assert results[1].success == False


class TestRejectTask:
    """Tests for reject_task method."""
    
    def test_reject_task_success(
        self, review_service, sample_review_tasks, sample_user
    ):
        """Should reject task with reason."""
        task_id = sample_review_tasks[0].id
        
        result = review_service.reject_task(
            task_id=task_id,
            reviewer_id=sample_user.id,
            reason="Document is unreadable",
        )
        
        assert result.status == ReviewTaskStatus.REJECTED.value
        assert "Rejected: Document is unreadable" in result.reviewer_notes


class TestCreateReviewTask:
    """Tests for create_review_task method."""
    
    def test_create_review_task(self, review_service, sample_document):
        """Should create a new review task."""
        task = review_service.create_review_task(
            document_id=sample_document.id,
            field_name="new_field",
            extracted_value="extracted_value",
            confidence=0.45,
        )
        
        assert task.id is not None
        assert task.document_id == sample_document.id
        assert task.field_name == "new_field"
        assert task.confidence == 0.45
        assert task.status == ReviewTaskStatus.PENDING


class TestGetCorrectionHistory:
    """Tests for get_correction_history method."""
    
    def test_get_correction_history(
        self, review_service, sample_review_tasks, sample_user
    ):
        """Should return completed corrections."""
        # Complete some tasks
        for task in sample_review_tasks[:2]:
            review_service.submit_correction(
                task_id=task.id,
                corrected_value=f"corrected_{task.field_name}",
                reviewer_id=sample_user.id,
                approve=True,
            )
        
        history = review_service.get_correction_history()
        
        assert len(history) == 2
        assert all("corrected_value" in h for h in history)
    
    def test_get_correction_history_filter_by_field(
        self, review_service, sample_review_tasks, sample_user
    ):
        """Should filter by field name."""
        # Complete tasks
        for task in sample_review_tasks:
            review_service.submit_correction(
                task_id=task.id,
                corrected_value=f"corrected_{task.field_name}",
                reviewer_id=sample_user.id,
                approve=True,
            )
        
        history = review_service.get_correction_history(field_name="patient_name")
        
        assert len(history) == 1
        assert history[0]["field_name"] == "patient_name"


class TestGetTrainingData:
    """Tests for get_training_data method."""
    
    def test_get_training_data(
        self, review_service, sample_review_tasks, sample_user
    ):
        """Should export training data format."""
        # Complete tasks
        for task in sample_review_tasks:
            review_service.submit_correction(
                task_id=task.id,
                corrected_value=f"corrected_{task.field_name}",
                reviewer_id=sample_user.id,
                approve=True,
            )
        
        training_data = review_service.get_training_data()
        
        assert len(training_data) == len(sample_review_tasks)
        
        # Check format
        for sample in training_data:
            assert "field_name" in sample
            assert "extracted_value" in sample
            assert "correct_value" in sample
            assert "original_confidence" in sample

