"""Use case for triggering extraction in the background with retry and dead-letter support."""
import os
import traceback
from uuid import UUID

from ...infrastructure.persistence.database import Database
from ...infrastructure.persistence.repositories import (
    DocumentRepository,
    ExtractionRepository,
    AuditTrailRepository,
)
from ...infrastructure.external.ocr.base import OCRService
from ...infrastructure.external.llm.base import LLMService
from ...infrastructure.external.storage.base import StorageService
from ...infrastructure.error_handling.error_categorizer import ErrorCategorizer
from ...infrastructure.error_handling.retry import retry_with_backoff, PermanentError
from ...infrastructure.messaging.redis_queue import RedisQueue
from ...infrastructure.error_handling.dead_letter_queue import DeadLetterQueue
from ...domain.services.document_type_classifier import DocumentTypeClassifier
from .extract_fields import ExtractFieldsUseCase
from ...infrastructure.monitoring.logging import get_logger

logger = get_logger("sortex.application.trigger_extraction")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
MAX_RETRIES = int(os.getenv("EXTRACTION_MAX_RETRIES", "3"))


class TriggerExtractionUseCase:
    """Runs ExtractFieldsUseCase in a dedicated session with retry and DLQ support."""

    def __init__(
        self,
        database: Database,
        storage_service: StorageService,
        ocr_service: OCRService,
        llm_service: LLMService,
        document_type_classifier: DocumentTypeClassifier,
    ):
        self.database = database
        self.storage_service = storage_service
        self.ocr_service = ocr_service
        self.llm_service = llm_service
        self.document_type_classifier = document_type_classifier

    def execute(self, document_id: UUID) -> None:
        """Run extraction with automatic retry for transient failures."""

        @retry_with_backoff(max_retries=MAX_RETRIES, initial_delay=2.0, max_delay=30.0)
        def _run_extraction() -> None:
            session = self.database.get_session()
            try:
                document_repo = DocumentRepository(session)
                extraction_repo = ExtractionRepository(session)
                audit_repo = AuditTrailRepository(session)
                extract_uc = ExtractFieldsUseCase(
                    document_repository=document_repo,
                    extraction_repository=extraction_repo,
                    audit_trail_repository=audit_repo,
                    ocr_service=self.ocr_service,
                    llm_service=self.llm_service,
                    storage_service=self.storage_service,
                    document_type_classifier=self.document_type_classifier,
                )
                extract_uc.execute(document_id)
                session.commit()
                logger.info("Extraction completed", document_id=str(document_id))
            except Exception as e:
                session.rollback()
                # Categorise the error so the retry decorator knows whether to retry
                is_retryable = ErrorCategorizer.should_retry(e)
                if not is_retryable:
                    raise PermanentError(str(e)) from e
                logger.warning(
                    "Extraction attempt failed (will retry)",
                    error=str(e),
                    error_type=type(e).__name__,
                    document_id=str(document_id),
                )
                raise  # let retry_with_backoff handle it
            finally:
                session.close()

        try:
            _run_extraction()
        except Exception as e:
            logger.error(
                "Extraction failed after retries — sending to DLQ",
                error=str(e),
                error_type=type(e).__name__,
                document_id=str(document_id),
                traceback=traceback.format_exc(),
            )
            self._send_to_dlq(document_id, e)

    def _send_to_dlq(self, document_id: UUID, error: Exception) -> None:
        """Best-effort enqueue to the dead-letter queue."""
        try:
            redis_queue = RedisQueue(REDIS_URL)
            dlq = DeadLetterQueue(redis_queue)
            dlq.enqueue_failed_job(
                original_queue="extraction",
                job_data={"document_id": str(document_id)},
                error_message=str(error),
                retry_count=MAX_RETRIES,
            )
            logger.info("Document sent to DLQ", document_id=str(document_id))
        except Exception as dlq_error:
            logger.error(
                "Failed to enqueue to DLQ",
                error=str(dlq_error),
                document_id=str(document_id),
            )
