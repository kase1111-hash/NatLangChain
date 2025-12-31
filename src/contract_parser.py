"""
NatLangChain - Contract Parser
Parses natural language contract entries and extracts structured terms
Enables self-seeking live contracts with AI-mediated matching
"""

import json
import os
import re
from typing import Any

from anthropic import Anthropic


class ContractParser:
    """
    Parses natural language contract entries and extracts structured terms.

    Supports multiple formats:
    - Tagged format: "[CONTRACT: OFFER] description [TERMS: key=value, ...]"
    - Natural format: Uses LLM to extract terms from pure prose
    """

    # Contract types
    TYPE_OFFER = "offer"
    TYPE_SEEK = "seek"
    TYPE_PROPOSAL = "proposal"
    TYPE_RESPONSE = "response"
    TYPE_CLOSURE = "closure"
    TYPE_PAYOUT = "payout"

    # Contract statuses
    STATUS_OPEN = "open"
    STATUS_MATCHED = "matched"
    STATUS_NEGOTIATING = "negotiating"
    STATUS_CLOSED = "closed"
    STATUS_CANCELLED = "cancelled"

    def __init__(self, api_key: str | None = None):
        """
        Initialize contract parser.

        Args:
            api_key: Anthropic API key for LLM-based term extraction
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=self.api_key) if self.api_key else None
        self.model = "claude-3-5-sonnet-20241022"

    def is_contract(self, content: str) -> bool:
        """
        Check if content represents a contract.

        Args:
            content: Natural language content

        Returns:
            True if content is a contract
        """
        # Check for explicit contract tags
        if re.search(r'\[CONTRACT:', content, re.IGNORECASE):
            return True

        # Check for contract keywords
        contract_keywords = [
            'offer', 'seeking', 'contract for', 'proposal',
            'terms:', 'fee:', 'escrow:', 'facilitation:'
        ]

        content_lower = content.lower()
        return any(keyword in content_lower for keyword in contract_keywords)

    def parse_contract(self, content: str, use_llm: bool = True) -> dict[str, Any]:
        """
        Parse contract from natural language.

        Args:
            content: Natural language contract content
            use_llm: Whether to use LLM for advanced parsing

        Returns:
            Dictionary with contract metadata
        """
        contract_data = {
            "is_contract": False,
            "contract_type": None,
            "terms": {},
            "status": self.STATUS_OPEN,
            "links": [],  # Links to other contract hashes
            "match_score": None,
            "negotiation_round": 0
        }

        if not self.is_contract(content):
            return contract_data

        contract_data["is_contract"] = True

        # Parse explicit tags
        contract_data.update(self._parse_tagged_format(content))

        # Use LLM for advanced term extraction if available
        if use_llm and self.client and not contract_data["terms"]:
            llm_terms = self._llm_extract_terms(content)
            if llm_terms:
                contract_data["terms"] = llm_terms

        return contract_data

    def _parse_tagged_format(self, content: str) -> dict[str, Any]:
        """
        Parse explicitly tagged contract format.

        Format: "[CONTRACT: TYPE] description [TERMS: key=value, key=value]"

        Args:
            content: Contract content

        Returns:
            Parsed contract data
        """
        result = {}

        # Extract contract type
        type_match = re.search(r'\[CONTRACT:\s*(\w+)\]', content, re.IGNORECASE)
        if type_match:
            contract_type = type_match.group(1).lower()
            if contract_type in [self.TYPE_OFFER, self.TYPE_SEEK, self.TYPE_PROPOSAL,
                                 self.TYPE_RESPONSE, self.TYPE_CLOSURE, self.TYPE_PAYOUT]:
                result["contract_type"] = contract_type

        # Extract terms
        terms_match = re.search(r'\[TERMS:\s*(.*?)\]', content, re.IGNORECASE)
        if terms_match:
            terms_str = terms_match.group(1)
            terms = {}

            # Parse key=value pairs
            for pair in re.split(r',\s*', terms_str):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    terms[key.strip()] = value.strip()

            result["terms"] = terms

        # Extract links to other contracts
        links_match = re.search(r'\[LINKS:\s*(.*?)\]', content, re.IGNORECASE)
        if links_match:
            links_str = links_match.group(1)
            result["links"] = [link.strip() for link in links_str.split(',')]

        # Extract response reference
        response_match = re.search(r'\[RESPONSE TO:\s*([a-f0-9]+)\]', content, re.IGNORECASE)
        if response_match:
            result["contract_type"] = self.TYPE_RESPONSE
            result["links"] = [response_match.group(1)]

        # Extract match score
        score_match = re.search(r'\[PROPOSAL:\s*Match\s*(\d+)%\]', content, re.IGNORECASE)
        if score_match:
            result["contract_type"] = self.TYPE_PROPOSAL
            result["match_score"] = int(score_match.group(1))

        return result

    def _llm_extract_terms(self, content: str) -> dict[str, str] | None:
        """
        Use LLM to extract contract terms from natural prose.

        Args:
            content: Contract content

        Returns:
            Extracted terms or None if extraction fails
        """
        if not self.client:
            return None

        try:
            prompt = f"""Extract structured contract terms from this natural language contract:

{content}

Identify and extract key terms such as:
- fee/price/cost
- escrow requirements
- facilitation percentage
- deadline/timeline
- quantities/amounts
- payment method
- conditions

Return JSON only:
{{
    "fee": "extracted fee if present",
    "escrow": "escrow details if present",
    "facilitation": "facilitation percentage if present",
    "deadline": "deadline if present",
    "other_terms": {{"key": "value"}}
}}

If a term is not present, omit it. Return {{}} if no clear terms found."""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )

            # Safe access to API response
            if not message.content:
                raise ValueError("Empty response from API: no content returned during term extraction")
            if not hasattr(message.content[0], 'text'):
                raise ValueError("Invalid API response format: missing 'text' attribute in term extraction")

            response_text = message.content[0].text

            # Extract JSON with validation
            response_text = self._extract_json_from_response(response_text)

            try:
                terms = json.loads(response_text)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse term extraction JSON: {e.msg} at position {e.pos}")

            # Flatten other_terms
            if "other_terms" in terms:
                other = terms.pop("other_terms")
                terms.update(other)

            return terms if terms else None

        except json.JSONDecodeError as e:
            print(f"LLM term extraction failed - JSON parsing error: {e}")
            return None
        except ValueError as e:
            print(f"LLM term extraction failed - validation error: {e}")
            return None
        except Exception as e:
            print(f"LLM term extraction failed - unexpected error: {e}")
            return None

    def _extract_json_from_response(self, response_text: str) -> str:
        """
        Extract JSON from a response that may contain markdown code blocks.

        Args:
            response_text: Raw response text

        Returns:
            Extracted JSON string

        Raises:
            ValueError: If JSON extraction fails
        """
        if not response_text or not response_text.strip():
            raise ValueError("Empty response text received")

        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            if json_end == -1:
                raise ValueError("Malformed response: unclosed JSON code block")
            return response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            if json_end == -1:
                raise ValueError("Malformed response: unclosed code block")
            return response_text[json_start:json_end].strip()

        return response_text.strip()

    def validate_contract_clarity(self, content: str) -> tuple[bool, str]:
        """
        Validate that contract terms are unambiguous.

        Args:
            content: Contract content

        Returns:
            Tuple of (is_valid, reason)
        """
        if not self.client:
            # Without LLM, do basic checks
            if len(content.strip()) < 20:
                return False, "Contract too short"

            vague_terms = ['maybe', 'soon', 'approximately', 'some', 'later']
            content_lower = content.lower()

            for term in vague_terms:
                if term in content_lower:
                    return False, f"Vague term detected: '{term}'"

            return True, "Basic validation passed"

        try:
            prompt = f"""Analyze this contract for clarity and enforceability:

{content}

Check for:
1. Vague or ambiguous terms (e.g., "soon", "some", "approximately")
2. Missing critical details (amounts, deadlines, parties)
3. Contradictions or unclear conditions

Return JSON:
{{
    "is_clear": true/false,
    "ambiguities": ["list of ambiguous terms/issues"],
    "missing_critical": ["list of missing critical information"],
    "recommendation": "ACCEPT/NEEDS_CLARIFICATION/REJECT",
    "reasoning": "brief explanation"
}}"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )

            # Safe access to API response
            if not message.content:
                raise ValueError("Empty response from API: no content returned during clarity validation")
            if not hasattr(message.content[0], 'text'):
                raise ValueError("Invalid API response format: missing 'text' attribute in clarity validation")

            response_text = message.content[0].text

            # Extract JSON with validation
            response_text = self._extract_json_from_response(response_text)

            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse clarity validation JSON: {e.msg} at position {e.pos}")

            if result.get("recommendation") == "REJECT":
                issues = result.get("ambiguities", []) + result.get("missing_critical", [])
                return False, f"Contract validation failed: {'; '.join(issues)}"

            if result.get("recommendation") == "NEEDS_CLARIFICATION":
                return False, f"Contract needs clarification: {result.get('reasoning', 'Unclear terms')}"

            return True, "Contract is clear and enforceable"

        except json.JSONDecodeError as e:
            print(f"Contract validation failed - JSON parsing error: {e}")
            return False, f"JSON parsing error during validation: {e!s}"
        except ValueError as e:
            print(f"Contract validation failed - validation error: {e}")
            return False, f"Validation error: {e!s}"
        except Exception as e:
            print(f"Contract validation failed - unexpected error: {e}")
            return False, f"Unexpected validation error: {e!s}"

    def format_contract(
        self,
        contract_type: str,
        content: str,
        terms: dict[str, str] | None = None,
        links: list[str] | None = None
    ) -> str:
        """
        Format a contract with proper tags.

        Args:
            contract_type: Type of contract (offer, seek, etc.)
            content: Natural language content
            terms: Contract terms
            links: Links to other contracts

        Returns:
            Formatted contract string
        """
        parts = [f"[CONTRACT: {contract_type.upper()}]"]
        parts.append(content)

        if terms:
            terms_str = ", ".join(f"{k}={v}" for k, v in terms.items())
            parts.append(f"[TERMS: {terms_str}]")

        if links:
            links_str = ", ".join(links)
            parts.append(f"[LINKS: {links_str}]")

        return " ".join(parts)
