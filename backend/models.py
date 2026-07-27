from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON, ForeignKey, Enum, Boolean
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class RiskLevel(str, enum.Enum):
    """Enumeration for risk severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ContractStatus(str, enum.Enum):
    """Enumeration for contract processing status."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    ANALYZED = "analyzed"
    FAILED = "failed"


class RiskCategory(str, enum.Enum):
    """Enumeration for risk assessment categories."""
    PAYMENT_TERMS = "payment_terms"
    LIABILITY = "liability"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    TERMINATION = "termination"
    INDEMNIFICATION = "indemnification"
    CONFIDENTIALITY = "confidentiality"
    DISPUTE_RESOLUTION = "dispute_resolution"
    SCOPE_OF_WORK = "scope_of_work"


class Contract(Base):
    """
    Represents an uploaded contract document.
    
    Stores contract metadata, processing status, and relationships to analyses.
    """
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(255), nullable=False, index=True)  # External user ID from auth system
    title = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)  # Path to stored file
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_hash = Column(String(64), nullable=False, unique=True)  # SHA-256 hash for deduplication
    mime_type = Column(String(100), nullable=False)
    
    # Processing metadata
    status = Column(Enum(ContractStatus), nullable=False, default=ContractStatus.UPLOADED)
    error_message = Column(Text, nullable=True)
    
    # Extracted content
    extracted_text = Column(Text, nullable=True)
    page_count = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)
    
    # Overall risk metrics (denormalized for quick access)
    overall_risk_score = Column(Float, nullable=True)  # 0-100 scale
    overall_risk_level = Column(Enum(RiskLevel), nullable=True)
    
    # Metadata storage for flexible attributes
    metadata = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    analyzed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    analysis = relationship("ContractAnalysis", back_populates="contract", uselist=False, cascade="all, delete-orphan")
    risk_assessments = relationship("RiskAssessment", back_populates="contract", cascade="all, delete-orphan")
    flagged_clauses = relationship("FlaggedClause", back_populates="contract", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Contract(id={self.id}, title='{self.title}', status={self.status})>"


class ContractAnalysis(Base):
    """
    Stores comprehensive analysis results for a contract.
    
    One-to-one relationship with Contract. Contains aggregated insights,
    recommendations, and structured analysis data.
    """
    __tablename__ = "contract_analyses"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    # Analysis results
    summary = Column(Text, nullable=True)
    key_findings = Column(JSON, nullable=True, default=list)  # List of key finding objects
    recommendations = Column(JSON, nullable=True, default=list)  # List of recommendation objects
    
    # Detected contract attributes
    contract_type = Column(String(100), nullable=True)  # e.g., "Service Agreement", "NDA"
    parties = Column(JSON, nullable=True, default=list)  # List of identified parties
    effective_date = Column(String(100), nullable=True)
    expiration_date = Column(String(100), nullable=True)
    
    # Payment analysis
    payment_terms_found = Column(Boolean, default=False)
    payment_schedule = Column(String(500), nullable=True)
    payment_amount = Column(String(200), nullable=True)
    late_payment_penalties = Column(Boolean, default=False)
    
    # Liability analysis
    liability_cap_present = Column(Boolean, default=False)
    liability_cap_amount = Column(String(200), nullable=True)
    unlimited_liability = Column(Boolean, default=False)
    
    # IP rights analysis
    ip_ownership_clear = Column(Boolean, default=False)
    ip_transfer_clause = Column(Boolean, default=False)
    work_for_hire = Column(Boolean, default=False)
    
    # Termination analysis
    termination_clause_present = Column(Boolean, default=False)
    notice_period = Column(String(100), nullable=True)
    termination_for_convenience = Column(Boolean, default=False)
    
    # Missing protections (flags for important clauses that should exist)
    missing_protections = Column(JSON, nullable=True, default=list)
    
    # Processing metadata
    analysis_version = Column(String(20), nullable=False)  # Version of analysis algorithm
    processing_time_seconds = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    contract = relationship("Contract", back_populates="analysis")

    def __repr__(self) -> str:
        return f"<ContractAnalysis(id={self.id}, contract_id={self.contract_id})>"


class RiskAssessment(Base):
    """
    Stores individual risk assessments for specific categories.
    
    Each contract can have multiple risk assessments, one per category
    (payment terms, liability, IP rights, etc.).
    """
    __tablename__ = "risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Risk categorization
    category = Column(Enum(RiskCategory), nullable=False)
    risk_level = Column(Enum(RiskLevel), nullable=False)
    risk_score = Column(Float, nullable=False)  # 0-100 scale
    
    # Assessment details
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    impact = Column(Text, nullable=True)  # What could happen if this risk materializes
    mitigation = Column(Text, nullable=True)  # How to address this risk
    
    # Supporting evidence
    evidence = Column(JSON, nullable=True, default=list)  # References to specific clauses or text
    confidence_score = Column(Float, nullable=True)  # 0-1 confidence in this assessment
    
    # Metadata
    metadata = Column(JSON, nullable=True, default=dict)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    contract = relationship("Contract", back_populates="risk_assessments")

    def __repr__(self) -> str:
        return f"<RiskAssessment(id={self.id}, category={self.category}, risk_level={self.risk_level})>"


class FlaggedClause(Base):
    """
    Represents a specific clause or text segment flagged as potentially problematic.
    
    Allows for granular identification of risky language within contracts.
    """
    __tablename__ = "flagged_clauses"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Clause identification
    clause_text = Column(Text, nullable=False)
    clause_type = Column(String(200), nullable=True)  # e.g., "Indemnification", "Non-compete"
    page_number = Column(Integer, nullable=True)
    section_reference = Column(String(200), nullable=True)  # e.g., "Section 4.2"
    
    # Risk assessment for this specific clause
    risk_level = Column(Enum(RiskLevel), nullable=False)
    risk_category = Column(Enum(RiskCategory), nullable=True)
    
    # Explanation
    issue_description = Column(Text, nullable=False)
    why_problematic = Column(Text, nullable=False)
    suggested_revision = Column(Text, nullable=True)
    
    # Context and position
    start_position = Column(Integer, nullable=True)  # Character position in extracted text
    end_position = Column(Integer, nullable=True)
    surrounding_context = Column(Text, nullable=True)  # Additional context around the clause
    
    # Flagging metadata
    flagged_by_rule = Column(String(200), nullable=True)  # Which analysis rule triggered this
    confidence_score = Column(Float, nullable=True)  # 0-1 confidence
    
    # User interaction
    user_acknowledged = Column(Boolean, default=False)
    user_notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    contract = relationship("Contract", back_populates="flagged_clauses")

    def __repr__(self) -> str:
        return f"<FlaggedClause(id={self.id}, contract_id={self.contract_id}, risk_level={self.risk_level})>"


class AnalysisTemplate(Base):
    """
    Stores reusable analysis templates and rule sets.
    
    Allows for customizable analysis profiles (e.g., "Freelancer-focused",
    "Startup-friendly") that can be applied to contracts.
    """
    __tablename__ = "analysis_templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    
    # Template configuration
    category_weights = Column(JSON, nullable=False, default=dict)  # Weight for each risk category
    enabled_rules = Column(JSON, nullable=False, default=list)  # List of enabled analysis rules
    risk_thresholds = Column(JSON, nullable=False, default=dict)  # Custom thresholds for risk levels
    
    # Visibility and access
    is_public = Column(Boolean, default=True)
    created_by_user_id = Column(String(255),