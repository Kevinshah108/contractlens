```python
import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import uvicorn

from app.database import engine, get_db, Base
from app.models import Contract, Analysis
from app.schemas import (
    ContractResponse,
    AnalysisResponse,
    ContractListResponse,
    HealthCheckResponse,
)
from app.services.document_parser import DocumentParser
from app.services.risk_analyzer import RiskAnalyzer
from app.utils.file_validator import validate_file_upload
from app.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    Creates database tables on startup.
    """
    logger.info("Starting ContractLens API...")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")
    
    # Initialize services
    app.state.document_parser = DocumentParser()
    app.state.risk_analyzer = RiskAnalyzer()
    logger.info("Services initialized")
    
    yield
    
    logger.info("Shutting down ContractLens API...")


# Initialize FastAPI application
app = FastAPI(
    title="ContractLens API",
    description="AI-powered contract analysis for freelancers and small businesses",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An internal server error occurred",
            "error": str(exc) if settings.DEBUG else "Internal server error"
        }
    )


@app.get("/", response_model=HealthCheckResponse)
async def root():
    """Root endpoint - health check."""
    return {
        "status": "healthy",
        "service": "ContractLens API",
        "version": "1.0.0"
    }


@app.get("/api/health", response_model=HealthCheckResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint with database connectivity verification.
    """
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        db_status = "disconnected"
        
    return {
        "status": "healthy" if db_status == "connected" else "degraded",
        "service": "ContractLens API",
        "version": "1.0.0",
        "database": db_status
    }


@app.post("/api/contracts/upload", response_model=ContractResponse, status_code=status.HTTP_201_CREATED)
async def upload_contract(
    file: UploadFile = File(...),
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Upload and parse a contract document.
    
    Args:
        file: PDF or TXT file containing the contract
        user_id: Optional user identifier for tracking
        db: Database session
        
    Returns:
        ContractResponse with parsed content and metadata
        
    Raises:
        HTTPException: If file validation or parsing fails
    """
    logger.info(f"Received contract upload: {file.filename}")
    
    # Validate file
    try:
        validate_file_upload(file)
    except ValueError as e:
        logger.warning(f"File validation failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Read file content
    try:
        content = await file.read()
        file_size = len(content)
        
        if file_size > settings.MAX_FILE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds {settings.MAX_FILE_SIZE_MB}MB limit"
            )
    except Exception as e:
        logger.error(f"Error reading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to read uploaded file"
        )
    
    # Parse document
    try:
        parser = app.state.document_parser
        parsed_data = parser.parse(content, file.filename)
    except Exception as e:
        logger.error(f"Document parsing failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse document: {str(e)}"
        )
    
    # Store contract in database
    try:
        contract = Contract(
            filename=file.filename,
            file_size=file_size,
            content_type=file.content_type,
            raw_text=parsed_data["text"],
            word_count=parsed_data["word_count"],
            page_count=parsed_data.get("page_count", 1),
            user_id=user_id
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        logger.info(f"Contract stored successfully: ID={contract.id}")
        
        return ContractResponse(
            id=contract.id,
            filename=contract.filename,
            file_size=contract.file_size,
            word_count=contract.word_count,
            page_count=contract.page_count,
            uploaded_at=contract.created_at,
            status="parsed"
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store contract"
        )


@app.post("/api/contracts/{contract_id}/analyze", response_model=AnalysisResponse)
async def analyze_contract(
    contract_id: int,
    db: Session = Depends(get_db)
):
    """
    Perform comprehensive risk analysis on an uploaded contract.
    
    Args:
        contract_id: ID of the contract to analyze
        db: Database session
        
    Returns:
        AnalysisResponse with risk scores and recommendations
        
    Raises:
        HTTPException: If contract not found or analysis fails
    """
    logger.info(f"Starting analysis for contract ID: {contract_id}")
    
    # Retrieve contract
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract with ID {contract_id} not found"
        )
    
    # Check if analysis already exists
    existing_analysis = db.query(Analysis).filter(
        Analysis.contract_id == contract_id
    ).first()
    
    if existing_analysis:
        logger.info(f"Returning existing analysis for contract {contract_id}")
        return AnalysisResponse(
            id=existing_analysis.id,
            contract_id=existing_analysis.contract_id,
            overall_risk_score=existing_analysis.overall_risk_score,
            payment_risk_score=existing_analysis.payment_risk_score,
            liability_risk_score=existing_analysis.liability_risk_score,
            ip_rights_risk_score=existing_analysis.ip_rights_risk_score,
            termination_risk_score=existing_analysis.termination_risk_score,
            risky_clauses=existing_analysis.risky_clauses,
            missing_protections=existing_analysis.missing_protections,
            recommendations=existing_analysis.recommendations,
            analyzed_at=existing_analysis.created_at
        )
    
    # Perform analysis
    try:
        analyzer = app.state.risk_analyzer
        analysis_result = analyzer.analyze(contract.raw_text)
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Contract analysis failed: {str(e)}"
        )
    
    # Store analysis results
    try:
        analysis = Analysis(
            contract_id=contract_id,
            overall_risk_score=analysis_result["overall_risk_score"],
            payment_risk_score=analysis_result["payment_risk_score"],
            liability_risk_score=analysis_result["liability_risk_score"],
            ip_rights_risk_score=analysis_result["ip_rights_risk_score"],
            termination_risk_score=analysis_result["termination_risk_score"],
            risky_clauses=analysis_result["risky_clauses"],
            missing_protections=analysis_result["missing_protections"],
            recommendations=analysis_result["recommendations"]
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        
        logger.info(f"Analysis completed for contract {contract_id}: Overall risk={analysis.overall_risk_score}")
        
        return AnalysisResponse(
            id=analysis.id,
            contract_id=analysis.contract_id,
            overall_risk_score=analysis.overall_risk_score,
            payment_risk_score=analysis.payment_risk_score,
            liability_risk_score=analysis.liability_risk_score,
            ip_rights_risk_score=analysis.ip_rights_risk_score,
            termination_risk_score=analysis.termination_risk_score,
            risky_clauses=analysis.risky_clauses,
            missing_protections=analysis.missing_protections,
            recommendations=analysis.recommendations,
            analyzed_at=analysis.created_at
        )
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to store analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to store analysis results"
        )


@app.get("/api/contracts", response_model=ContractListResponse)
async def list_contracts(
    skip: int = 0,
    limit: int = 20,
    user_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all uploaded contracts with optional filtering.
    
    Args:
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
        user_id: Optional filter by user ID
        db: Database session
        
    Returns:
        ContractListResponse with contracts and total count
    """
    query = db.query(Contract)