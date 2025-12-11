"""
Review Tasks Service Module.

Manages human-in-the-loop review workflow for low-confidence parsed fields.
Allows admins to view, edit, and approve corrections to parsed document fields.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import and_, func, desc
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.parsed_field import ParsedField
from app.models.review_task import ReviewTask, ReviewTaskStatus
from app.models.user import User

logger = logging.getLogger(__name__)


class ReviewTaskError(Exception):
    """Base exception for review task errors."""
    pass


class TaskNotFoundError(ReviewTaskError):
    """Raised when a review task is not found."""
    pass


class TaskAlreadyCompletedError(ReviewTaskError):
    """Raised when attempting to modify a completed task."""
    pass


class UnauthorizedError(ReviewTaskError):
    """Raised when user doesn't have permission for the action."""
    pass


@dataclass
class ReviewTaskSummary:
    """Summary of review task statistics."""
    total_pending: int
    total_in_progress: int
    total_completed: int
    total_rejected: int
    corrections_since_last_retrain: int
    retrain_threshold: int
    retrain_needed: bool


@dataclass
class ReviewTaskDetail:
    """Detailed view of a review task."""
    id: int
    document_id: int
    document_name: str
    field_name: str
    extracted_value: Optional[str]
    corrected_value: Optional[str]
    confidence: float
    status: str
    assigned_to_user_id: Optional[int]
    assigned_to_username: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]
    reviewed_at: Optional[datetime]
    reviewer_notes: Optional[str]


@dataclass
class CorrectionResult:
    """Result of applying a correction."""
    task_id: int
    field_name: str
    original_value: Optional[str]
    corrected_value: str
    success: bool
    retrain_triggered: bool


class ReviewTaskService:
    """
    Service for managing review tasks and field corrections.
    
    Provides functionality to:
    - List and filter review tasks
    - Assign tasks to reviewers
    - Submit corrections
    - Track correction history
    - Trigger retraining when threshold is reached
    """
    
    # Default threshold for triggering retraining
    DEFAULT_RETRAIN_THRESHOLD = 100
    
    def __init__(
        self,
        db: Session,
        retrain_threshold: int = DEFAULT_RETRAIN_THRESHOLD,
        retrain_callback: Optional[callable] = None,
    ):
        """
        Initialize the review task service.
        
        Args:
            db: SQLAlchemy database session.
            retrain_threshold: Number of corrections before triggering retrain.
            retrain_callback: Optional callback function to trigger retraining.
        """
        self.db = db
        self.retrain_threshold = retrain_threshold
        self.retrain_callback = retrain_callback
        self._corrections_since_retrain = 0
    
    def get_summary(self) -> ReviewTaskSummary:
        """
        Get summary statistics for review tasks.
        
        Returns:
            ReviewTaskSummary with task counts and retrain status.
        """
        pending = self.db.query(func.count(ReviewTask.id)).filter(
            ReviewTask.status == ReviewTaskStatus.PENDING
        ).scalar() or 0
        
        in_progress = self.db.query(func.count(ReviewTask.id)).filter(
            ReviewTask.status == ReviewTaskStatus.IN_PROGRESS
        ).scalar() or 0
        
        completed = self.db.query(func.count(ReviewTask.id)).filter(
            ReviewTask.status == ReviewTaskStatus.COMPLETED
        ).scalar() or 0
        
        rejected = self.db.query(func.count(ReviewTask.id)).filter(
            ReviewTask.status == ReviewTaskStatus.REJECTED
        ).scalar() or 0
        
        # Get corrections count since last retrain
        corrections_count = self._get_corrections_since_last_retrain()
        
        return ReviewTaskSummary(
            total_pending=pending,
            total_in_progress=in_progress,
            total_completed=completed,
            total_rejected=rejected,
            corrections_since_last_retrain=corrections_count,
            retrain_threshold=self.retrain_threshold,
            retrain_needed=corrections_count >= self.retrain_threshold,
        )
    
    def list_pending_tasks(
        self,
        confidence_threshold: float = 0.75,
        limit: int = 50,
        offset: int = 0,
        assigned_to_user_id: Optional[int] = None,
        document_id: Optional[int] = None,
        field_name: Optional[str] = None,
    ) -> List[ReviewTaskDetail]:
        """
        List pending review tasks with optional filters.
        
        Args:
            confidence_threshold: Maximum confidence to include.
            limit: Maximum number of results.
            offset: Pagination offset.
            assigned_to_user_id: Filter by assigned user.
            document_id: Filter by document.
            field_name: Filter by field name.
        
        Returns:
            List of ReviewTaskDetail objects.
        """
        query = self.db.query(
            ReviewTask,
            Document.file_name,
            User.username,
        ).join(
            Document, ReviewTask.document_id == Document.id
        ).outerjoin(
            User, ReviewTask.assigned_to_user_id == User.id
        ).filter(
            ReviewTask.status.in_([ReviewTaskStatus.PENDING, ReviewTaskStatus.IN_PROGRESS]),
            ReviewTask.confidence < confidence_threshold,
        )
        
        if assigned_to_user_id is not None:
            query = query.filter(ReviewTask.assigned_to_user_id == assigned_to_user_id)
        
        if document_id is not None:
            query = query.filter(ReviewTask.document_id == document_id)
        
        if field_name is not None:
            query = query.filter(ReviewTask.field_name == field_name)
        
        query = query.order_by(
            ReviewTask.confidence.asc(),  # Lowest confidence first
            ReviewTask.created_at.asc(),
        ).offset(offset).limit(limit)
        
        results = []
        for task, doc_name, username in query.all():
            results.append(ReviewTaskDetail(
                id=task.id,
                document_id=task.document_id,
                document_name=doc_name,
                field_name=task.field_name,
                extracted_value=task.extracted_value,
                corrected_value=task.corrected_value,
                confidence=task.confidence,
                status=task.status.value,
                assigned_to_user_id=task.assigned_to_user_id,
                assigned_to_username=username,
                created_at=task.created_at,
                updated_at=task.updated_at,
                reviewed_at=task.reviewed_at,
                reviewer_notes=task.reviewer_notes,
            ))
        
        logger.info(f"Retrieved {len(results)} pending review tasks")
        return results
    
    def list_low_confidence_fields(
        self,
        confidence_threshold: float = 0.75,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List all low-confidence parsed fields from the database.
        
        Args:
            confidence_threshold: Maximum confidence to include.
            limit: Maximum number of results.
        
        Returns:
            List of dictionaries with field details.
        """
        query = self.db.query(
            ParsedField,
            Document.file_name,
        ).join(
            Document, ParsedField.document_id == Document.id
        ).filter(
            ParsedField.confidence < confidence_threshold,
        ).order_by(
            ParsedField.confidence.asc(),
        ).limit(limit)
        
        results = []
        for field, doc_name in query.all():
            results.append({
                "field_id": field.id,
                "document_id": field.document_id,
                "document_name": doc_name,
                "field_name": field.field_name,
                "field_value": field.field_value,
                "confidence": field.confidence,
                "source": field.source,
                "created_at": field.created_at.isoformat() if field.created_at else None,
            })
        
        logger.info(f"Found {len(results)} low-confidence fields below threshold {confidence_threshold}")
        return results
    
    def get_task(self, task_id: int) -> ReviewTaskDetail:
        """
        Get a single review task by ID.
        
        Args:
            task_id: The task ID to retrieve.
        
        Returns:
            ReviewTaskDetail for the task.
        
        Raises:
            TaskNotFoundError: If task doesn't exist.
        """
        result = self.db.query(
            ReviewTask,
            Document.file_name,
            User.username,
        ).join(
            Document, ReviewTask.document_id == Document.id
        ).outerjoin(
            User, ReviewTask.assigned_to_user_id == User.id
        ).filter(
            ReviewTask.id == task_id
        ).first()
        
        if not result:
            raise TaskNotFoundError(f"Review task with ID {task_id} not found")
        
        task, doc_name, username = result
        
        return ReviewTaskDetail(
            id=task.id,
            document_id=task.document_id,
            document_name=doc_name,
            field_name=task.field_name,
            extracted_value=task.extracted_value,
            corrected_value=task.corrected_value,
            confidence=task.confidence,
            status=task.status.value,
            assigned_to_user_id=task.assigned_to_user_id,
            assigned_to_username=username,
            created_at=task.created_at,
            updated_at=task.updated_at,
            reviewed_at=task.reviewed_at,
            reviewer_notes=task.reviewer_notes,
        )
    
    def assign_task(
        self,
        task_id: int,
        user_id: int,
        assigner_id: int,
    ) -> ReviewTaskDetail:
        """
        Assign a review task to a user.
        
        Args:
            task_id: The task to assign.
            user_id: The user to assign to.
            assigner_id: The user making the assignment.
        
        Returns:
            Updated ReviewTaskDetail.
        
        Raises:
            TaskNotFoundError: If task doesn't exist.
            TaskAlreadyCompletedError: If task is already completed.
        """
        task = self.db.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        
        if not task:
            raise TaskNotFoundError(f"Review task with ID {task_id} not found")
        
        if task.status in [ReviewTaskStatus.COMPLETED, ReviewTaskStatus.REJECTED]:
            raise TaskAlreadyCompletedError(f"Task {task_id} is already {task.status.value}")
        
        task.assigned_to_user_id = user_id
        task.status = ReviewTaskStatus.IN_PROGRESS
        task.updated_at = datetime.utcnow()
        
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        
        logger.info(f"Task {task_id} assigned to user {user_id} by user {assigner_id}")
        
        return self.get_task(task_id)
    
    def submit_correction(
        self,
        task_id: int,
        corrected_value: str,
        reviewer_id: int,
        reviewer_notes: Optional[str] = None,
        approve: bool = True,
    ) -> CorrectionResult:
        """
        Submit a correction for a review task.
        
        Args:
            task_id: The task being corrected.
            corrected_value: The corrected field value.
            reviewer_id: The user submitting the correction.
            reviewer_notes: Optional notes about the correction.
            approve: Whether to approve (True) or reject (False) the correction.
        
        Returns:
            CorrectionResult with details of the operation.
        
        Raises:
            TaskNotFoundError: If task doesn't exist.
            TaskAlreadyCompletedError: If task is already completed.
        """
        task = self.db.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        
        if not task:
            raise TaskNotFoundError(f"Review task with ID {task_id} not found")
        
        if task.status in [ReviewTaskStatus.COMPLETED, ReviewTaskStatus.REJECTED]:
            raise TaskAlreadyCompletedError(f"Task {task_id} is already {task.status.value}")
        
        original_value = task.extracted_value
        
        # Update task
        task.corrected_value = corrected_value
        task.reviewer_notes = reviewer_notes
        task.reviewed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        task.status = ReviewTaskStatus.COMPLETED if approve else ReviewTaskStatus.REJECTED
        
        # Update the corresponding ParsedField if approved
        retrain_triggered = False
        if approve:
            parsed_field = self.db.query(ParsedField).filter(
                ParsedField.document_id == task.document_id,
                ParsedField.field_name == task.field_name,
            ).first()
            
            if parsed_field:
                parsed_field.field_value = corrected_value
                parsed_field.confidence = 1.0  # Human-verified
                parsed_field.source = "human_review"
                parsed_field.updated_at = datetime.utcnow()
                self.db.add(parsed_field)
                
                logger.info(
                    f"Updated ParsedField for document {task.document_id}, "
                    f"field '{task.field_name}': '{original_value}' -> '{corrected_value}'"
                )
            
            # Check if retraining should be triggered
            retrain_triggered = self._check_and_trigger_retrain()
        
        self.db.add(task)
        self.db.commit()
        
        logger.info(
            f"Correction submitted for task {task_id} by user {reviewer_id}: "
            f"{'approved' if approve else 'rejected'}"
        )
        
        return CorrectionResult(
            task_id=task_id,
            field_name=task.field_name,
            original_value=original_value,
            corrected_value=corrected_value,
            success=True,
            retrain_triggered=retrain_triggered,
        )
    
    def bulk_approve(
        self,
        task_ids: List[int],
        reviewer_id: int,
    ) -> List[CorrectionResult]:
        """
        Bulk approve tasks where extracted value is accepted as correct.
        
        Args:
            task_ids: List of task IDs to approve.
            reviewer_id: The user approving the tasks.
        
        Returns:
            List of CorrectionResult for each task.
        """
        results = []
        
        for task_id in task_ids:
            try:
                task = self.get_task(task_id)
                result = self.submit_correction(
                    task_id=task_id,
                    corrected_value=task.extracted_value or "",
                    reviewer_id=reviewer_id,
                    reviewer_notes="Bulk approved - extracted value accepted",
                    approve=True,
                )
                results.append(result)
            except (TaskNotFoundError, TaskAlreadyCompletedError) as e:
                logger.warning(f"Could not bulk approve task {task_id}: {e}")
                results.append(CorrectionResult(
                    task_id=task_id,
                    field_name="unknown",
                    original_value=None,
                    corrected_value="",
                    success=False,
                    retrain_triggered=False,
                ))
        
        logger.info(f"Bulk approved {sum(1 for r in results if r.success)}/{len(task_ids)} tasks")
        return results
    
    def reject_task(
        self,
        task_id: int,
        reviewer_id: int,
        reason: str,
    ) -> ReviewTaskDetail:
        """
        Reject a review task (e.g., document is unreadable).
        
        Args:
            task_id: The task to reject.
            reviewer_id: The user rejecting the task.
            reason: Reason for rejection.
        
        Returns:
            Updated ReviewTaskDetail.
        """
        task = self.db.query(ReviewTask).filter(ReviewTask.id == task_id).first()
        
        if not task:
            raise TaskNotFoundError(f"Review task with ID {task_id} not found")
        
        if task.status in [ReviewTaskStatus.COMPLETED, ReviewTaskStatus.REJECTED]:
            raise TaskAlreadyCompletedError(f"Task {task_id} is already {task.status.value}")
        
        task.status = ReviewTaskStatus.REJECTED
        task.reviewer_notes = f"Rejected: {reason}"
        task.reviewed_at = datetime.utcnow()
        task.updated_at = datetime.utcnow()
        
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        
        logger.info(f"Task {task_id} rejected by user {reviewer_id}: {reason}")
        
        return self.get_task(task_id)
    
    def create_review_task(
        self,
        document_id: int,
        field_name: str,
        extracted_value: Optional[str],
        confidence: float,
    ) -> ReviewTask:
        """
        Create a new review task for a low-confidence field.
        
        Args:
            document_id: The document containing the field.
            field_name: Name of the field to review.
            extracted_value: The extracted value to review.
            confidence: Confidence score of the extraction.
        
        Returns:
            The created ReviewTask.
        """
        task = ReviewTask(
            document_id=document_id,
            field_name=field_name,
            extracted_value=extracted_value,
            confidence=confidence,
            status=ReviewTaskStatus.PENDING,
        )
        
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        
        logger.info(
            f"Created review task {task.id} for document {document_id}, "
            f"field '{field_name}' (confidence: {confidence:.2f})"
        )
        
        return task
    
    def _get_corrections_since_last_retrain(self) -> int:
        """Get the count of completed corrections since last retraining."""
        # In a production system, you'd track the last retrain timestamp
        # For now, we count all completed tasks
        count = self.db.query(func.count(ReviewTask.id)).filter(
            ReviewTask.status == ReviewTaskStatus.COMPLETED,
        ).scalar() or 0
        
        return count
    
    def _check_and_trigger_retrain(self) -> bool:
        """
        Check if retraining threshold is reached and trigger if needed.
        
        Returns:
            True if retraining was triggered, False otherwise.
        """
        corrections_count = self._get_corrections_since_last_retrain()
        
        if corrections_count >= self.retrain_threshold:
            logger.info(
                f"Retraining threshold reached: {corrections_count}/{self.retrain_threshold} corrections"
            )
            
            if self.retrain_callback:
                try:
                    self.retrain_callback()
                    logger.info("Retraining pipeline triggered successfully")
                    return True
                except Exception as e:
                    logger.error(f"Failed to trigger retraining pipeline: {e}")
            else:
                logger.warning("Retraining threshold reached but no callback configured")
        
        return False
    
    def get_correction_history(
        self,
        document_id: Optional[int] = None,
        field_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Get history of completed corrections for analysis/retraining.
        
        Args:
            document_id: Optional filter by document.
            field_name: Optional filter by field name.
            limit: Maximum number of results.
        
        Returns:
            List of correction records.
        """
        query = self.db.query(
            ReviewTask,
            Document.file_name,
        ).join(
            Document, ReviewTask.document_id == Document.id
        ).filter(
            ReviewTask.status == ReviewTaskStatus.COMPLETED,
        )
        
        if document_id is not None:
            query = query.filter(ReviewTask.document_id == document_id)
        
        if field_name is not None:
            query = query.filter(ReviewTask.field_name == field_name)
        
        query = query.order_by(desc(ReviewTask.reviewed_at)).limit(limit)
        
        results = []
        for task, doc_name in query.all():
            results.append({
                "task_id": task.id,
                "document_id": task.document_id,
                "document_name": doc_name,
                "field_name": task.field_name,
                "original_value": task.extracted_value,
                "corrected_value": task.corrected_value,
                "original_confidence": task.confidence,
                "reviewed_at": task.reviewed_at.isoformat() if task.reviewed_at else None,
                "reviewer_notes": task.reviewer_notes,
            })
        
        return results
    
    def get_training_data(self) -> List[Dict[str, Any]]:
        """
        Export correction data formatted for model retraining.
        
        Returns:
            List of training samples with original and corrected values.
        """
        corrections = self.get_correction_history(limit=10000)
        
        training_data = []
        for correction in corrections:
            if correction["corrected_value"]:
                training_data.append({
                    "field_name": correction["field_name"],
                    "extracted_value": correction["original_value"],
                    "correct_value": correction["corrected_value"],
                    "original_confidence": correction["original_confidence"],
                })
        
        logger.info(f"Exported {len(training_data)} training samples")
        return training_data


def trigger_retraining_pipeline():
    """
    Placeholder function to trigger the ML retraining pipeline.
    
    In production, this would:
    - Export training data
    - Queue a Celery task for model retraining
    - Update model version tracking
    """
    from backend.celery_app.tasks.ml_tasks import retrain_model_task
    
    logger.info("Triggering ML model retraining pipeline...")
    retrain_model_task.delay()

