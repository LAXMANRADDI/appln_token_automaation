import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.database import AsyncSessionLocal
from app.token_manager import token_manager

logger = logging.getLogger("scheduler")

scheduler = AsyncIOScheduler()


async def _refresh_job() -> None:
    async with AsyncSessionLocal() as session:
        try:
            refreshed = await token_manager.check_and_refresh_if_needed(session)
            if refreshed:
                logger.info("Scheduled check: token was refreshed.")
            else:
                logger.debug("Scheduled check: token still valid, no refresh needed.")
        except Exception:
            logger.exception("Scheduled token refresh check failed.")


def start_scheduler() -> None:
    scheduler.add_job(
        _refresh_job,
        "interval",
        seconds=settings.poll_interval_seconds,
        id="token_refresh_check",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("Scheduler started, checking every %ss", settings.poll_interval_seconds)


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")
