"""
Data Retention Service.

Handles secure deletion of documents and related data for GDPR compliance.
Implements the "right to be forgotten" by removing data from all storage systems.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.parsed_field import ParsedField
from app.models.review_task import ReviewTask
from app.models.deletion_log import (
    DeletionLog,
    DeletionReason,
    DeletionStatus,
)
from app.models.user import User
from app.services.storage_service import StorageService
from app.core.rbac import Permission, has_permission, Role

logger = logging.getLogger(__name__)


class DataRetentionError(Exception):
    """Base exception for data retention errors."""
    pass


class DocumentNotFoundError(DataRetentionError):
    """Raised when document is not found."""
    pass


class PermissionDeniedError(DataRetentionError):
    """Raised when user lacks permission to delete."""
    pass


class DeletionResult:
    """Result of a deletion operation."""
    
    def __init__(
        self,
        success: bool,
        document_id: int,
        deleted_components: Dict[str, bool],
        error_message: Optional[str] = None,
    ):
        self.success = success
        self.document_id = document_id
        self.deleted_components = deleted_components
        self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "document_id": self.document_id,
            "deleted_components": self.deleted_components,
            "error_message": self.error_message,
        }


class DataRetentionService:
    """
    Service for managing data retention and deletion.
    
    Provides GDPR-compliant deletion of documents and all related data
    from database, object storage, and task queues.
    """
    
    def __init__(
        self,
        db: Session,
        storage_service: Optional[StorageService] = None,
    ):
        self.db = db
        self.storage_service = storage_service or StorageService()
    
    def can_delete_document(
        self,
        user: User,
        document: Document,
    ) -> bool:
        """
        Check if user has permission to delete a document.
        
        Args:
            user: The user attempting deletion.
            document: The document to delete.
        
        Returns:
            True if user can delete, False otherwise.
        """
        # Owner can always delete their own documents
        if document.user_id == user.id:
            user_role = Role(user.role.value) if user.role else Role.USER
            return has_permission(user_role, Permission.DOCUMENT_DELETE)
        
        # Admins can delete any document
        user_role = Role(user.role.value) if user.role else Role.USER
        return has_permission(user_role, Permission.DOCUMENT_DELETE_ALL)
    
    def delete_document(
        self,
        document_id: int,
        user: User,
        reason: DeletionReason = DeletionReason.USER_REQUEST,
        reason_details: Optional[str] = None,
        request_ip: Optional[str] = None,
    ) -> DeletionResult:
        """
        Delete a document and all related data.
        
        Implements the right to be forgotten by removing:
        - Document record from database
        - File from S3/MinIO
        - Parsed fields from database
        - Review tasks from database
        - Cancels pending Celery tasks
        
        Args:
            document_id: ID of document to delete.
            user: User requesting deletion.
            reason: Reason for deletion.
            reason_details: Additional details about deletion.
            request_ip: IP address of the request.
        
        Returns:
            DeletionResult with status and deleted components.
        
        Raises:
            DocumentNotFoundError: If document doesn't exist.
            PermissionDeniedError: If user lacks permission.
        """
        # Find the document
        document = self.db.query(Document).filter(
            Document.id == document_id
        ).first()
        
        if not document:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        
        # Check permissions
        if not self.can_delete_document(user, document):
            logger.warning(
                f"User {user.id} denied permission to delete document {document_id}"
            )
            raise PermissionDeniedError(
                "You don't have permission to delete this document"
            )
        
        # Create deletion log entry
        deletion_log = DeletionLog(
            resource_type="document",
            resource_id=document_id,
            resource_identifier=document.filename,
            deleted_by_user_id=user.id,
            deleted_by_username=user.username,
            deleted_by_role=user.role.value if user.role else "user",
            resource_owner_id=document.user_id,
            reason=reason,
            reason_details=reason_details,
            status=DeletionStatus.IN_PROGRESS,
            deletion_started_at=datetime.utcnow(),
            request_ip=request_ip,
        )
        self.db.add(deletion_log)
        self.db.flush()
        
        # Track deleted components
        deleted_components = {
            "database_record": False,
            "storage_file": False,
            "parsed_fields": False,
            "review_tasks": False,
            "celery_tasks": False,
        }
        
        error_messages = []
        
        try:
            # 1. Cancel pending Celery tasks
            deleted_components["celery_tasks"] = self._cancel_celery_tasks(
                document_id
            )
            
            # 2. Delete from S3/MinIO
            if document.s3_key:
                try:
                    self.storage_service.delete_file(document.s3_key)
                    deleted_components["storage_file"] = True
                    logger.info(f"Deleted S3 file: {document.s3_key}")
                except Exception as e:
                    error_messages.append(f"S3 deletion failed: {str(e)}")
                    logger.error(f"Failed to delete S3 file {document.s3_key}: {e}")
            else:
                deleted_components["storage_file"] = True  # No file to delete
            
            # 3. Delete review tasks
            review_task_count = self.db.query(ReviewTask).filter(
                ReviewTask.document_id == document_id
            ).delete()
            deleted_components["review_tasks"] = True
            logger.info(f"Deleted {review_task_count} review tasks for document {document_id}")
            
            # 4. Delete parsed fields
            parsed_field_count = self.db.query(ParsedField).filter(
                ParsedField.document_id == document_id
            ).delete()
            deleted_components["parsed_fields"] = True
            logger.info(f"Deleted {parsed_field_count} parsed fields for document {document_id}")
            
            # 5. Delete document record
            self.db.delete(document)
            deleted_components["database_record"] = True
            logger.info(f"Deleted document record: {document_id}")
            
            # Update deletion log
            deletion_log.deleted_components = deleted_components
            deletion_log.deletion_completed_at = datetime.utcnow()
            
            if all(deleted_components.values()):
                deletion_log.status = DeletionStatus.COMPLETED
            else:
                deletion_log.status = DeletionStatus.PARTIAL
                deletion_log.error_message = "; ".join(error_messages)
            
            self.db.commit()
            
            logger.info(
                f"Document {document_id} deleted by user {user.id} "
                f"(reason: {reason.value})"
            )
            
            return DeletionResult(
                success=all(deleted_components.values()),
                document_id=document_id,
                deleted_components=deleted_components,
                error_message="; ".join(error_messages) if error_messages else None,
            )
            
        except Exception as e:
            self.db.rollback()
            
            # Update deletion log with failure
            deletion_log.status = DeletionStatus.FAILED
            deletion_log.error_message = str(e)
            deletion_log.deleted_components = deleted_components
            deletion_log.deletion_completed_at = datetime.utcnow()
            
            # Commit just the log update
            try:
                self.db.add(deletion_log)
                self.db.commit()
            except Exception:
                pass
            
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise DataRetentionError(f"Deletion failed: {str(e)}")
    
    def _cancel_celery_tasks(self, document_id: int) -> bool:
        """
        Cancel any pending Celery tasks for a document.
        
        Args:
            document_id: Document ID whose tasks should be cancelled.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            from backend.celery_app.celery import celery_app
            
            # Get active tasks
            inspect = celery_app.control.inspect()
            active_tasks = inspect.active() or {}
            scheduled_tasks = inspect.scheduled() or {}
            reserved_tasks = inspect.reserved() or {}
            
            cancelled_count = 0
            
            # Check all task queues
            for worker_tasks in [active_tasks, scheduled_tasks, reserved_tasks]:
                for worker, tasks in worker_tasks.items():
                    for task in tasks:
                        task_args = task.get("args", [])
                        task_kwargs = task.get("kwargs", {})
                        
                        # Check if task is for this document
                        if (
                            document_id in task_args or
                            task_kwargs.get("document_id") == document_id
                        ):
                            task_id = task.get("id")
                            if task_id:
                                celery_app.control.revoke(
                                    task_id,
                                    terminate=True,
                                )
                                cancelled_count += 1
                                logger.info(f"Cancelled Celery task {task_id}")
            
            logger.info(f"Cancelled {cancelled_count} Celery tasks for document {document_id}")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to cancel Celery tasks: {e}")
            return True  # Non-critical, continue with deletion
    
    def get_deletion_logs(
        self,
        user: User,
        resource_type: Optional[str] = None,
        resource_owner_id: Optional[int] = None,
        limit: int = 100,
    ) -> List[DeletionLog]:
        """
        Get deletion logs for audit purposes.
        
        Args:
            user: User requesting logs.
            resource_type: Filter by resource type.
            resource_owner_id: Filter by resource owner.
            limit: Maximum number of logs to return.
        
        Returns:
            List of deletion log entries.
        """
        query = self.db.query(DeletionLog)
        
        # Non-admins can only see their own deletions
        user_role = Role(user.role.value) if user.role else Role.USER
        if not has_permission(user_role, Permission.SYSTEM_LOGS):
            query = query.filter(
                (DeletionLog.deleted_by_user_id == user.id) |
                (DeletionLog.resource_owner_id == user.id)
            )
        
        if resource_type:
            query = query.filter(DeletionLog.resource_type == resource_type)
        
        if resource_owner_id:
            query = query.filter(DeletionLog.resource_owner_id == resource_owner_id)
        
        return query.order_by(DeletionLog.created_at.desc()).limit(limit).all()
    
    def delete_user_data(
        self,
        user_id: int,
        requesting_user: User,
        reason: DeletionReason = DeletionReason.ACCOUNT_DELETION,
        reason_details: Optional[str] = None,
        request_ip: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Delete all data for a user (full account deletion).
        
        Args:
            user_id: ID of user whose data should be deleted.
            requesting_user: User making the deletion request.
            reason: Reason for deletion.
            reason_details: Additional details.
            request_ip: Request IP address.
        
        Returns:
            Summary of deleted data.
        """
        # Check permissions
        user_role = Role(requesting_user.role.value) if requesting_user.role else Role.USER
        
        if user_id != requesting_user.id:
            if not has_permission(user_role, Permission.USER_DELETE):
                raise PermissionDeniedError(
                    "You don't have permission to delete this user's data"
                )
        
        # Get all documents for user
        documents = self.db.query(Document).filter(
            Document.user_id == user_id
        ).all()
        
        results = {
            "documents_deleted": 0,
            "documents_failed": 0,
            "errors": [],
        }
        
        # Delete each document
        for document in documents:
            try:
                self.delete_document(
                    document_id=document.id,
                    user=requesting_user,
                    reason=reason,
                    reason_details=reason_details,
                    request_ip=request_ip,
                )
                results["documents_deleted"] += 1
            except Exception as e:
                results["documents_failed"] += 1
                results["errors"].append(f"Document {document.id}: {str(e)}")
        
        logger.info(
            f"User data deletion for user {user_id}: "
            f"{results['documents_deleted']} deleted, "
            f"{results['documents_failed']} failed"
        )
        
        return results

