"""
Celery Tasks
=============
Defines async tasks for log processing.
"""
try:
    from .celery_app import celery_app
except ImportError:
    from celery_app import celery_app
from backend.services.job_service import JobService, get_job_service
from backend.auth import TokenManager
import redis as redis_lib
from backend.utils.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

# OAuth token manager
try:
    redis_client = redis_lib.Redis.from_url(settings.celery_broker_url)
    token_manager = TokenManager(redis_client, settings.secret_key)
except Exception as e:
    logger.warning(f"Token manager unavailable: {e}")
    token_manager = None


@celery_app.task(bind=True)
def process_log_task(
    self,
    zip_bytes: bytes,
    py_files: dict[str, bytes],
    compact: bool,
    user_id: str | None = None,
    provider: str | None = None,
    api_key: str | None = None,
    language: str = "en",
):
    """Async task to process Spark log ZIP and return results.
    
    Retrieves LLM API key either from:
    1. OAuth token (if user_id + provider supplied)
    2. BYOK api_key (legacy fallback)
    """
    logger.info(f"Starting task {self.request.id} with zip_bytes size: {len(zip_bytes)}")
    logger.info(f"Parameters: compact={compact}, user_id={user_id}, provider={provider}, api_key={'***' if api_key else None}")
    
    service = get_job_service()
    
    # Resolve API key: prefer OAuth token
    resolved_api_key = api_key
    resolved_provider = provider
    
    if user_id and provider and token_manager:
        try:
            token_data = token_manager.get_token(user_id, provider)
            if token_data:
                resolved_api_key = token_data.get("access_token")
                logger.info(f"Using OAuth token for {user_id}:{provider}")
        except Exception as e:
            logger.error(f"Failed to retrieve OAuth token: {e}")
    
    result = service.process(
        zip_bytes=zip_bytes,
        py_files=py_files,
        compact=compact,
        llm_provider=resolved_provider,
        api_key=resolved_api_key,
        language=language,
    )
    
    logger.info(f"Task {self.request.id} completed. Summary: {result.summary is not None}, Report length: {len(result.reduced_report)}, Analysis length: {len(result.llm_analysis)}")
    
    return {
        "reduced_report": result.reduced_report,
        "llm_analysis": result.llm_analysis,
        "summary": result.summary.model_dump() if result.summary else None,
    }