"""
Database Models for MCP Server
Defines all SQLAlchemy ORM models
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Integer,
    DateTime,
    Text,
    Boolean,
    JSON,
    ForeignKey,
    Index,
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


# ============================================
# Enums
# ============================================

class MappingStatus(str, enum.Enum):
    """Status of a mapping record"""
    PENDING = "pending"
    ACTIVE = "active"
    FAILED = "failed"
    ARCHIVED = "archived"


class JobStatus(str, enum.Enum):
    """Status of a sync job"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EntityType(str, enum.Enum):
    """Types of entities that can be mapped"""
    EMPLOYEE = "employee"
    PATIENT = "patient"
    PROCEDURE = "procedure"
    PAYMENT = "payment"
    INVOICE = "invoice"
    VENDOR = "vendor"
    TRANSACTION = "transaction"
    DEPARTMENT = "department"
    VISIT = "visit"


class UserRole(str, enum.Enum):
    """User roles for authentication system"""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class IntegrationSystem(str, enum.Enum):
    """Supported integration systems"""
    ADP = "adp"
    EAGLESOFT = "eaglesoft"
    DENTALINTEL = "dentalintel"
    NETSUITE = "netsuite"
    BANK = "bank"
    DENTALERP = "dentalerp"


# ============================================
# Mapping Registry
# ============================================

class Mapping(Base):
    """
    Core mapping table - links entities across different systems
    """
    __tablename__ = "mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Source system information
    source_system = Column(SQLEnum(IntegrationSystem), nullable=False)
    source_id = Column(String(255), nullable=False)
    source_entity_type = Column(SQLEnum(EntityType), nullable=False)

    # Target system information
    target_system = Column(SQLEnum(IntegrationSystem), nullable=False)
    target_id = Column(String(255), nullable=False)
    target_entity_type = Column(SQLEnum(EntityType), nullable=False)

    # Mapping metadata
    status = Column(SQLEnum(MappingStatus), default=MappingStatus.PENDING, nullable=False)
    confidence_score = Column(Integer, default=100)  # 0-100 confidence in mapping

    # Additional data (JSON for flexibility)
    metadata = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_synced_at = Column(DateTime, nullable=True)

    # Soft delete
    deleted_at = Column(DateTime, nullable=True)

    # Indexes for fast lookups
    __table_args__ = (
        Index('idx_source_lookup', 'source_system', 'source_id', 'source_entity_type'),
        Index('idx_target_lookup', 'target_system', 'target_id', 'target_entity_type'),
        Index('idx_status', 'status'),
        Index('idx_last_synced', 'last_synced_at'),
    )

    def __repr__(self):
        return f"<Mapping {self.source_system}:{self.source_id} -> {self.target_system}:{self.target_id}>"


# ============================================
# Jobs / Orchestration
# ============================================

class Job(Base):
    """
    Tracks sync jobs and workflows
    """
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Job identification
    job_type = Column(String(100), nullable=False)  # e.g., "sync_employees", "import_procedures"
    workflow_id = Column(String(255), nullable=True)  # Temporal workflow ID

    # Source and target
    source_system = Column(SQLEnum(IntegrationSystem), nullable=False)
    target_system = Column(SQLEnum(IntegrationSystem), nullable=False)
    entity_type = Column(SQLEnum(EntityType), nullable=False)

    # Job status
    status = Column(SQLEnum(JobStatus), default=JobStatus.PENDING, nullable=False)

    # Progress tracking
    total_records = Column(Integer, default=0)
    processed_records = Column(Integer, default=0)
    failed_records = Column(Integer, default=0)

    # Job configuration
    config = Column(JSON, default={})

    # Results and errors
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationship to audit logs
    audit_logs = relationship("AuditLog", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_job_status', 'status'),
        Index('idx_job_type', 'job_type'),
        Index('idx_workflow', 'workflow_id'),
        Index('idx_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<Job {self.job_type} {self.status}>"


# ============================================
# Audit Logs
# ============================================

class AuditLog(Base):
    """
    Audit trail for all sync operations and API calls
    """
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Related job (optional)
    job_id = Column(UUID(as_uuid=True), ForeignKey('jobs.id'), nullable=True)

    # Event information
    event_type = Column(String(100), nullable=False)  # e.g., "mapping_created", "sync_completed"
    entity_type = Column(SQLEnum(EntityType), nullable=True)
    entity_id = Column(String(255), nullable=True)

    # Systems involved
    source_system = Column(SQLEnum(IntegrationSystem), nullable=True)
    target_system = Column(SQLEnum(IntegrationSystem), nullable=True)

    # Event details
    action = Column(String(50), nullable=False)  # CREATE, READ, UPDATE, DELETE
    status = Column(String(50), nullable=False)  # SUCCESS, FAILED, PARTIAL

    # User/Service information
    user_id = Column(String(255), nullable=True)
    service_name = Column(String(100), nullable=True)

    # Request/Response data
    request_data = Column(JSON, nullable=True)
    response_data = Column(JSON, nullable=True)
    error_details = Column(JSON, nullable=True)

    # Metadata
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    job = relationship("Job", back_populates="audit_logs")

    __table_args__ = (
        Index('idx_event_type', 'event_type'),
        Index('idx_job_id', 'job_id'),
        Index('idx_entity', 'entity_type', 'entity_id'),
        Index('idx_created_at', 'created_at'),
        Index('idx_status', 'status'),
    )

    def __repr__(self):
        return f"<AuditLog {self.event_type} {self.status}>"


# ============================================
# Integration Configuration
# ============================================

class Integration(Base):
    """
    Store integration credentials and configuration
    """
    __tablename__ = "integrations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Integration identification
    system = Column(SQLEnum(IntegrationSystem), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    is_configured = Column(Boolean, default=False)

    # Configuration (encrypted in production)
    config = Column(JSON, default={})  # API keys, endpoints, etc.

    # Rate limiting
    rate_limit_per_minute = Column(Integer, default=60)

    # Sync settings
    sync_enabled = Column(Boolean, default=False)
    sync_schedule_cron = Column(String(100), nullable=True)  # e.g., "0 */6 * * *"
    last_sync_at = Column(DateTime, nullable=True)
    next_sync_at = Column(DateTime, nullable=True)

    # Health check
    last_health_check_at = Column(DateTime, nullable=True)
    health_status = Column(String(50), default="unknown")  # healthy, degraded, down

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_system', 'system'),
        Index('idx_active', 'is_active'),
    )

    def __repr__(self):
        return f"<Integration {self.system} {'active' if self.is_active else 'inactive'}>"


# ============================================
# Data Sync State
# ============================================

class SyncState(Base):
    """
    Track the state of incremental syncs
    """
    __tablename__ = "sync_states"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Sync identification
    source_system = Column(SQLEnum(IntegrationSystem), nullable=False)
    target_system = Column(SQLEnum(IntegrationSystem), nullable=False)
    entity_type = Column(SQLEnum(EntityType), nullable=False)

    # State tracking
    last_sync_timestamp = Column(DateTime, nullable=True)
    last_sync_cursor = Column(String(255), nullable=True)  # For cursor-based pagination
    last_sync_checkpoint = Column(JSON, nullable=True)  # Custom checkpoint data

    # Sync statistics
    total_synced = Column(Integer, default=0)
    last_batch_size = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index('idx_sync_systems', 'source_system', 'target_system', 'entity_type'),
    )

    def __repr__(self):
        return f"<SyncState {self.source_system}->{self.target_system} {self.entity_type}>"


# ============================================
# User Authentication & Management
# ============================================

class User(Base):
    """
    User model for authentication system
    Multi-tenant support via tenant field
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Tenant isolation
    tenant = Column(String(100), nullable=False, index=True)  # e.g., 'talleresia', 'eunacom'

    # User identification
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)

    # User information
    full_name = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)

    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)  # Email verification
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)

    # Metadata
    last_login = Column(DateTime, nullable=True)
    profile_data = Column(JSON, nullable=True)  # Additional user data

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    verification_tokens = relationship("EmailVerificationToken", back_populates="user", cascade="all, delete-orphan")
    password_reset_tokens = relationship("PasswordResetToken", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_tenant', 'tenant'),
        Index('idx_user_tenant_email', 'tenant', 'email'),
        Index('idx_user_active', 'is_active'),
        Index('idx_user_verified', 'is_verified'),
    )

    def __repr__(self):
        return f"<User {self.email} ({self.tenant})>"


class EmailVerificationToken(Base):
    """
    Email verification tokens for user registration
    Tokens expire after 24 hours
    """
    __tablename__ = "email_verification_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Token
    token = Column(String(255), nullable=False, unique=True, index=True)

    # Expiration
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    user = relationship("User", back_populates="verification_tokens")

    __table_args__ = (
        Index('idx_verification_token', 'token'),
        Index('idx_verification_user', 'user_id'),
        Index('idx_verification_expires', 'expires_at'),
    )

    def __repr__(self):
        return f"<EmailVerificationToken {self.user_id}>"


class PasswordResetToken(Base):
    """
    Password reset tokens
    Tokens expire after 1 hour
    """
    __tablename__ = "password_reset_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User reference
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # Token
    token = Column(String(255), nullable=False, unique=True, index=True)

    # Expiration
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False, nullable=False)
    used_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    user = relationship("User", back_populates="password_reset_tokens")

    __table_args__ = (
        Index('idx_reset_token', 'token'),
        Index('idx_reset_user', 'user_id'),
        Index('idx_reset_expires', 'expires_at'),
    )

    def __repr__(self):
        return f"<PasswordResetToken {self.user_id}>"
