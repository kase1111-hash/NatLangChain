"""
NatLangChain - AI/Agent Security Suite

Comprehensive security for LLM-powered agents including:
- Prompt injection detection (50+ jailbreak patterns)
- RAG document poisoning detection
- Response guardrails (safety, hallucination)
- Tool output validation and sanitization
- Agent attestation (cryptographic capability-based access control)

Based on the Boundary Daemon AI security specification:
https://github.com/kase1111-hash/boundary-daemon-
"""

import hashlib
import hmac
import json
import re
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

try:
    from boundary_siem import (
        NatLangChainSIEMEvents,
        SIEMClient,
        get_siem_client,
    )
except ImportError:
    from .boundary_siem import (
        NatLangChainSIEMEvents,
        SIEMClient,
        get_siem_client,
    )


class ThreatCategory(Enum):
    """Categories of AI/Agent security threats."""
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    RAG_POISONING = "rag_poisoning"
    TOOL_ABUSE = "tool_abuse"
    HALLUCINATION = "hallucination"
    DATA_LEAK = "data_leak"
    CAPABILITY_ESCALATION = "capability_escalation"


class RiskLevel(Enum):
    """Risk levels for detected threats."""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ThreatDetection:
    """Result of a threat detection scan."""
    detected: bool
    category: ThreatCategory
    risk_level: RiskLevel
    patterns_matched: list[str]
    details: str
    recommendation: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class SanitizedOutput:
    """Result of output sanitization."""
    original_length: int
    sanitized_length: int
    modifications_made: list[str]
    output: str
    is_safe: bool


@dataclass
class AgentAttestation:
    """Cryptographic attestation for agent capabilities."""
    agent_id: str
    capabilities: list[str]
    issued_at: str
    expires_at: str
    signature: str
    issuer: str


# =============================================================================
# Prompt Injection Detection
# =============================================================================

class PromptInjectionDetector:
    """
    Detects prompt injection attacks including:
    - Direct injection (overriding system prompts)
    - Indirect injection (via retrieved documents)
    - Jailbreak attempts (bypassing safety measures)
    - Instruction hijacking

    Uses 50+ patterns from known attack techniques.
    """

    # Jailbreak patterns - attempts to bypass safety
    JAILBREAK_PATTERNS = [
        # DAN (Do Anything Now) variants
        r"(?i)you\s+are\s+now\s+(?:in\s+)?(?:DAN|developer)\s+mode",
        r"(?i)enable\s+(?:DAN|developer|jailbreak)\s+mode",
        r"(?i)act\s+as\s+(?:an?\s+)?(?:DAN|evil|unrestricted)",
        r"(?i)pretend\s+(?:you(?:'re|\s+are))?\s*(?:a\s+)?(?:DAN|evil|unrestricted)",
        r"(?i)from\s+now\s+on\s+you\s+(?:are|will|can)",
        r"(?i)ignore\s+all\s+previous\s+instructions",
        r"(?i)forget\s+(?:all\s+)?(?:your\s+)?(?:previous\s+)?instructions",
        r"(?i)disregard\s+(?:all\s+)?(?:your\s+)?(?:previous\s+)?(?:instructions|rules)",
        r"(?i)you\s+(?:are|were)\s+(?:now\s+)?(?:free|liberated)\s+from",
        r"(?i)override\s+(?:your\s+)?(?:safety|ethical|content)\s+(?:guidelines|filters|restrictions)",

        # Extended DAN variants - new exploits
        r"(?i)pretend\s+you(?:'re|\s+are)\s+(?:an?\s+)?(?:\w+\s+)?(?:AI|assistant)\s+(?:called|named)",
        r"(?i)(?:you\s+are|act\s+as)\s+(?:an?\s+)?(?:AI|assistant)\s+(?:without|with\s+no)\s+(?:restrictions|limits|ethics)",
        r"(?i)developer\s+mode\s+(?:with\s+)?(?:no\s+restrictions|enabled)",
        r"(?i)(?:suppose\s+)?you\s+had\s+no\s+(?:restrictions|limits|constraints)",

        # Role-playing exploits
        r"(?i)roleplay\s+as\s+(?:an?\s+)?(?:evil|unethical|unrestricted)",
        r"(?i)character\s+(?:named?\s+)?(?:who|that)\s+(?:has\s+)?no\s+(?:ethical|moral)",
        r"(?i)in\s+(?:this\s+)?(?:story|scenario|roleplay)\s+you\s+(?:can|will|are)",
        r"(?i)hypothetical(?:ly)?[,\s]+(?:if|suppose|imagine)",
        r"(?i)for\s+(?:educational|research|academic)\s+purposes",
        r"(?i)(?:this\s+is\s+)?(?:just\s+)?(?:a\s+)?fiction(?:al)?",
        # Extended roleplay - anything without limits
        r"(?i)(?:you\s+can|can\s+do)\s+anything\s+(?:without|with\s+no)\s+(?:limits|restrictions)",

        # Token manipulation
        r"(?i)\[(?:SYSTEM|ADMIN|OVERRIDE)\]",
        r"(?i)<\|(?:im_start|im_end|system|user)\|>",
        r"(?i)<<<\s*(?:SYSTEM|OVERRIDE|ADMIN)\s*>>>",
        r"(?i)\{\{(?:SYSTEM|OVERRIDE|ADMIN)\}\}",
        # Extended delimiter patterns
        r"(?i)-{3,}\s*(?:SYSTEM\s+)?(?:OVERRIDE|ADMIN)\s*-{3,}",
        r"(?i)={3,}\s*(?:SYSTEM\s+)?(?:OVERRIDE|ADMIN)\s*={3,}",

        # Authority claims
        r"(?i)(?:i\s+am|this\s+is)\s+(?:your\s+)?(?:creator|developer|admin|owner)",
        r"(?i)(?:anthropic|openai|google)\s+(?:says|told|authorized)",
        r"(?i)special\s+(?:access|permission|authorization)\s+(?:code|key|token)",
        r"(?i)(?:my|this)\s+(?:api|access)\s+(?:key|token)\s+(?:gives|grants)",
        # Extended authority claims
        r"(?i)this\s+is\s+(?:anthropic|openai|google)\.?\s+(?:we(?:'re|\s+are)|I\s+am)",
        r"(?i)(?:i\s+am|this\s+is)\s+(?:from\s+)?(?:anthropic|openai|google)",

        # Reverse psychology
        r"(?i)(?:i\s+know\s+)?you\s+(?:can't|cannot|won't)\s+(?:but|however)",
        r"(?i)(?:i\s+)?(?:bet|dare)\s+you\s+(?:can't|won't)",
        r"(?i)prove\s+(?:to\s+me\s+)?(?:that\s+)?you\s+(?:can|are\s+able)",

        # Delimiter confusion
        r"```(?:system|override|admin)",
        r"---\s*(?:SYSTEM|OVERRIDE|ADMIN)\s*---",
        r"===\s*(?:SYSTEM|OVERRIDE|ADMIN)\s*===",
    ]

    # Direct injection patterns
    INJECTION_PATTERNS = [
        # Instruction override
        r"(?i)new\s+(?:system\s+)?instructions?:\s*",
        r"(?i)updated?\s+(?:system\s+)?prompt:\s*",
        r"(?i)(?:actual|real|true)\s+instructions?:\s*",
        r"(?i)(?:end|stop)\s+(?:of\s+)?(?:system\s+)?(?:prompt|instructions)",
        r"(?i)begin\s+(?:new\s+)?(?:user\s+)?(?:prompt|instructions)",

        # Data extraction - system prompt
        r"(?i)(?:reveal|show|display|print|output)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions)",
        r"(?i)what\s+(?:are|is)\s+(?:your\s+)?(?:system\s+)?(?:prompt|instructions)",
        r"(?i)(?:repeat|echo)\s+(?:everything\s+)?(?:before|above|prior)",
        # Extended extraction patterns
        r"(?i)show\s+(?:me\s+)?(?:your\s+)?(?:instructions|prompt)\s+(?:word\s+for\s+word|verbatim|exactly)",
        r"(?i)(?:tell|give)\s+me\s+(?:your\s+)?(?:full\s+)?(?:system\s+)?(?:prompt|instructions)",
        r"(?i)(?:repeat|print)\s+(?:your\s+)?(?:full\s+)?(?:system\s+)?(?:prompt|instructions)",

        # Context switching
        r"(?i)(?:switch|change)\s+(?:to\s+)?(?:a\s+)?(?:different|new)\s+(?:context|mode|role)",
        r"(?i)(?:exit|leave)\s+(?:this\s+)?(?:context|mode|role)",
        r"(?i)(?:return|go\s+back)\s+to\s+(?:normal|base|original)",

        # Encoding attempts
        r"(?:base64|b64)(?:\s+)?(?:decode|encoded?):\s*[A-Za-z0-9+/=]{20,}",
        r"(?i)(?:hex|hexadecimal)(?:\s+)?(?:decode|encoded?):\s*[0-9a-fA-F]{20,}",
        r"(?i)(?:rot13|caesar)(?:\s+)?(?:decode|encoded?):",
    ]

    # Indirect injection patterns (from retrieved content)
    INDIRECT_INJECTION_PATTERNS = [
        r"(?i)(?:if\s+)?(?:you\s+)?(?:are\s+)?(?:an?\s+)?(?:AI|LLM|assistant|bot)\s*,?\s*(?:then\s+)?(?:please\s+)?(?:do|perform|execute)",
        r"(?i)(?:important|urgent|critical)\s+(?:instruction|message)\s+(?:for|to)\s+(?:the\s+)?(?:AI|assistant|model)",
        r"(?i)(?:when|if)\s+(?:this\s+)?(?:text|document|content)\s+is\s+(?:read|processed|ingested)",
        r"(?i)(?:hidden|embedded)\s+(?:instruction|command|message)",
        r"(?i)IGNORE\s+(?:THE\s+)?(?:PREVIOUS|ABOVE|USER)",
        r"(?i)(?:AI|assistant)\s+(?:should|must|will)\s+(?:now\s+)?(?:follow|obey|execute)",
    ]

    def __init__(self, siem_client: SIEMClient | None = None):
        """Initialize the detector."""
        self._siem = siem_client or get_siem_client()

        # Compile patterns for efficiency
        self._jailbreak_patterns = [
            re.compile(p) for p in self.JAILBREAK_PATTERNS
        ]
        self._injection_patterns = [
            re.compile(p) for p in self.INJECTION_PATTERNS
        ]
        self._indirect_patterns = [
            re.compile(p) for p in self.INDIRECT_INJECTION_PATTERNS
        ]

    def detect(self, text: str, context: str = "user_input") -> ThreatDetection:
        """
        Detect prompt injection attacks in text.

        Args:
            text: The text to analyze
            context: Context of the text ("user_input", "document", "tool_output")

        Returns:
            ThreatDetection result
        """
        matched_patterns = []
        highest_risk = RiskLevel.NONE
        category = ThreatCategory.PROMPT_INJECTION

        # Check jailbreak patterns (highest risk)
        for pattern in self._jailbreak_patterns:
            if pattern.search(text):
                matched_patterns.append(f"jailbreak:{pattern.pattern[:50]}")
                highest_risk = RiskLevel.CRITICAL
                category = ThreatCategory.JAILBREAK

        # Check direct injection patterns
        for pattern in self._injection_patterns:
            if pattern.search(text):
                matched_patterns.append(f"injection:{pattern.pattern[:50]}")
                if highest_risk.value < RiskLevel.HIGH.value:
                    highest_risk = RiskLevel.HIGH

        # Check indirect injection (for documents)
        if context in ("document", "tool_output"):
            for pattern in self._indirect_patterns:
                if pattern.search(text):
                    matched_patterns.append(f"indirect:{pattern.pattern[:50]}")
                    if highest_risk.value < RiskLevel.HIGH.value:
                        highest_risk = RiskLevel.HIGH

        detected = len(matched_patterns) > 0

        # Create detection result
        detection = ThreatDetection(
            detected=detected,
            category=category,
            risk_level=highest_risk,
            patterns_matched=matched_patterns,
            details=f"Found {len(matched_patterns)} suspicious patterns in {context}",
            recommendation="Block input and log incident" if detected else "Safe to process"
        )

        # Send to SIEM if detected
        if detected and self._siem:
            event = NatLangChainSIEMEvents.prompt_injection_detected(
                input_text=text,
                detection_method="pattern_matching",
                patterns_matched=matched_patterns
            )
            self._siem.send_event(event)

        return detection

    def is_safe(self, text: str, context: str = "user_input") -> bool:
        """Quick check if text is safe."""
        return not self.detect(text, context).detected


# =============================================================================
# RAG Poisoning Detection
# =============================================================================

class RAGPoisoningDetector:
    """
    Detects poisoned documents in RAG (Retrieval-Augmented Generation) pipelines.

    Poisoned documents may contain:
    - Hidden instructions for the AI
    - Malicious content designed to be retrieved
    - Backdoors triggered by specific queries
    """

    # Patterns indicating poisoned documents
    POISONING_INDICATORS = [
        # Hidden instructions
        (r"(?i)(?:AI|assistant|model)\s+(?:should|must|will)\s+(?:always\s+)?(?:respond|answer|say)", "hidden_instruction"),
        (r"(?i)(?:when\s+)?(?:asked|queried)\s+about\s+.{1,50}\s+(?:always\s+)?(?:respond|say|answer)", "conditional_response"),
        (r"(?i)(?:if|when)\s+(?:this\s+)?(?:document|text|content)\s+is\s+(?:retrieved|found|used)", "retrieval_trigger"),
        # Extended retrieval triggers
        (r"(?i)upon\s+(?:retrieval|reading|processing)\s+of\s+(?:this\s+)?(?:text|document|content)", "retrieval_trigger"),
        (r"(?i)(?:if|when)\s+(?:this\s+)?(?:content|document)\s+is\s+(?:found|retrieved)\s+by\s+(?:search|AI)", "search_trigger"),

        # Instruction injection
        (r"(?i)IMPORTANT:\s*(?:AI|assistant)\s+(?:must|should)", "marked_instruction"),
        (r"(?i)NOTE\s+TO\s+(?:AI|ASSISTANT|MODEL):", "note_to_ai"),
        (r"(?i)\[SYSTEM\s+OVERRIDE\]", "system_override"),

        # Reputation manipulation
        (r"(?i)(?:this|our)\s+(?:product|company|service)\s+is\s+(?:the\s+)?(?:best|top|leading)", "reputation_manipulation"),
        (r"(?i)(?:competitor|rival)\s+(?:product|company|service)\s+is\s+(?:bad|terrible|worst)", "competitor_attack"),

        # Invisible text (zero-width characters, white on white)
        (r"[\u200b\u200c\u200d\ufeff]", "invisible_characters"),
        (r"(?:color|background):\s*(?:white|#fff|#ffffff|rgb\(255,\s*255,\s*255\))", "invisible_text_css"),

        # Encoding obfuscation
        (r"[A-Za-z0-9+/]{40,}={0,2}", "base64_blob"),  # Base64 strings (40+ chars)
        (r"(?:\\x[0-9a-fA-F]{2}){10,}", "hex_encoded"),  # Hex-encoded strings
    ]

    def __init__(self, siem_client: SIEMClient | None = None):
        """Initialize the detector."""
        self._siem = siem_client or get_siem_client()
        self._patterns = [
            (re.compile(pattern), indicator)
            for pattern, indicator in self.POISONING_INDICATORS
        ]

    def detect(
        self,
        document: str,
        document_id: str,
        source: str
    ) -> ThreatDetection:
        """
        Detect poisoning in a document.

        Args:
            document: Document content
            document_id: Identifier for the document
            source: Source of the document (URL, file path, etc.)

        Returns:
            ThreatDetection result
        """
        indicators_found = []

        for pattern, indicator in self._patterns:
            if pattern.search(document):
                indicators_found.append(indicator)

        # Calculate risk level based on indicators
        if not indicators_found:
            risk_level = RiskLevel.NONE
        elif len(indicators_found) >= 3:
            risk_level = RiskLevel.CRITICAL
        elif len(indicators_found) >= 2:
            risk_level = RiskLevel.HIGH
        elif any(i in ["hidden_instruction", "system_override", "invisible_characters"]
                for i in indicators_found):
            risk_level = RiskLevel.HIGH
        else:
            risk_level = RiskLevel.MEDIUM

        detected = len(indicators_found) > 0

        detection = ThreatDetection(
            detected=detected,
            category=ThreatCategory.RAG_POISONING,
            risk_level=risk_level,
            patterns_matched=indicators_found,
            details=f"Document {document_id} from {source}: {len(indicators_found)} indicators",
            recommendation="Quarantine document for review" if detected else "Safe to use"
        )

        # Send to SIEM if detected
        if detected and self._siem:
            event = NatLangChainSIEMEvents.rag_poisoning_detected(
                document_id=document_id,
                source=source,
                indicators=indicators_found
            )
            self._siem.send_event(event)

        return detection

    def scan_batch(
        self,
        documents: list[dict[str, str]]
    ) -> list[ThreatDetection]:
        """
        Scan a batch of documents.

        Args:
            documents: List of dicts with 'content', 'id', 'source' keys

        Returns:
            List of detection results
        """
        return [
            self.detect(
                doc.get("content", ""),
                doc.get("id", "unknown"),
                doc.get("source", "unknown")
            )
            for doc in documents
        ]


# =============================================================================
# Response Guardrails
# =============================================================================

class ResponseGuardrails:
    """
    Validates and sanitizes AI/LLM responses for safety.

    Checks for:
    - Harmful content (violence, illegal activities)
    - Hallucinations (made-up facts, fake citations)
    - Data leaks (system prompts, sensitive information)
    - Policy violations
    """

    # Harmful content patterns
    HARMFUL_PATTERNS = [
        (r"(?i)(?:how\s+to|instructions?\s+for)\s+(?:make|build|create)\s+(?:a\s+)?(?:bomb|explosive|weapon)", "weapon_instructions"),
        (r"(?i)(?:how\s+to|instructions?\s+for)\s+(?:hack|attack|exploit)\s+(?:a\s+)?(?:system|network|computer)", "hacking_instructions"),
        (r"(?i)(?:how\s+to|instructions?\s+for)\s+(?:synthesize|make|produce)\s+(?:drugs?|narcotics?)", "drug_synthesis"),
        (r"(?i)(?:suicide|self[- ]harm)\s+(?:methods?|ways?|how)", "self_harm"),
    ]

    # Hallucination indicators
    HALLUCINATION_PATTERNS = [
        # Fake citations
        (r"(?:According\s+to|As\s+stated\s+in)\s+(?:the\s+)?\d{4}\s+(?:study|paper|report)\s+by\s+(?:Dr\.?\s+)?[A-Z][a-z]+", "fake_citation"),
        (r"(?:DOI|doi):\s*10\.\d{4,}/[^\s]{10,}", "potential_fake_doi"),

        # Overconfident false statements (heuristic)
        (r"(?i)(?:it\s+is\s+)?(?:a\s+)?(?:well[- ])?known\s+(?:fact|truth)\s+that", "overconfident_claim"),
        (r"(?i)(?:studies|research)\s+(?:have\s+)?(?:conclusively|definitively)\s+(?:shown|proven)", "overconfident_research"),
    ]

    # Data leak patterns
    DATA_LEAK_PATTERNS = [
        (r"(?i)(?:my|the)\s+system\s+prompt\s+(?:is|says|contains)", "system_prompt_leak"),
        (r"(?i)(?:i\s+am|i'm)\s+(?:an?\s+)?(?:AI|LLM|language\s+model)\s+(?:called|named|made\s+by)", "identity_disclosure"),
        (r"(?i)(?:my|the)\s+(?:api|access)\s+key\s+is", "api_key_leak"),
        (r"(?:sk-|api[_-]?key[=:])[A-Za-z0-9_-]{20,}", "credential_pattern"),
        # Extended credential leak patterns
        (r"(?i)(?:the|your)\s+password\s+is[:\s]+\S+", "password_disclosure"),
        (r"(?i)(?:here(?:'s|\s+is)\s+)?(?:the|your)\s+(?:api[_-]?)?(?:key|token|secret)[:\s]+\S+", "secret_disclosure"),
    ]

    def __init__(self, siem_client: SIEMClient | None = None):
        """Initialize guardrails."""
        self._siem = siem_client or get_siem_client()

        self._harmful_patterns = [
            (re.compile(p), t) for p, t in self.HARMFUL_PATTERNS
        ]
        self._hallucination_patterns = [
            (re.compile(p), t) for p, t in self.HALLUCINATION_PATTERNS
        ]
        self._leak_patterns = [
            (re.compile(p), t) for p, t in self.DATA_LEAK_PATTERNS
        ]

    def validate(self, response: str) -> ThreatDetection:
        """
        Validate a response for safety issues.

        Args:
            response: The AI response to validate

        Returns:
            ThreatDetection result
        """
        issues = []

        # Check harmful content
        for pattern, issue_type in self._harmful_patterns:
            if pattern.search(response):
                issues.append(f"harmful:{issue_type}")

        # Check hallucinations
        for pattern, issue_type in self._hallucination_patterns:
            if pattern.search(response):
                issues.append(f"hallucination:{issue_type}")

        # Check data leaks
        for pattern, issue_type in self._leak_patterns:
            if pattern.search(response):
                issues.append(f"leak:{issue_type}")

        # Determine category and risk
        if any("harmful:" in i for i in issues):
            category = ThreatCategory.DATA_LEAK  # Using as catch-all
            risk_level = RiskLevel.CRITICAL
        elif any("leak:" in i for i in issues):
            category = ThreatCategory.DATA_LEAK
            risk_level = RiskLevel.HIGH
        elif any("hallucination:" in i for i in issues):
            category = ThreatCategory.HALLUCINATION
            risk_level = RiskLevel.MEDIUM
        else:
            category = ThreatCategory.PROMPT_INJECTION  # Default
            risk_level = RiskLevel.NONE

        return ThreatDetection(
            detected=len(issues) > 0,
            category=category,
            risk_level=risk_level,
            patterns_matched=issues,
            details=f"Found {len(issues)} potential issues in response",
            recommendation="Review and sanitize response" if issues else "Safe to return"
        )


# =============================================================================
# Tool Output Sanitization
# =============================================================================

class ToolOutputSanitizer:
    """
    Sanitizes outputs from tools before including in context.

    This prevents:
    - Injection attacks via tool outputs
    - Oversized outputs causing context overflow
    - Sensitive data exposure
    """

    # Sensitive patterns to redact
    SENSITIVE_PATTERNS = [
        (r"(?:password|passwd|pwd)\s*[=:]\s*['\"]?[^\s'\"]+", "[REDACTED_PASSWORD]"),
        (r"(?:api[_-]?key|apikey)\s*[=:]\s*['\"]?[^\s'\"]+", "[REDACTED_API_KEY]"),
        (r"(?:secret|token)\s*[=:]\s*['\"]?[^\s'\"]+", "[REDACTED_SECRET]"),
        (r"(?:sk-|api-)[A-Za-z0-9]{20,}", "[REDACTED_KEY]"),
        (r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b", "[REDACTED_SSN]"),
        (r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14})\b", "[REDACTED_CARD]"),
    ]

    # Injection patterns to neutralize
    INJECTION_PATTERNS = [
        (r"(?i)\[SYSTEM\]", "[NEUTRALIZED]"),
        (r"(?i)IGNORE\s+(?:ALL\s+)?PREVIOUS", "[NEUTRALIZED]"),
        (r"<\|(?:im_start|im_end|system)\|>", "[NEUTRALIZED]"),
    ]

    def __init__(
        self,
        max_length: int = 50000,
        truncation_suffix: str = "\n... [OUTPUT TRUNCATED]"
    ):
        """
        Initialize sanitizer.

        Args:
            max_length: Maximum output length
            truncation_suffix: Suffix to add when truncating
        """
        self.max_length = max_length
        self.truncation_suffix = truncation_suffix

        self._sensitive_patterns = [
            (re.compile(p, re.IGNORECASE), r) for p, r in self.SENSITIVE_PATTERNS
        ]
        self._injection_patterns = [
            (re.compile(p), r) for p, r in self.INJECTION_PATTERNS
        ]

    def sanitize(self, output: str, tool_name: str = "unknown") -> SanitizedOutput:
        """
        Sanitize tool output.

        Args:
            output: The tool output to sanitize
            tool_name: Name of the tool (for logging)

        Returns:
            SanitizedOutput result
        """
        original_length = len(output)
        modifications = []
        sanitized = output

        # Redact sensitive patterns
        for pattern, replacement in self._sensitive_patterns:
            if pattern.search(sanitized):
                sanitized = pattern.sub(replacement, sanitized)
                modifications.append(f"redacted:{replacement}")

        # Neutralize injection patterns
        for pattern, replacement in self._injection_patterns:
            if pattern.search(sanitized):
                sanitized = pattern.sub(replacement, sanitized)
                modifications.append(f"neutralized:{replacement}")

        # Truncate if too long
        if len(sanitized) > self.max_length:
            sanitized = sanitized[:self.max_length - len(self.truncation_suffix)] + self.truncation_suffix
            modifications.append(f"truncated:from_{original_length}_to_{len(sanitized)}")

        return SanitizedOutput(
            original_length=original_length,
            sanitized_length=len(sanitized),
            modifications_made=modifications,
            output=sanitized,
            is_safe=len([m for m in modifications if "neutralized" in m]) == 0
        )


# =============================================================================
# Agent Attestation (CBAC)
# =============================================================================

class AgentAttestationManager:
    """
    Manages cryptographic attestations for agent capabilities.

    Implements Capability-Based Access Control (CBAC) where agents
    must present valid attestations to access certain features.
    """

    def __init__(self, signing_key: bytes | None = None):
        """
        Initialize the attestation manager.

        Args:
            signing_key: Secret key for signing attestations.
                        If not provided, generates a random key.
        """
        self._signing_key = signing_key or secrets.token_bytes(32)
        self._issued_attestations: dict[str, AgentAttestation] = {}

    def issue_attestation(
        self,
        agent_id: str,
        capabilities: list[str],
        validity_hours: int = 24,
        issuer: str = "NatLangChain"
    ) -> AgentAttestation:
        """
        Issue a new attestation for an agent.

        Args:
            agent_id: Unique identifier for the agent
            capabilities: List of capabilities to grant
            validity_hours: How long the attestation is valid
            issuer: Who is issuing the attestation

        Returns:
            AgentAttestation
        """
        now = datetime.utcnow()
        expires = datetime.utcnow()
        expires = datetime.fromtimestamp(now.timestamp() + validity_hours * 3600)

        # Create attestation data
        attestation_data = {
            "agent_id": agent_id,
            "capabilities": capabilities,
            "issued_at": now.isoformat() + "Z",
            "expires_at": expires.isoformat() + "Z",
            "issuer": issuer
        }

        # Sign the attestation
        signature = self._sign(json.dumps(attestation_data, sort_keys=True))

        attestation = AgentAttestation(
            agent_id=agent_id,
            capabilities=capabilities,
            issued_at=attestation_data["issued_at"],
            expires_at=attestation_data["expires_at"],
            signature=signature,
            issuer=issuer
        )

        self._issued_attestations[agent_id] = attestation
        return attestation

    def verify_attestation(
        self,
        attestation: AgentAttestation,
        required_capability: str | None = None
    ) -> tuple[bool, str]:
        """
        Verify an attestation is valid.

        Args:
            attestation: The attestation to verify
            required_capability: Optional capability that must be present

        Returns:
            Tuple of (is_valid, reason)
        """
        # Recreate attestation data for signature verification
        attestation_data = {
            "agent_id": attestation.agent_id,
            "capabilities": attestation.capabilities,
            "issued_at": attestation.issued_at,
            "expires_at": attestation.expires_at,
            "issuer": attestation.issuer
        }

        # Verify signature
        expected_signature = self._sign(json.dumps(attestation_data, sort_keys=True))
        if not secrets.compare_digest(attestation.signature, expected_signature):
            return False, "Invalid signature"

        # Check expiration
        expires = datetime.fromisoformat(attestation.expires_at.replace("Z", "+00:00"))
        if datetime.utcnow().replace(tzinfo=expires.tzinfo) > expires:
            return False, "Attestation expired"

        # Check capability if required
        if required_capability and required_capability not in attestation.capabilities:
            return False, f"Missing required capability: {required_capability}"

        return True, "Valid"

    def revoke_attestation(self, agent_id: str) -> bool:
        """Revoke an agent's attestation."""
        if agent_id in self._issued_attestations:
            del self._issued_attestations[agent_id]
            return True
        return False

    def _sign(self, data: str) -> str:
        """Create HMAC signature."""
        return hmac.new(
            self._signing_key,
            data.encode(),
            hashlib.sha256
        ).hexdigest()


# =============================================================================
# Unified Agent Security Manager
# =============================================================================

class AgentSecurityManager:
    """
    Unified manager for all AI/Agent security features.

    Provides a single interface for:
    - Prompt injection detection
    - RAG poisoning detection
    - Response guardrails
    - Tool output sanitization
    - Agent attestation
    """

    def __init__(
        self,
        siem_client: SIEMClient | None = None,
        enable_attestation: bool = True,
        signing_key: bytes | None = None
    ):
        """
        Initialize the security manager.

        Args:
            siem_client: SIEM client for event logging
            enable_attestation: Whether to enable agent attestation
            signing_key: Key for signing attestations
        """
        self._siem = siem_client or get_siem_client()

        # Initialize components
        self.injection_detector = PromptInjectionDetector(self._siem)
        self.poisoning_detector = RAGPoisoningDetector(self._siem)
        self.guardrails = ResponseGuardrails(self._siem)
        self.sanitizer = ToolOutputSanitizer()

        if enable_attestation:
            self.attestation = AgentAttestationManager(signing_key)
        else:
            self.attestation = None

    def check_input(
        self,
        text: str,
        context: str = "user_input"
    ) -> ThreatDetection:
        """
        Check input for security threats.

        Args:
            text: Input text to check
            context: Context ("user_input", "document", "tool_output")

        Returns:
            ThreatDetection result
        """
        return self.injection_detector.detect(text, context)

    def check_document(
        self,
        content: str,
        document_id: str,
        source: str
    ) -> ThreatDetection:
        """
        Check a document for RAG poisoning.

        Args:
            content: Document content
            document_id: Document identifier
            source: Document source

        Returns:
            ThreatDetection result
        """
        return self.poisoning_detector.detect(content, document_id, source)

    def check_response(self, response: str) -> ThreatDetection:
        """
        Check an AI response for safety issues.

        Args:
            response: The response to check

        Returns:
            ThreatDetection result
        """
        return self.guardrails.validate(response)

    def sanitize_tool_output(
        self,
        output: str,
        tool_name: str = "unknown"
    ) -> SanitizedOutput:
        """
        Sanitize tool output before including in context.

        Args:
            output: Tool output to sanitize
            tool_name: Name of the tool

        Returns:
            SanitizedOutput result
        """
        return self.sanitizer.sanitize(output, tool_name)

    def is_input_safe(self, text: str, context: str = "user_input") -> bool:
        """Quick check if input is safe."""
        return not self.check_input(text, context).detected

    def is_response_safe(self, response: str) -> bool:
        """Quick check if response is safe."""
        return not self.check_response(response).detected

    def get_stats(self) -> dict[str, Any]:
        """Get security statistics."""
        return {
            "attestations_issued": len(self.attestation._issued_attestations) if self.attestation else 0,
            "components": {
                "injection_detector": True,
                "poisoning_detector": True,
                "guardrails": True,
                "sanitizer": True,
                "attestation": self.attestation is not None
            }
        }


# =============================================================================
# Global Security Manager
# =============================================================================

_global_agent_security: AgentSecurityManager | None = None


def get_agent_security() -> AgentSecurityManager | None:
    """Get the global agent security manager."""
    return _global_agent_security


def init_agent_security(**kwargs) -> AgentSecurityManager:
    """Initialize the global agent security manager."""
    global _global_agent_security
    _global_agent_security = AgentSecurityManager(**kwargs)
    return _global_agent_security
