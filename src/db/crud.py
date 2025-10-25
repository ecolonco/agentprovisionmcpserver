"""
CRUD operations for database models
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_
from sqlalchemy.orm import selectinload

from src.db import models, schemas


# ============================================
# Mapping CRUD
# ============================================

class MappingCRUD:
    """CRUD operations for Mapping model"""

    @staticmethod
    async def create(
        db: AsyncSession,
        mapping: schemas.MappingCreate
    ) -> models.Mapping:
        """Create a new mapping"""
        db_mapping = models.Mapping(**mapping.model_dump())
        db.add(db_mapping)
        await db.commit()
        await db.refresh(db_mapping)
        return db_mapping

    @staticmethod
    async def get(
        db: AsyncSession,
        mapping_id: UUID
    ) -> Optional[models.Mapping]:
        """Get mapping by ID"""
        result = await db.execute(
            select(models.Mapping).where(models.Mapping.id == mapping_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_source(
        db: AsyncSession,
        source_system: str,
        source_id: str,
        entity_type: str
    ) -> Optional[models.Mapping]:
        """Get mapping by source system and ID"""
        result = await db.execute(
            select(models.Mapping).where(
                and_(
                    models.Mapping.source_system == source_system,
                    models.Mapping.source_id == source_id,
                    models.Mapping.source_entity_type == entity_type,
                    models.Mapping.deleted_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_target(
        db: AsyncSession,
        target_system: str,
        target_id: str,
        entity_type: str
    ) -> Optional[models.Mapping]:
        """Get mapping by target system and ID"""
        result = await db.execute(
            select(models.Mapping).where(
                and_(
                    models.Mapping.target_system == target_system,
                    models.Mapping.target_id == target_id,
                    models.Mapping.target_entity_type == entity_type,
                    models.Mapping.deleted_at.is_(None)
                )
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_multi(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        entity_type: Optional[str] = None
    ) -> List[models.Mapping]:
        """Get multiple mappings with filtering"""
        query = select(models.Mapping).where(
            models.Mapping.deleted_at.is_(None)
        )

        if status:
            query = query.where(models.Mapping.status == status)
        if entity_type:
            query = query.where(models.Mapping.source_entity_type == entity_type)

        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def count(
        db: AsyncSession,
        status: Optional[str] = None,
        entity_type: Optional[str] = None
    ) -> int:
        """Count mappings with filtering"""
        query = select(func.count(models.Mapping.id)).where(
            models.Mapping.deleted_at.is_(None)
        )

        if status:
            query = query.where(models.Mapping.status == status)
        if entity_type:
            query = query.where(models.Mapping.source_entity_type == entity_type)

        result = await db.execute(query)
        return result.scalar()

    @staticmethod
    async def update(
        db: AsyncSession,
        mapping_id: UUID,
        mapping_update: schemas.MappingUpdate
    ) -> Optional[models.Mapping]:
        """Update a mapping"""
        update_data = mapping_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()

        await db.execute(
            update(models.Mapping)
            .where(models.Mapping.id == mapping_id)
            .values(**update_data)
        )
        await db.commit()

        return await MappingCRUD.get(db, mapping_id)

    @staticmethod
    async def delete(
        db: AsyncSession,
        mapping_id: UUID,
        soft: bool = True
    ) -> bool:
        """Delete a mapping (soft delete by default)"""
        if soft:
            await db.execute(
                update(models.Mapping)
                .where(models.Mapping.id == mapping_id)
                .values(deleted_at=datetime.utcnow())
            )
        else:
            await db.execute(
                delete(models.Mapping).where(models.Mapping.id == mapping_id)
            )

        await db.commit()
        return True


# ============================================
# Job CRUD
# ============================================

class JobCRUD:
    """CRUD operations for Job model"""

    @staticmethod
    async def create(
        db: AsyncSession,
        job: schemas.JobCreate
    ) -> models.Job:
        """Create a new job"""
        db_job = models.Job(**job.model_dump())
        db.add(db_job)
        await db.commit()
        await db.refresh(db_job)
        return db_job

    @staticmethod
    async def get(
        db: AsyncSession,
        job_id: UUID
    ) -> Optional[models.Job]:
        """Get job by ID with audit logs"""
        result = await db.execute(
            select(models.Job)
            .options(selectinload(models.Job.audit_logs))
            .where(models.Job.id == job_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_workflow_id(
        db: AsyncSession,
        workflow_id: str
    ) -> Optional[models.Job]:
        """Get job by Temporal workflow ID"""
        result = await db.execute(
            select(models.Job).where(models.Job.workflow_id == workflow_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_multi(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        job_type: Optional[str] = None
    ) -> List[models.Job]:
        """Get multiple jobs with filtering"""
        query = select(models.Job)

        if status:
            query = query.where(models.Job.status == status)
        if job_type:
            query = query.where(models.Job.job_type == job_type)

        query = query.order_by(models.Job.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def count(
        db: AsyncSession,
        status: Optional[str] = None,
        job_type: Optional[str] = None
    ) -> int:
        """Count jobs with filtering"""
        query = select(func.count(models.Job.id))

        if status:
            query = query.where(models.Job.status == status)
        if job_type:
            query = query.where(models.Job.job_type == job_type)

        result = await db.execute(query)
        return result.scalar()

    @staticmethod
    async def update(
        db: AsyncSession,
        job_id: UUID,
        job_update: schemas.JobUpdate
    ) -> Optional[models.Job]:
        """Update a job"""
        update_data = job_update.model_dump(exclude_unset=True)

        # Set completed_at if status is completed or failed
        if update_data.get("status") in ["completed", "failed", "cancelled"]:
            update_data["completed_at"] = datetime.utcnow()

        # Set started_at if status is running
        if update_data.get("status") == "running":
            update_data["started_at"] = datetime.utcnow()

        await db.execute(
            update(models.Job)
            .where(models.Job.id == job_id)
            .values(**update_data)
        )
        await db.commit()

        return await JobCRUD.get(db, job_id)

    @staticmethod
    async def delete(
        db: AsyncSession,
        job_id: UUID
    ) -> bool:
        """Delete a job (hard delete, cascades to audit logs)"""
        await db.execute(
            delete(models.Job).where(models.Job.id == job_id)
        )
        await db.commit()
        return True


# ============================================
# AuditLog CRUD
# ============================================

class AuditLogCRUD:
    """CRUD operations for AuditLog model"""

    @staticmethod
    async def create(
        db: AsyncSession,
        audit_log: schemas.AuditLogCreate
    ) -> models.AuditLog:
        """Create a new audit log entry"""
        db_log = models.AuditLog(**audit_log.model_dump())
        db.add(db_log)
        await db.commit()
        await db.refresh(db_log)
        return db_log

    @staticmethod
    async def get_multi(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        job_id: Optional[UUID] = None,
        event_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[models.AuditLog]:
        """Get multiple audit logs with filtering"""
        query = select(models.AuditLog)

        if job_id:
            query = query.where(models.AuditLog.job_id == job_id)
        if event_type:
            query = query.where(models.AuditLog.event_type == event_type)
        if status:
            query = query.where(models.AuditLog.status == status)

        query = query.order_by(models.AuditLog.created_at.desc())
        query = query.offset(skip).limit(limit)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def count(
        db: AsyncSession,
        job_id: Optional[UUID] = None,
        event_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """Count audit logs with filtering"""
        query = select(func.count(models.AuditLog.id))

        if job_id:
            query = query.where(models.AuditLog.job_id == job_id)
        if event_type:
            query = query.where(models.AuditLog.event_type == event_type)
        if status:
            query = query.where(models.AuditLog.status == status)

        result = await db.execute(query)
        return result.scalar()


# ============================================
# Integration CRUD
# ============================================

class IntegrationCRUD:
    """CRUD operations for Integration model"""

    @staticmethod
    async def create(
        db: AsyncSession,
        integration: schemas.IntegrationCreate
    ) -> models.Integration:
        """Create a new integration"""
        db_integration = models.Integration(**integration.model_dump())
        db.add(db_integration)
        await db.commit()
        await db.refresh(db_integration)
        return db_integration

    @staticmethod
    async def get(
        db: AsyncSession,
        integration_id: UUID
    ) -> Optional[models.Integration]:
        """Get integration by ID"""
        result = await db.execute(
            select(models.Integration).where(
                models.Integration.id == integration_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_system(
        db: AsyncSession,
        system: str
    ) -> Optional[models.Integration]:
        """Get integration by system name"""
        result = await db.execute(
            select(models.Integration).where(
                models.Integration.system == system
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_multi(
        db: AsyncSession,
        is_active: Optional[bool] = None
    ) -> List[models.Integration]:
        """Get multiple integrations"""
        query = select(models.Integration)

        if is_active is not None:
            query = query.where(models.Integration.is_active == is_active)

        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update(
        db: AsyncSession,
        integration_id: UUID,
        integration_update: schemas.IntegrationUpdate
    ) -> Optional[models.Integration]:
        """Update an integration"""
        update_data = integration_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()

        await db.execute(
            update(models.Integration)
            .where(models.Integration.id == integration_id)
            .values(**update_data)
        )
        await db.commit()

        return await IntegrationCRUD.get(db, integration_id)


# ============================================
# SyncState CRUD
# ============================================

class SyncStateCRUD:
    """CRUD operations for SyncState model"""

    @staticmethod
    async def get_or_create(
        db: AsyncSession,
        source_system: str,
        target_system: str,
        entity_type: str
    ) -> models.SyncState:
        """Get or create sync state"""
        result = await db.execute(
            select(models.SyncState).where(
                and_(
                    models.SyncState.source_system == source_system,
                    models.SyncState.target_system == target_system,
                    models.SyncState.entity_type == entity_type
                )
            )
        )
        sync_state = result.scalar_one_or_none()

        if not sync_state:
            sync_state = models.SyncState(
                source_system=source_system,
                target_system=target_system,
                entity_type=entity_type
            )
            db.add(sync_state)
            await db.commit()
            await db.refresh(sync_state)

        return sync_state

    @staticmethod
    async def update(
        db: AsyncSession,
        sync_state_id: UUID,
        sync_state_update: schemas.SyncStateUpdate
    ) -> Optional[models.SyncState]:
        """Update sync state"""
        update_data = sync_state_update.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()

        await db.execute(
            update(models.SyncState)
            .where(models.SyncState.id == sync_state_id)
            .values(**update_data)
        )
        await db.commit()

        result = await db.execute(
            select(models.SyncState).where(models.SyncState.id == sync_state_id)
        )
        return result.scalar_one_or_none()
