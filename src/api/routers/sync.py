"""
Sync and workflow endpoints
Handles data synchronization between systems
"""
from typing import Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.database import get_db
from src.db import crud, schemas, models
from src.core.security import get_current_user
from src.utils.logger import logger

router = APIRouter()


@router.post(
    "/workflows/run",
    response_model=schemas.WorkflowTriggerResponse,
    status_code=status.HTTP_202_ACCEPTED
)
async def trigger_workflow(
    workflow_request: schemas.WorkflowTriggerRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Trigger a data sync workflow between systems

    This endpoint creates a job and starts a workflow to sync data
    from source to target system.
    """
    logger.info(
        f"Triggering workflow: {workflow_request.workflow_type} - "
        f"{workflow_request.source_system} -> {workflow_request.target_system}"
    )

    try:
        # Create a job record
        job_data = schemas.JobCreate(
            job_type=workflow_request.workflow_type,
            source_system=workflow_request.source_system,
            target_system=workflow_request.target_system,
            entity_type=workflow_request.entity_type,
            config=workflow_request.config
        )

        db_job = await crud.JobCRUD.create(db, job_data)

        # Generate workflow ID (in production, this would be Temporal workflow ID)
        workflow_id = f"workflow_{uuid4().hex[:12]}"

        # Update job with workflow ID
        await crud.JobCRUD.update(
            db,
            db_job.id,
            schemas.JobUpdate(status=models.JobStatus.PENDING)
        )

        # TODO: Start Temporal workflow here
        # await temporal_client.start_workflow(...)

        logger.info(f"Workflow triggered: {workflow_id} for job {db_job.id}")

        return {
            "job_id": db_job.id,
            "workflow_id": workflow_id,
            "status": "pending",
            "message": f"Workflow {workflow_request.workflow_type} has been queued"
        }

    except Exception as e:
        logger.error(f"Error triggering workflow: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error triggering workflow: {str(e)}"
        )


@router.get("/jobs/{job_id}", response_model=schemas.JobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get job details by ID
    """
    job = await crud.JobCRUD.get(db, job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    return job


@router.get("/jobs", response_model=schemas.JobList)
async def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List jobs with pagination and filtering

    Query parameters:
    - page: Page number (starts at 1)
    - page_size: Number of items per page
    - status: Filter by job status
    - job_type: Filter by job type
    """
    skip = (page - 1) * page_size

    jobs = await crud.JobCRUD.get_multi(
        db,
        skip=skip,
        limit=page_size,
        status=status,
        job_type=job_type
    )

    total = await crud.JobCRUD.count(
        db,
        status=status,
        job_type=job_type
    )

    return {
        "items": jobs,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.patch("/jobs/{job_id}", response_model=schemas.JobResponse)
async def update_job(
    job_id: UUID,
    job_update: schemas.JobUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update job status and progress
    """
    # Check if job exists
    existing = await crud.JobCRUD.get(db, job_id)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Update job
    updated_job = await crud.JobCRUD.update(db, job_id, job_update)
    logger.info(f"Job updated: {job_id} - status: {job_update.status}")

    return updated_job


@router.post("/jobs/{job_id}/cancel", response_model=schemas.JobResponse)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel a running job
    """
    # Check if job exists
    job = await crud.JobCRUD.get(db, job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Check if job can be cancelled
    if job.status in [models.JobStatus.COMPLETED, models.JobStatus.FAILED, models.JobStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job in {job.status} state"
        )

    # Update job status
    updated_job = await crud.JobCRUD.update(
        db,
        job_id,
        schemas.JobUpdate(status=models.JobStatus.CANCELLED)
    )

    # TODO: Cancel Temporal workflow
    # await temporal_client.cancel_workflow(job.workflow_id)

    logger.info(f"Job cancelled: {job_id}")

    return updated_job


@router.get("/audit-logs", response_model=schemas.AuditLogList)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    job_id: Optional[UUID] = None,
    event_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List audit logs with pagination and filtering

    Query parameters:
    - page: Page number (starts at 1)
    - page_size: Number of items per page
    - job_id: Filter by job ID
    - event_type: Filter by event type
    - status: Filter by status
    """
    skip = (page - 1) * page_size

    logs = await crud.AuditLogCRUD.get_multi(
        db,
        skip=skip,
        limit=page_size,
        job_id=job_id,
        event_type=event_type,
        status=status
    )

    total = await crud.AuditLogCRUD.count(
        db,
        job_id=job_id,
        event_type=event_type,
        status=status
    )

    return {
        "items": logs,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.get("/sync/status", response_model=dict)
async def get_sync_status(
    source_system: str = Query(...),
    target_system: str = Query(...),
    entity_type: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get current sync state for given systems and entity type

    Returns the last sync timestamp and statistics
    """
    try:
        sync_state = await crud.SyncStateCRUD.get_or_create(
            db,
            source_system,
            target_system,
            entity_type
        )

        return {
            "source_system": source_system,
            "target_system": target_system,
            "entity_type": entity_type,
            "last_sync_timestamp": sync_state.last_sync_timestamp,
            "last_sync_cursor": sync_state.last_sync_cursor,
            "total_synced": sync_state.total_synced,
            "last_batch_size": sync_state.last_batch_size,
            "updated_at": sync_state.updated_at
        }

    except Exception as e:
        logger.error(f"Error getting sync status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting sync status: {str(e)}"
        )
