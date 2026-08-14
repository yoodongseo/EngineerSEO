
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.database import async_session
from app.models.job import JobTemplate
from sqlalchemy import select
import httpx

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

async def execute_template_job(template_id):
    logger.info(f"Executing scheduled template job {template_id}")
    # Make an internal API call or use service layer to trigger job
    async with async_session() as db:
        template = await db.get(JobTemplate, template_id)
        if not template or not template.is_active:
            return
        
        # Call the internal run endpoint using httpx
        payload = {
            "project": template.project,
            "playbook": template.playbook,
            "inventory_id": str(template.inventory_id) if template.inventory_id else None,
            "extra_vars": template.extra_vars,
            "target_scope": template.target_scope,
            "target_group_name": template.target_group_name,
            "target_host_name": template.target_host_name
        }
        async with httpx.AsyncClient() as client:
            try:
                # Replace with actual backend port if needed, 8000 is internal
                res = await client.post("http://127.0.0.1:8000/api/jobs/run", json=payload)
                res.raise_for_status()
                logger.info(f"Successfully scheduled job from template {template_id}")
            except Exception as e:
                logger.error(f"Failed to run template {template_id}: {e}")

async def reload_scheduler_jobs():
    scheduler.remove_all_jobs()
    async with async_session() as db:
        result = await db.execute(select(JobTemplate).where(JobTemplate.is_active == 1, JobTemplate.cron_expression.isnot(None)))
        templates = result.scalars().all()
        for t in templates:
            if t.cron_expression:
                try:
                    scheduler.add_job(
                        execute_template_job,
                        CronTrigger.from_crontab(t.cron_expression),
                        args=[t.id],
                        id=str(t.id),
                        replace_existing=True
                    )
                    logger.info(f"Loaded cron job for template {t.id} with expression {t.cron_expression}")
                except Exception as e:
                    logger.error(f"Invalid cron expression for template {t.id}: {t.cron_expression}")

async def start_scheduler():
    await reload_scheduler_jobs()
    scheduler.start()
    logger.info("APScheduler started")

