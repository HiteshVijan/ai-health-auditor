"""
Unit tests for data retention service.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock

from app.services.data_retention import (
    DataRetentionService,
    DeletionResult,
    DocumentNotFoundError,
    PermissionDeniedError,
    DataRetentionError,
)
from app.models.document import Document, DocumentStatus
from app.models.deletion_log import DeletionLog, DeletionReason, DeletionStatus
from app.models.parsed_field import ParsedField
from app.models.review_task import ReviewTask
from app.models.user import User, UserRole


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.delete.return_value = 0
    return db


@pytest.fixture
def mock_storage():
    """Create a mock storage service."""
    storage = MagicMock()
    storage.delete_file.return_value = True
    return storage


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = 1
    user.username = "testuser"
    user.role = UserRole.USER
    return user


@pytest.fixture
def mock_admin():
    """Create a mock admin user."""
    admin = MagicMock(spec=User)
    admin.id = 2
    admin.username = "admin"
    admin.role = UserRole.ADMIN
    return admin


@pytest.fixture
def mock_document():
    """Create a mock document."""
    doc = MagicMock(spec=Document)
    doc.id = 100
    doc.user_id = 1
    doc.filename = "test_bill.pdf"
    doc.s3_key = "documents/user_1/test_bill.pdf"
    doc.status = DocumentStatus.UPLOADED
    return doc


@pytest.fixture
def retention_service(mock_db, mock_storage):
    """Create a data retention service instance."""
    return DataRetentionService(db=mock_db, storage_service=mock_storage)


class TestCanDeleteDocument:
    """Tests for permission checking."""
    
    def test_owner_can_delete_own_document(
        self, retention_service, mock_user, mock_document
    ):
        """Owner should be able to delete their own document."""
        mock_document.user_id = mock_user.id
        
        result = retention_service.can_delete_document(mock_user, mock_document)
        
        assert result is True
    
    def test_user_cannot_delete_others_document(
        self, retention_service, mock_user, mock_document
    ):
        """User should not be able to delete another user's document."""
        mock_document.user_id = 999  # Different user
        
        result = retention_service.can_delete_document(mock_user, mock_document)
        
        assert result is False
    
    def test_admin_can_delete_any_document(
        self, retention_service, mock_admin, mock_document
    ):
        """Admin should be able to delete any document."""
        mock_document.user_id = 999  # Different user
        
        result = retention_service.can_delete_document(mock_admin, mock_document)
        
        assert result is True


class TestDeleteDocument:
    """Tests for document deletion."""
    
    def test_delete_document_not_found(
        self, retention_service, mock_user, mock_db
    ):
        """Should raise error if document doesn't exist."""
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(DocumentNotFoundError):
            retention_service.delete_document(
                document_id=999,
                user=mock_user,
            )
    
    def test_delete_document_permission_denied(
        self, retention_service, mock_user, mock_document, mock_db
    ):
        """Should raise error if user lacks permission."""
        mock_document.user_id = 999  # Different user
        mock_db.query.return_value.filter.return_value.first.return_value = mock_document
        
        with pytest.raises(PermissionDeniedError):
            retention_service.delete_document(
                document_id=mock_document.id,
                user=mock_user,
            )
    
    def test_delete_document_success(
        self, retention_service, mock_user, mock_document, mock_db, mock_storage
    ):
        """Should successfully delete document and all related data."""
        mock_document.user_id = mock_user.id
        mock_db.query.return_value.filter.return_value.first.return_value = mock_document
        mock_db.query.return_value.filter.return_value.delete.return_value = 5
        
        # Mock Celery task cancellation
        with patch('backend.app.services.data_retention.DataRetentionService._cancel_celery_tasks') as mock_cancel:
            mock_cancel.return_value = True
            
            result = retention_service.delete_document(
                document_id=mock_document.id,
                user=mock_user,
                reason=DeletionReason.USER_REQUEST,
            )
        
        assert result.success is True
        assert result.document_id == mock_document.id
        assert result.deleted_components["database_record"] is True
        assert result.deleted_components["storage_file"] is True
        assert result.deleted_components["parsed_fields"] is True
        assert result.deleted_components["review_tasks"] is True
        
        # Verify storage deletion was called
        mock_storage.delete_file.assert_called_once_with(mock_document.s3_key)
        
        # Verify database operations
        mock_db.delete.assert_called_once_with(mock_document)
        mock_db.commit.assert_called()
    
    def test_delete_document_logs_deletion(
        self, retention_service, mock_user, mock_document, mock_db, mock_storage
    ):
        """Should create a deletion log entry."""
        mock_document.user_id = mock_user.id
        mock_db.query.return_value.filter.return_value.first.return_value = mock_document
        
        with patch('backend.app.services.data_retention.DataRetentionService._cancel_celery_tasks') as mock_cancel:
            mock_cancel.return_value = True
            
            retention_service.delete_document(
                document_id=mock_document.id,
                user=mock_user,
                reason=DeletionReason.USER_REQUEST,
                reason_details="User requested data deletion",
                request_ip="192.168.1.1",
            )
        
        # Verify deletion log was added
        add_calls = mock_db.add.call_args_list
        assert len(add_calls) >= 1
        
        # First add should be the deletion log
        deletion_log = add_calls[0][0][0]
        assert isinstance(deletion_log, DeletionLog)
        assert deletion_log.resource_type == "document"
        assert deletion_log.resource_id == mock_document.id
        assert deletion_log.deleted_by_user_id == mock_user.id
        assert deletion_log.reason == DeletionReason.USER_REQUEST
    
    def test_delete_document_no_s3_key(
        self, retention_service, mock_user, mock_document, mock_db, mock_storage
    ):
        """Should handle documents without S3 key."""
        mock_document.user_id = mock_user.id
        mock_document.s3_key = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_document
        
        with patch('backend.app.services.data_retention.DataRetentionService._cancel_celery_tasks') as mock_cancel:
            mock_cancel.return_value = True
            
            result = retention_service.delete_document(
                document_id=mock_document.id,
                user=mock_user,
            )
        
        assert result.success is True
        assert result.deleted_components["storage_file"] is True
        
        # S3 delete should not be called
        mock_storage.delete_file.assert_not_called()
    
    def test_delete_document_s3_failure_partial(
        self, retention_service, mock_user, mock_document, mock_db, mock_storage
    ):
        """Should continue with partial deletion if S3 fails."""
        mock_document.user_id = mock_user.id
        mock_db.query.return_value.filter.return_value.first.return_value = mock_document
        
        # Make S3 deletion fail
        mock_storage.delete_file.side_effect = Exception("S3 error")
        
        with patch('backend.app.services.data_retention.DataRetentionService._cancel_celery_tasks') as mock_cancel:
            mock_cancel.return_value = True
            
            result = retention_service.delete_document(
                document_id=mock_document.id,
                user=mock_user,
            )
        
        # Should still complete but with partial success
        assert result.deleted_components["storage_file"] is False
        assert result.deleted_components["database_record"] is True
        assert "S3 deletion failed" in result.error_message
    
    def test_delete_document_admin_can_delete_any(
        self, retention_service, mock_admin, mock_document, mock_db, mock_storage
    ):
        """Admin should be able to delete any user's document."""
        mock_document.user_id = 999  # Different user
        mock_db.query.return_value.filter.return_value.first.return_value = mock_document
        
        with patch('backend.app.services.data_retention.DataRetentionService._cancel_celery_tasks') as mock_cancel:
            mock_cancel.return_value = True
            
            result = retention_service.delete_document(
                document_id=mock_document.id,
                user=mock_admin,
                reason=DeletionReason.ADMIN_REQUEST,
            )
        
        assert result.success is True


class TestDeleteUserData:
    """Tests for full user data deletion."""
    
    def test_delete_user_data_success(
        self, retention_service, mock_user, mock_db, mock_storage
    ):
        """Should delete all documents for a user."""
        doc1 = MagicMock(spec=Document)
        doc1.id = 1
        doc1.user_id = mock_user.id
        doc1.s3_key = "doc1.pdf"
        
        doc2 = MagicMock(spec=Document)
        doc2.id = 2
        doc2.user_id = mock_user.id
        doc2.s3_key = "doc2.pdf"
        
        mock_db.query.return_value.filter.return_value.all.return_value = [doc1, doc2]
        mock_db.query.return_value.filter.return_value.first.side_effect = [doc1, doc2]
        
        with patch('backend.app.services.data_retention.DataRetentionService._cancel_celery_tasks') as mock_cancel:
            mock_cancel.return_value = True
            
            result = retention_service.delete_user_data(
                user_id=mock_user.id,
                requesting_user=mock_user,
                reason=DeletionReason.ACCOUNT_DELETION,
            )
        
        assert result["documents_deleted"] == 2
        assert result["documents_failed"] == 0
    
    def test_delete_user_data_permission_denied(
        self, retention_service, mock_user, mock_db
    ):
        """Should deny deletion of another user's data."""
        with pytest.raises(PermissionDeniedError):
            retention_service.delete_user_data(
                user_id=999,  # Different user
                requesting_user=mock_user,
            )
    
    def test_delete_user_data_admin_can_delete_any(
        self, retention_service, mock_admin, mock_db, mock_storage
    ):
        """Admin should be able to delete any user's data."""
        doc = MagicMock(spec=Document)
        doc.id = 1
        doc.user_id = 999
        doc.s3_key = "doc.pdf"
        
        mock_db.query.return_value.filter.return_value.all.return_value = [doc]
        mock_db.query.return_value.filter.return_value.first.return_value = doc
        
        with patch('backend.app.services.data_retention.DataRetentionService._cancel_celery_tasks') as mock_cancel:
            mock_cancel.return_value = True
            
            result = retention_service.delete_user_data(
                user_id=999,
                requesting_user=mock_admin,
                reason=DeletionReason.ADMIN_REQUEST,
            )
        
        assert result["documents_deleted"] == 1


class TestCancelCeleryTasks:
    """Tests for Celery task cancellation."""
    
    def test_cancel_celery_tasks_success(self, retention_service):
        """Should cancel pending Celery tasks."""
        mock_celery = MagicMock()
        mock_inspect = MagicMock()
        mock_inspect.active.return_value = {
            "worker1": [
                {
                    "id": "task-123",
                    "args": [100],
                    "kwargs": {},
                }
            ]
        }
        mock_inspect.scheduled.return_value = {}
        mock_inspect.reserved.return_value = {}
        mock_celery.control.inspect.return_value = mock_inspect
        
        with patch('backend.celery_app.celery.celery_app', mock_celery):
            result = retention_service._cancel_celery_tasks(document_id=100)
        
        assert result is True
        mock_celery.control.revoke.assert_called_once_with(
            "task-123",
            terminate=True,
        )
    
    def test_cancel_celery_tasks_handles_error(self, retention_service):
        """Should handle Celery errors gracefully."""
        with patch('backend.celery_app.celery.celery_app') as mock_celery:
            mock_celery.control.inspect.side_effect = Exception("Celery error")
            
            result = retention_service._cancel_celery_tasks(document_id=100)
        
        # Should return True (non-critical) even on error
        assert result is True


class TestGetDeletionLogs:
    """Tests for deletion log retrieval."""
    
    def test_get_deletion_logs_admin(
        self, retention_service, mock_admin, mock_db
    ):
        """Admin should see all deletion logs."""
        mock_log = MagicMock(spec=DeletionLog)
        mock_log.resource_type = "document"
        mock_log.resource_id = 100
        
        mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_log]
        
        logs = retention_service.get_deletion_logs(user=mock_admin)
        
        assert len(logs) == 1
    
    def test_get_deletion_logs_user_filtered(
        self, retention_service, mock_user, mock_db
    ):
        """Non-admin should only see own deletion logs."""
        mock_log = MagicMock(spec=DeletionLog)
        mock_log.deleted_by_user_id = mock_user.id
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [mock_log]
        
        logs = retention_service.get_deletion_logs(user=mock_user)
        
        # Verify filter was applied
        mock_db.query.return_value.filter.assert_called()


class TestDeletionResult:
    """Tests for DeletionResult class."""
    
    def test_deletion_result_to_dict(self):
        """Should convert result to dictionary."""
        result = DeletionResult(
            success=True,
            document_id=100,
            deleted_components={
                "database_record": True,
                "storage_file": True,
            },
            error_message=None,
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["document_id"] == 100
        assert result_dict["deleted_components"]["database_record"] is True
        assert result_dict["error_message"] is None
    
    def test_deletion_result_with_error(self):
        """Should include error message."""
        result = DeletionResult(
            success=False,
            document_id=100,
            deleted_components={"database_record": False},
            error_message="Deletion failed",
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is False
        assert result_dict["error_message"] == "Deletion failed"


class TestDeletionReasons:
    """Tests for different deletion reasons."""
    
    def test_user_request_deletion(
        self, retention_service, mock_user, mock_document, mock_db, mock_storage
    ):
        """Should log user-requested deletion."""
        mock_document.user_id = mock_user.id
        mock_db.query.return_value.filter.return_value.first.return_value = mock_document
        
        with patch('backend.app.services.data_retention.DataRetentionService._cancel_celery_tasks') as mock_cancel:
            mock_cancel.return_value = True
            
            retention_service.delete_document(
                document_id=mock_document.id,
                user=mock_user,
                reason=DeletionReason.USER_REQUEST,
                reason_details="GDPR Article 17 request",
            )
        
        # Verify deletion log has correct reason
        add_calls = mock_db.add.call_args_list
        deletion_log = add_calls[0][0][0]
        assert deletion_log.reason == DeletionReason.USER_REQUEST
        assert deletion_log.reason_details == "GDPR Article 17 request"
    
    def test_retention_policy_deletion(
        self, retention_service, mock_admin, mock_document, mock_db, mock_storage
    ):
        """Should log retention policy deletion."""
        mock_document.user_id = 999
        mock_db.query.return_value.filter.return_value.first.return_value = mock_document
        
        with patch('backend.app.services.data_retention.DataRetentionService._cancel_celery_tasks') as mock_cancel:
            mock_cancel.return_value = True
            
            retention_service.delete_document(
                document_id=mock_document.id,
                user=mock_admin,
                reason=DeletionReason.RETENTION_POLICY,
                reason_details="Data older than 7 years",
            )
        
        add_calls = mock_db.add.call_args_list
        deletion_log = add_calls[0][0][0]
        assert deletion_log.reason == DeletionReason.RETENTION_POLICY

