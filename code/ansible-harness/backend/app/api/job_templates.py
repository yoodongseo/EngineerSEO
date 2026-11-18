
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
from uuid import UUID
from app.database import get_db
from app.scheduler import reload_scheduler_jobs
from app.models.job import JobTemplate
from app.schemas.job_templates import JobTemplateCreate, JobTemplateUpdate, JobTemplateResponse

router = APIRouter(prefix="/api/job_templates", tags=["job_templates"])

@router.get("/", response_model=List[JobTemplateResponse])
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(JobTemplate).order_by(JobTemplate.name))
    return result.scalars().all()

@router.post("/", response_model=JobTemplateResponse)
async def create_template(payload: JobTemplateCreate, db: AsyncSession = Depends(get_db)):
    template = JobTemplate(**payload.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)
    await reload_scheduler_jobs()
    return template

@router.put("/{template_id}", response_model=JobTemplateResponse)
async def update_template(template_id: UUID, payload: JobTemplateUpdate, db: AsyncSession = Depends(get_db)):
    template = await db.get(JobTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)
    
    await db.commit()
    await db.refresh(template)
    await reload_scheduler_jobs()
    return template

@router.delete("/{template_id}")
async def delete_template(template_id: UUID, db: AsyncSession = Depends(get_db)):
    template = await db.get(JobTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    await db.delete(template)
    await db.commit()
    await reload_scheduler_jobs()
    return {"success": True}

