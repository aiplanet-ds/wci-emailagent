"""SQLAlchemy models for WCI Email Agent"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Numeric,
    Index,
)
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.orm import relationship
from database.config import Base


class User(Base):
    """User model for authentication and tracking"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(255))
    is_active = Column(Boolean, default=True, index=True)

    # Authentication
    msal_account_id = Column(String(255))
    token_expires_at = Column(DateTime)

    # Settings
    preferences = Column(JSONB, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime)

    # Relationships
    emails = relationship("Email", back_populates="user", cascade="all, delete-orphan")
    email_states = relationship(
        "EmailState",
        foreign_keys="EmailState.user_id",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    processed_emails = relationship(
        "EmailState",
        foreign_keys="EmailState.processed_by_id",
        back_populates="processed_by_user",
    )
    delta_token = relationship("DeltaToken", back_populates="user", uselist=False, cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}')>"


class Vendor(Base):
    """Vendor model for supplier information"""

    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(String(100), unique=True, nullable=False, index=True)
    vendor_name = Column(String(255), nullable=False)

    # Contact info
    contact_email = Column(String(255), index=True)
    contact_phone = Column(String(50))

    # Verification
    verified = Column(Boolean, default=True, index=True)
    verified_domains = Column(JSONB, default=[])

    # Epicor sync
    last_synced_from_epicor = Column(DateTime)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    email_states = relationship("EmailState", back_populates="vendor")

    def __repr__(self):
        return f"<Vendor(id={self.id}, vendor_id='{self.vendor_id}', name='{self.vendor_name}')>"


class Email(Base):
    """Email model for storing email metadata and content"""

    __tablename__ = "emails"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(500), unique=True, nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Email metadata
    subject = Column(Text)
    sender_email = Column(String(255), index=True)
    sender_name = Column(String(255))
    received_at = Column(DateTime, index=True)
    has_attachments = Column(Boolean, default=False)

    # Email content
    body_text = Column(Text)
    body_html = Column(Text)

    # Extracted data (JSONB for flexibility)
    supplier_info = Column(JSONB)
    price_change_summary = Column(JSONB)
    affected_products = Column(JSONB)
    additional_details = Column(JSONB)

    # Raw email data
    raw_email_data = Column(JSONB)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="emails")
    email_state = relationship("EmailState", back_populates="email", uselist=False, cascade="all, delete-orphan")
    attachments = relationship("Attachment", back_populates="email", cascade="all, delete-orphan")
    epicor_sync_results = relationship("EpicorSyncResult", back_populates="email", cascade="all, delete-orphan")
    bom_impact_results = relationship("BomImpactResult", back_populates="email", cascade="all, delete-orphan")

    # Full-text search indexes
    __table_args__ = (
        Index("idx_emails_subject_fts", "subject", postgresql_using="gin", postgresql_ops={"subject": "gin_trgm_ops"}),
        Index("idx_emails_body_fts", "body_text", postgresql_using="gin", postgresql_ops={"body_text": "gin_trgm_ops"}),
    )

    def __repr__(self):
        return f"<Email(id={self.id}, message_id='{self.message_id}', subject='{self.subject[:50]}...')>"


class EmailState(Base):
    """Email state model for tracking processing status"""

    __tablename__ = "email_states"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(500), unique=True, nullable=False, index=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Processing status
    processed = Column(Boolean, default=False, index=True)
    processed_at = Column(DateTime)
    processed_by_id = Column(Integer, ForeignKey("users.id"))

    # Classification
    is_price_change = Column(Boolean)
    llm_confidence = Column(Numeric(5, 4))
    llm_reasoning = Column(Text)
    awaiting_llm_detection = Column(Boolean, default=False)
    llm_detection_performed = Column(Boolean, default=False)

    # Epicor sync
    epicor_synced = Column(Boolean, default=False, index=True)
    epicor_synced_at = Column(DateTime)
    epicor_sync_attempts = Column(Integer, default=0)

    # Follow-up
    needs_info = Column(Boolean, default=False)
    selected_missing_fields = Column(JSONB, default=[])
    followup_draft = Column(Text)

    # Vendor verification
    vendor_verified = Column(Boolean, default=False)
    verification_status = Column(String(50), default="pending_review", index=True)
    verification_method = Column(String(50))
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    manually_approved_by_id = Column(Integer, ForeignKey("users.id"))
    manually_approved_at = Column(DateTime)
    flagged_reason = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    email = relationship("Email", back_populates="email_state")
    user = relationship("User", foreign_keys=[user_id], back_populates="email_states")
    processed_by_user = relationship("User", foreign_keys=[processed_by_id], back_populates="processed_emails")
    manually_approved_by_user = relationship("User", foreign_keys=[manually_approved_by_id])
    vendor = relationship("Vendor", back_populates="email_states")

    def __repr__(self):
        return f"<EmailState(id={self.id}, message_id='{self.message_id}', processed={self.processed})>"


class Attachment(Base):
    """Attachment model for email attachments"""

    __tablename__ = "attachments"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, index=True)

    # File info
    filename = Column(String(500), index=True)
    content_type = Column(String(100))
    file_size = Column(Integer)

    # Storage
    storage_path = Column(Text)

    # Processing
    extracted_text = Column(Text)
    processed = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    email = relationship("Email", back_populates="attachments")

    def __repr__(self):
        return f"<Attachment(id={self.id}, filename='{self.filename}')>"


class EpicorSyncResult(Base):
    """Epicor sync result model for tracking Epicor integration"""

    __tablename__ = "epicor_sync_results"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Sync details
    sync_status = Column(String(50), index=True)  # 'success', 'partial', 'failed'
    total_products = Column(Integer, default=0)
    successful_updates = Column(Integer, default=0)
    failed_updates = Column(Integer, default=0)

    # Results
    results_summary = Column(JSONB)
    error_message = Column(Text)

    # Timestamps
    synced_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    email = relationship("Email", back_populates="epicor_sync_results")
    user = relationship("User")

    def __repr__(self):
        return f"<EpicorSyncResult(id={self.id}, sync_status='{self.sync_status}')>"


class DeltaToken(Base):
    """Delta token model for Microsoft Graph delta queries"""

    __tablename__ = "delta_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    delta_token = Column(Text, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="delta_token")

    def __repr__(self):
        return f"<DeltaToken(id={self.id}, user_id={self.user_id})>"


class AuditLog(Base):
    """Audit log model for tracking user actions"""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id"), nullable=True, index=True)

    # Action details
    action_type = Column(String(100), index=True)  # 'processed', 'approved', 'synced', etc.
    action_details = Column(JSONB)

    # Metadata
    ip_address = Column(INET)
    user_agent = Column(Text)

    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
    email = relationship("Email")

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action_type='{self.action_type}')>"


class BomImpactResult(Base):
    """BOM Impact Analysis results for each product in an email"""

    __tablename__ = "bom_impact_results"

    id = Column(Integer, primary_key=True, index=True)
    email_id = Column(Integer, ForeignKey("emails.id", ondelete="CASCADE"), nullable=False, index=True)

    # Product identification
    product_index = Column(Integer, nullable=False)  # Index of product in affected_products array
    part_num = Column(String(100), index=True)
    product_name = Column(String(255))

    # Price change info
    old_price = Column(Numeric(18, 6))
    new_price = Column(Numeric(18, 6))
    price_delta = Column(Numeric(18, 6))
    price_change_pct = Column(Numeric(10, 4))

    # Component validation
    component_validated = Column(Boolean, default=False)
    component_description = Column(String(500))

    # Supplier validation
    supplier_id = Column(String(100))
    supplier_validated = Column(Boolean, default=False)
    supplier_name = Column(String(255))
    vendor_num = Column(Integer)

    # BOM impact summary (JSONB for flexibility)
    summary = Column(JSONB)  # total_assemblies, risk_summary, annual_impact, etc.

    # Impact details - list of affected assemblies
    impact_details = Column(JSONB)  # Full array of assembly impacts

    # High-risk assemblies (for quick access)
    high_risk_assemblies = Column(JSONB)

    # Annual impact calculation
    annual_impact = Column(JSONB)  # Full annual impact breakdown
    total_annual_cost_impact = Column(Numeric(18, 2))

    # Actions and approval
    actions_required = Column(JSONB)  # List of required actions
    can_auto_approve = Column(Boolean, default=True)
    recommendation = Column(Text)

    # Thresholds used for analysis
    thresholds_used = Column(JSONB)

    # Processing status
    status = Column(String(20), default="pending", index=True)  # 'pending', 'success', 'warning', 'error'
    processing_errors = Column(JSONB, default=[])

    # Approval tracking
    approved = Column(Boolean, default=False, index=True)
    approved_by_id = Column(Integer, ForeignKey("users.id"))
    approved_at = Column(DateTime)
    approval_notes = Column(Text)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    email = relationship("Email", back_populates="bom_impact_results")
    approved_by = relationship("User")

    # Compound index for quick lookup
    __table_args__ = (
        Index('ix_bom_impact_email_product', 'email_id', 'product_index'),
    )

    def __repr__(self):
        return f"<BomImpactResult(id={self.id}, part_num='{self.part_num}', status='{self.status}')>"


class OAuthToken(Base):
    """OAuth token storage for external API integrations (e.g., Epicor)"""

    __tablename__ = "oauth_tokens"

    id = Column(Integer, primary_key=True, index=True)

    # Service identification (e.g., 'epicor', 'microsoft', etc.)
    service_name = Column(String(100), unique=True, nullable=False, index=True)

    # Token data
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=True)
    token_type = Column(String(50), default="Bearer")

    # Expiration tracking
    expires_at = Column(DateTime, nullable=False, index=True)

    # Metadata for tracking
    obtained_via = Column(String(50))  # 'client_credentials', 'password', 'refresh_token'
    scope = Column(String(500))

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Index for efficient lookup by service and expiration
    __table_args__ = (
        Index('ix_oauth_tokens_service_expires', 'service_name', 'expires_at'),
    )

    def __repr__(self):
        return f"<OAuthToken(id={self.id}, service='{self.service_name}', expires_at={self.expires_at})>"

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired"""
        return datetime.utcnow() >= self.expires_at

    @property
    def expires_soon(self) -> bool:
        """Check if the token expires within 5 minutes"""
        from datetime import timedelta
        return datetime.utcnow() >= (self.expires_at - timedelta(minutes=5))
