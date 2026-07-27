"""
Contract Analysis Engine

Core module for analyzing contract text and identifying risky clauses,
unfair terms, and missing protections across multiple dimensions.
"""

import re
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    """Risk severity levels for contract clauses"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"


class ClauseCategory(str, Enum):
    """Categories of contract clauses to analyze"""
    PAYMENT = "payment"
    LIABILITY = "liability"
    IP_RIGHTS = "ip_rights"
    TERMINATION = "termination"
    CONFIDENTIALITY = "confidentiality"
    INDEMNIFICATION = "indemnification"
    DISPUTE_RESOLUTION = "dispute_resolution"
    SCOPE_OF_WORK = "scope_of_work"


@dataclass
class ClauseMatch:
    """Represents a matched clause in the contract"""
    category: ClauseCategory
    text: str
    risk_level: RiskLevel
    position: Tuple[int, int]  # start, end character positions
    confidence: float  # 0.0 to 1.0
    reason: str
    recommendation: str


@dataclass
class ContractScore:
    """Overall contract risk scoring"""
    overall_score: int  # 0-100, higher is better
    category_scores: Dict[ClauseCategory, int] = field(default_factory=dict)
    risk_distribution: Dict[RiskLevel, int] = field(default_factory=dict)
    total_issues: int = 0
    missing_protections: List[str] = field(default_factory=list)


class ContractAnalyzer:
    """
    Main contract analysis engine that performs pattern matching,
    risk assessment, and generates actionable recommendations.
    """

    def __init__(self):
        self._initialize_patterns()
        self._initialize_weights()

    def _initialize_patterns(self) -> None:
        """Initialize regex patterns and keywords for clause detection"""
        
        # Payment-related patterns
        self.payment_patterns = {
            "net_90_plus": (
                r"(?:payment|paid|due)\s+(?:within|in|net)\s+(\d+)\s+days",
                RiskLevel.HIGH,
                "Payment terms exceed 60 days, creating cash flow risk"
            ),
            "no_late_fees": (
                r"(?:late|overdue|past\s+due)(?:.*?)(?:fee|penalty|interest)",
                RiskLevel.MEDIUM,
                "Contract lacks late payment penalties"
            ),
            "spec_work": (
                r"(?:sample|spec|speculative|unpaid)\s+(?:work|deliverable|demo)",
                RiskLevel.CRITICAL,
                "Contract may require unpaid speculative work"
            ),
            "payment_upon_completion": (
                r"payment\s+(?:upon|after|following)\s+(?:completion|delivery|acceptance)",
                RiskLevel.MEDIUM,
                "No milestone payments; all payment deferred to end"
            ),
        }

        # Liability patterns
        self.liability_patterns = {
            "unlimited_liability": (
                r"(?:unlimited|without\s+limit|no\s+cap)(?:.*?)(?:liability|damages|indemnif)",
                RiskLevel.CRITICAL,
                "Unlimited liability exposure"
            ),
            "consequential_damages": (
                r"(?:consequential|indirect|incidental|punitive)\s+damages",
                RiskLevel.HIGH,
                "Liability includes consequential damages"
            ),
            "no_liability_cap": (
                r"(?<!limitation\s+of\s+)(?<!limited\s+)liability(?!.*?(?:limited|capped|not\s+exceed))",
                RiskLevel.HIGH,
                "No apparent cap on liability"
            ),
        }

        # IP Rights patterns
        self.ip_patterns = {
            "full_ip_transfer": (
                r"(?:all|entire|complete)(?:.*?)(?:intellectual\s+property|ip|copyright|rights?)(?:.*?)(?:transfer|assign|convey|grant)",
                RiskLevel.HIGH,
                "Broad IP rights transfer, including pre-existing work"
            ),
            "work_for_hire": (
                r"work(?:\s+|-)for(?:\s+|-)hire",
                RiskLevel.MEDIUM,
                "Work-for-hire clause detected"
            ),
            "perpetual_license": (
                r"(?:perpetual|unlimited|forever)(?:.*?)(?:license|right)",
                RiskLevel.MEDIUM,
                "Perpetual license grant without scope limitations"
            ),
            "no_ip_retention": (
                r"(?:waive|relinquish|surrender)(?:.*?)(?:rights?|ownership|ip)",
                RiskLevel.HIGH,
                "Contractor may not retain any IP rights"
            ),
        }

        # Termination patterns
        self.termination_patterns = {
            "at_will_termination": (
                r"(?:terminate|cancel)(?:.*?)(?:at\s+will|for\s+any\s+reason|without\s+cause)",
                RiskLevel.HIGH,
                "Client can terminate without cause"
            ),
            "no_termination_fee": (
                r"terminate(?!.*?(?:fee|penalty|compensation|payment))",
                RiskLevel.MEDIUM,
                "No termination fee or kill fee specified"
            ),
            "immediate_termination": (
                r"(?:immediate|instant)(?:.*?)termination",
                RiskLevel.HIGH,
                "Allows immediate termination without notice period"
            ),
        }

        # Indemnification patterns
        self.indemnification_patterns = {
            "broad_indemnification": (
                r"(?:indemnify|hold\s+harmless)(?:.*?)(?:from\s+any|against\s+all|for\s+all)",
                RiskLevel.CRITICAL,
                "Broad indemnification clause with extensive obligations"
            ),
            "third_party_claims": (
                r"(?:third[\s-]party|3rd[\s-]party)(?:.*?)(?:claims?|actions?|suits?)",
                RiskLevel.HIGH,
                "Indemnification covers third-party claims"
            ),
        }

        # Confidentiality patterns
        self.confidentiality_patterns = {
            "perpetual_nda": (
                r"(?:perpetual|indefinite|permanent)(?:.*?)(?:confidential|nda|non[\s-]disclos)",
                RiskLevel.MEDIUM,
                "Confidentiality obligations have no time limit"
            ),
            "broad_confidentiality": (
                r"(?:all|any|entire)(?:.*?)(?:information|data|materials?)(?:.*?)(?:confidential|proprietary)",
                RiskLevel.MEDIUM,
                "Overly broad confidentiality definition"
            ),
        }

    def _initialize_weights(self) -> None:
        """Initialize scoring weights for different categories"""
        self.category_weights = {
            ClauseCategory.PAYMENT: 0.25,
            ClauseCategory.LIABILITY: 0.20,
            ClauseCategory.IP_RIGHTS: 0.20,
            ClauseCategory.TERMINATION: 0.15,
            ClauseCategory.INDEMNIFICATION: 0.10,
            ClauseCategory.CONFIDENTIALITY: 0.05,
            ClauseCategory.DISPUTE_RESOLUTION: 0.05,
        }

        self.risk_penalties = {
            RiskLevel.CRITICAL: 40,
            RiskLevel.HIGH: 25,
            RiskLevel.MEDIUM: 15,
            RiskLevel.LOW: 5,
            RiskLevel.NONE: 0,
        }

    def analyze(self, contract_text: str) -> Tuple[List[ClauseMatch], ContractScore]:
        """
        Perform comprehensive contract analysis.
        
        Args:
            contract_text: Raw contract text to analyze
            
        Returns:
            Tuple of (list of clause matches, overall contract score)
        """
        if not contract_text or not contract_text.strip():
            logger.warning("Empty contract text provided for analysis")
            return [], ContractScore(overall_score=0, total_issues=0)

        # Normalize text for better pattern matching
        normalized_text = self._normalize_text(contract_text)
        
        # Find all clause matches
        matches = self._find_all_matches(normalized_text)
        
        # Check for missing protections
        missing = self._check_missing_protections(normalized_text, matches)
        
        # Calculate overall score
        score = self._calculate_score(matches, missing)
        
        logger.info(
            f"Analysis complete: {len(matches)} issues found, "
            f"overall score: {score.overall_score}"
        )
        
        return matches, score

    def _normalize_text(self, text: str) -> str:
        """Normalize contract text for consistent pattern matching"""
        # Convert to lowercase for case-insensitive matching
        text = text.lower()
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common formatting artifacts
        text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f]', '', text)
        
        return text.strip()

    def _find_all_matches(self, text: str) -> List[ClauseMatch]:
        """Find all pattern matches across all categories"""
        all_matches = []
        
        # Payment analysis
        all_matches.extend(
            self._match_category(text, self.payment_patterns, ClauseCategory.PAYMENT)
        )
        
        # Liability analysis
        all_matches.extend(
            self._match_category(text, self.liability_patterns, ClauseCategory.LIABILITY)
        )
        
        # IP rights analysis
        all_matches.extend(
            self._match_category(text, self.ip_patterns, ClauseCategory.IP_RIGHTS)
        )
        
        # Termination analysis
        all_matches.extend(
            self._match_category(text, self.termination_patterns, ClauseCategory.TERMINATION)
        )
        
        # Indemnification analysis
        all_matches.extend(
            self._match_category(
                text, self.indemnification_patterns, ClauseCategory.INDEMNIFICATION
            )
        )
        
        # Confidentiality analysis
        all_matches.extend(
            self._match_category(
                text, self.confidentiality_patterns, ClauseCategory.CONFIDENTIALITY
            )
        )
        
        # Remove duplicate/overlapping matches
        all_matches = self._deduplicate_matches(all_matches)
        
        return all_matches

    def _match_category(
        self,
        text: str,
        patterns: Dict[str, Tuple[str, RiskLevel, str]],
        category: ClauseCategory
    ) -> List[ClauseMatch]:
        """Match patterns for a specific category"""
        matches = []
        
        for pattern_name, (pattern, risk_level, reason) in patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE | re.DOTALL):
                # Extract context around match (up to 200 chars)
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 150)
                context = text[start:end].strip()
                
                # Calculate confidence based on pattern specificity
                confidence = self._calculate