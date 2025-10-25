"""
Pydantic Schemas for API request/response validation
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from src.db.models import (
    MappingStatus,
    JobStatus,
    EntityType,
    IntegrationSystem,
)


# ============================================
# Base Schemas
# ============================================

class BaseSchema(BaseModel):
    """Base schema with common configuration"""
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)


# ============================================
# Mapping Schemas
# ============================================

class MappingBase(BaseSchema):
    """Base mapping schema"""
    source_system: IntegrationSystem
    source_id: str
    source_entity_type: EntityType
    target_system: IntegrationSystem
    target_id: str
    target_entity_type: EntityType
    confidence_score: Optional[int] = 100
    metadata: Optional[Dict[str, Any]] = {}


class MappingCreate(MappingBase):
    """Schema for creating a new mapping"""
    pass


class MappingUpdate(BaseSchema):
    """Schema for updating a mapping"""
    status: Optional[MappingStatus] = None
    confidence_score: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    last_synced_at: Optional[datetime] = None


class MappingResponse(MappingBase):
    """Schema for mapping response"""
    id: UUID
    status: MappingStatus
    created_at: datetime
    updated_at: datetime
    last_synced_at: Optional[datetime] = None


class MappingList(BaseSchema):
    """Schema for paginated mapping list"""
    items: List[MappingResponse]
    total: int
    page: int
    page_size: int


# ============================================
# Job Schemas
# ============================================

class JobBase(BaseSchema):
    """Base job schema"""
    job_type: str
    source_system: IntegrationSystem
    target_system: IntegrationSystem
    entity_type: EntityType
    config: Optional[Dict[str, Any]] = {}


class JobCreate(JobBase):
    """Schema for creating a new job"""
    pass


class JobUpdate(BaseSchema):
    """Schema for updating a job"""
    status: Optional[JobStatus] = None
    processed_records: Optional[int] = None
    failed_records: Optional[int] = None
    error_message: Optional[str] = None


class JobResponse(JobBase):
    """Schema for job response"""
    id: UUID
    workflow_id: Optional[str] = None
    status: JobStatus
    total_records: int
    processed_records: int
    failed_records: int
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class JobList(BaseSchema):
    """Schema for paginated job list"""
    items: List[JobResponse]
    total: int
    page: int
    page_size: int


# ============================================
# Audit Log Schemas
# ============================================

class AuditLogBase(BaseSchema):
    """Base audit log schema"""
    event_type: str
    action: str
    status: str
    entity_type: Optional[EntityType] = None
    entity_id: Optional[str] = None
    source_system: Optional[IntegrationSystem] = None
    target_system: Optional[IntegrationSystem] = None


class AuditLogCreate(AuditLogBase):
    """Schema for creating an audit log"""
    job_id: Optional[UUID] = None
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    duration_ms: Optional[int] = None


class AuditLogResponse(AuditLogBase):
    """Schema for audit log response"""
    id: UUID
    job_id: Optional[UUID] = None
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    error_details: Optional[Dict[str, Any]] = None
    created_at: datetime


class AuditLogList(BaseSchema):
    """Schema for paginated audit log list"""
    items: List[AuditLogResponse]
    total: int
    page: int
    page_size: int


# ============================================
# Integration Schemas
# ============================================

class IntegrationBase(BaseSchema):
    """Base integration schema"""
    system: IntegrationSystem
    name: str
    description: Optional[str] = None
    is_active: bool = True
    rate_limit_per_minute: int = 60
    sync_enabled: bool = False
    sync_schedule_cron: Optional[str] = None


class IntegrationCreate(IntegrationBase):
    """Schema for creating an integration"""
    config: Dict[str, Any] = {}


class IntegrationUpdate(BaseSchema):
    """Schema for updating an integration"""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None
    rate_limit_per_minute: Optional[int] = None
    sync_enabled: Optional[bool] = None
    sync_schedule_cron: Optional[str] = None


class IntegrationResponse(IntegrationBase):
    """Schema for integration response (without sensitive config)"""
    id: UUID
    is_configured: bool
    last_sync_at: Optional[datetime] = None
    next_sync_at: Optional[datetime] = None
    health_status: str
    last_health_check_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    # Don't expose config in response for security


class IntegrationList(BaseSchema):
    """Schema for integration list"""
    items: List[IntegrationResponse]
    total: int


# ============================================
# Sync State Schemas
# ============================================

class SyncStateBase(BaseSchema):
    """Base sync state schema"""
    source_system: IntegrationSystem
    target_system: IntegrationSystem
    entity_type: EntityType


class SyncStateCreate(SyncStateBase):
    """Schema for creating sync state"""
    last_sync_timestamp: Optional[datetime] = None
    last_sync_cursor: Optional[str] = None
    last_sync_checkpoint: Optional[Dict[str, Any]] = None


class SyncStateUpdate(BaseSchema):
    """Schema for updating sync state"""
    last_sync_timestamp: Optional[datetime] = None
    last_sync_cursor: Optional[str] = None
    last_sync_checkpoint: Optional[Dict[str, Any]] = None
    total_synced: Optional[int] = None
    last_batch_size: Optional[int] = None


class SyncStateResponse(SyncStateBase):
    """Schema for sync state response"""
    id: UUID
    last_sync_timestamp: Optional[datetime] = None
    last_sync_cursor: Optional[str] = None
    total_synced: int
    last_batch_size: int
    created_at: datetime
    updated_at: datetime


# ============================================
# Workflow Schemas
# ============================================

class WorkflowTriggerRequest(BaseSchema):
    """Schema for triggering a workflow"""
    workflow_type: str = Field(..., description="Type of workflow to run")
    source_system: IntegrationSystem
    target_system: IntegrationSystem
    entity_type: EntityType
    config: Optional[Dict[str, Any]] = Field(default={}, description="Workflow configuration")
    priority: Optional[int] = Field(default=5, ge=1, le=10, description="Workflow priority (1-10)")


class WorkflowTriggerResponse(BaseSchema):
    """Schema for workflow trigger response"""
    job_id: UUID
    workflow_id: str
    status: str
    message: str


# ============================================
# Health Check Schemas
# ============================================

class HealthCheckResponse(BaseSchema):
    """Schema for health check response"""
    status: str
    version: str
    timestamp: datetime
    services: Dict[str, Any]


class HealthCheckDetail(BaseSchema):
    """Detailed health check"""
    database: Dict[str, Any]
    redis: Dict[str, Any]
    kafka: Optional[Dict[str, Any]] = None
    temporal: Optional[Dict[str, Any]] = None


# ============================================
# Error Schemas
# ============================================

class ErrorResponse(BaseSchema):
    """Standard error response"""
    error: str
    detail: Optional[str] = None
    status_code: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================
# Statistics Schemas
# ============================================

class MappingStats(BaseSchema):
    """Mapping statistics"""
    total_mappings: int
    by_status: Dict[str, int]
    by_entity_type: Dict[str, int]
    by_system: Dict[str, int]


class JobStats(BaseSchema):
    """Job statistics"""
    total_jobs: int
    by_status: Dict[str, int]
    by_type: Dict[str, int]
    average_duration_seconds: Optional[float] = None
    success_rate: Optional[float] = None


class SystemStats(BaseSchema):
    """Overall system statistics"""
    mappings: MappingStats
    jobs: JobStats
    integrations_active: int
    last_sync_at: Optional[datetime] = None
