"""
NatLangChain - Contract Matcher
Finds semantic matches between contracts using LLM-based similarity scoring
Enables autonomous contract matching and proposal generation
"""

import json
import os
from typing import Any

from anthropic import Anthropic

from blockchain import NatLangChain, NaturalLanguageEntry
from contract_parser import ContractParser


class ContractMatcher:
    """
    Finds and proposes matches between compatible contracts.

    Uses LLM to compute semantic similarity and generate merged proposals.
    Miners earn fees for successful matches.
    """

    def __init__(self, api_key: str | None = None, match_threshold: int = 80):
        """
        Initialize contract matcher.

        Args:
            api_key: Anthropic API key for LLM matching
            match_threshold: Minimum match score (0-100) to propose
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required for contract matching")

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.match_threshold = match_threshold
        self.parser = ContractParser(api_key)

    def find_matches(
        self, blockchain: NatLangChain, pending_entries: list[NaturalLanguageEntry], miner_id: str
    ) -> list[NaturalLanguageEntry]:
        """
        Find matches for pending contract entries against open contracts.

        Args:
            blockchain: The blockchain to search for open contracts
            pending_entries: New pending entries to match
            miner_id: ID of the miner proposing matches

        Returns:
            List of proposal entries for matched contracts
        """
        proposals = []

        # Get all open contracts from the blockchain
        open_contracts = self._get_open_contracts(blockchain)

        # Check each pending contract entry
        for pending in pending_entries:
            # Skip if not a contract
            if not pending.metadata.get("is_contract"):
                continue

            # Skip if not an offer or seek
            contract_type = pending.metadata.get("contract_type")
            if contract_type not in [ContractParser.TYPE_OFFER, ContractParser.TYPE_SEEK]:
                continue

            # Find matches
            for existing in open_contracts:
                # Don't match same types (offer with offer, seek with seek)
                existing_type = existing["metadata"].get("contract_type")
                if contract_type == existing_type:
                    continue

                # Compute semantic match
                match_result = self._compute_match(
                    pending.content,
                    pending.intent,
                    pending.metadata.get("terms", {}),
                    existing["content"],
                    existing["intent"],
                    existing["metadata"].get("terms", {}),
                )

                if match_result["score"] >= self.match_threshold:
                    # Generate proposal
                    proposal = self._generate_proposal(pending, existing, match_result, miner_id)
                    proposals.append(proposal)

        return proposals

    def _get_open_contracts(self, blockchain: NatLangChain) -> list[dict[str, Any]]:
        """
        Get all open contracts from the blockchain.

        Args:
            blockchain: The blockchain to search

        Returns:
            List of open contract entries with metadata
        """
        open_contracts = []

        for block in blockchain.chain:
            for entry in block.entries:
                # Check if it's a contract
                if not entry.metadata.get("is_contract"):
                    continue

                # Check if it's open
                status = entry.metadata.get("status", ContractParser.STATUS_OPEN)
                if status != ContractParser.STATUS_OPEN:
                    continue

                # Add to list with block info
                open_contracts.append(
                    {
                        "content": entry.content,
                        "author": entry.author,
                        "intent": entry.intent,
                        "metadata": entry.metadata,
                        "timestamp": entry.timestamp,
                        "block_index": block.index,
                        "block_hash": block.hash,
                    }
                )

        return open_contracts

    def _compute_match(
        self,
        content1: str,
        intent1: str,
        terms1: dict[str, str],
        content2: str,
        intent2: str,
        terms2: dict[str, str],
    ) -> dict[str, Any]:
        """
        Compute semantic match score between two contracts.

        Args:
            content1: Content of first contract
            intent1: Intent of first contract
            terms1: Terms of first contract
            content2: Content of second contract
            intent2: Intent of second contract
            terms2: Terms of second contract

        Returns:
            Match result with score and analysis
        """
        try:
            prompt = f"""Rate the semantic match between these two contracts on a scale of 0-100.

CONTRACT A:
Intent: {intent1}
Content: {content1}
Terms: {json.dumps(terms1, indent=2)}

CONTRACT B:
Intent: {intent2}
Content: {content2}
Terms: {json.dumps(terms2, indent=2)}

Analyze:
1. Do they represent complementary offers (e.g., one offers what the other seeks)?
2. Are the terms compatible (e.g., price ranges overlap, timelines align)?
3. Is there semantic alignment in intent and requirements?

Return JSON:
{{
    "score": 0-100,
    "compatibility": "description of how they match",
    "conflicts": ["list any term conflicts or incompatibilities"],
    "recommendation": "MATCH/PARTIAL/NO_MATCH",
    "reasoning": "explanation of score"
}}"""

            message = self.client.messages.create(
                model=self.model, max_tokens=512, messages=[{"role": "user", "content": prompt}]
            )

            # Safe access to API response
            if not message.content:
                raise ValueError(
                    "Empty response from API: no content returned during match computation"
                )
            if not hasattr(message.content[0], "text"):
                raise ValueError("Invalid API response format: missing 'text' attribute")

            response_text = message.content[0].text

            # Extract JSON with validation
            response_text = self._extract_json_from_response(response_text)

            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse match result JSON: {e.msg} at position {e.pos}")

            return result

        except json.JSONDecodeError as e:
            print(f"Match computation failed - JSON parsing error: {e}")
            return {
                "score": 0,
                "compatibility": "",
                "conflicts": [f"JSON parsing error: {e!s}"],
                "recommendation": "NO_MATCH",
                "reasoning": f"Failed to parse API response: {e!s}",
            }
        except ValueError as e:
            print(f"Match computation failed - validation error: {e}")
            return {
                "score": 0,
                "compatibility": "",
                "conflicts": [str(e)],
                "recommendation": "NO_MATCH",
                "reasoning": f"API response validation failed: {e!s}",
            }
        except Exception as e:
            print(f"Match computation failed - unexpected error: {e}")
            return {
                "score": 0,
                "compatibility": "",
                "conflicts": [str(e)],
                "recommendation": "NO_MATCH",
                "reasoning": f"Unexpected error: {e!s}",
            }

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

    def _generate_proposal(
        self,
        pending: NaturalLanguageEntry,
        existing: dict[str, Any],
        match_result: dict[str, Any],
        miner_id: str,
    ) -> NaturalLanguageEntry:
        """
        Generate a proposal entry for a matched pair.

        Args:
            pending: Pending contract entry
            existing: Existing open contract
            match_result: Match analysis result
            miner_id: ID of miner proposing the match

        Returns:
            Proposal entry
        """
        try:
            # Generate merged proposal prose
            prompt = f"""Generate a contract proposal that merges these two matched contracts:

CONTRACT A (Pending):
{pending.content}
Terms: {json.dumps(pending.metadata.get("terms", {}), indent=2)}

CONTRACT B (Existing):
{existing["content"]}
Terms: {json.dumps(existing["metadata"].get("terms", {}), indent=2)}

MATCH ANALYSIS:
Score: {match_result["score"]}%
{match_result["compatibility"]}

Create a natural language proposal that:
1. References both parties (authors: {pending.author} and {existing["author"]})
2. Synthesizes the compatible terms
3. Highlights the match compatibility
4. Suggests next steps for finalization

Write in clear, contract-appropriate language."""

            message = self.client.messages.create(
                model=self.model, max_tokens=512, messages=[{"role": "user", "content": prompt}]
            )

            # Safe access to API response
            if not message.content:
                raise ValueError(
                    "Empty response from API: no content returned during proposal generation"
                )
            if not hasattr(message.content[0], "text"):
                raise ValueError(
                    "Invalid API response format: missing 'text' attribute in proposal generation"
                )

            merged_prose = message.content[0].text.strip()

            # Create proposal entry
            proposal_content = f"[PROPOSAL: Match {match_result['score']}%] {merged_prose}"

            # Merge terms from both contracts
            merged_terms = {}
            merged_terms.update(existing["metadata"].get("terms", {}))
            merged_terms.update(pending.metadata.get("terms", {}))
            merged_terms["miner"] = miner_id
            merged_terms["match_score"] = str(match_result["score"])

            # Create the proposal entry
            proposal = NaturalLanguageEntry(
                content=proposal_content,
                author=miner_id,
                intent=f"Propose match between {pending.author} and {existing['author']}",
                metadata={
                    "is_contract": True,
                    "contract_type": ContractParser.TYPE_PROPOSAL,
                    "status": ContractParser.STATUS_MATCHED,
                    "match_score": match_result["score"],
                    "links": [pending.author, existing["author"]],  # Would use hashes in production
                    "terms": merged_terms,
                    "compatibility": match_result.get("compatibility", ""),
                    "conflicts": match_result.get("conflicts", []),
                },
            )

            return proposal

        except Exception as e:
            print(f"Proposal generation failed: {e}")
            # Return a basic proposal
            return NaturalLanguageEntry(
                content=f"[PROPOSAL: Match {match_result['score']}%] Match proposal between {pending.author} and {existing['author']}",
                author=miner_id,
                intent="Contract match proposal",
                metadata={
                    "is_contract": True,
                    "contract_type": ContractParser.TYPE_PROPOSAL,
                    "status": ContractParser.STATUS_MATCHED,
                    "match_score": match_result["score"],
                    "error": str(e),
                },
            )

    def mediate_negotiation(
        self,
        original_proposal: str,
        original_terms: dict[str, str],
        counter_response: str,
        counter_terms: dict[str, str],
        round_number: int,
    ) -> dict[str, Any]:
        """
        Mediate between original proposal and counter-response.

        Args:
            original_proposal: Original proposal content
            original_terms: Original proposed terms
            counter_response: Counter-offer content
            counter_terms: Counter-offer terms
            round_number: Current negotiation round

        Returns:
            Mediation result with suggestion
        """
        try:
            prompt = f"""You are mediating a contract negotiation (Round {round_number}).

ORIGINAL PROPOSAL:
{original_proposal}
Terms: {json.dumps(original_terms, indent=2)}

COUNTER-OFFER:
{counter_response}
Terms: {json.dumps(counter_terms, indent=2)}

As a neutral mediator:
1. Identify points of agreement
2. Highlight remaining differences
3. Suggest a fair compromise
4. Recommend acceptance, further negotiation, or termination

Return JSON:
{{
    "points_of_agreement": ["list of agreed terms"],
    "differences": ["list of remaining differences"],
    "suggested_compromise": "proposed middle ground",
    "recommended_action": "ACCEPT/CONTINUE/TERMINATE",
    "reasoning": "explanation",
    "revised_terms": {{"suggested merged terms"}}
}}"""

            message = self.client.messages.create(
                model=self.model, max_tokens=512, messages=[{"role": "user", "content": prompt}]
            )

            # Safe access to API response
            if not message.content:
                raise ValueError("Empty response from API: no content returned during mediation")
            if not hasattr(message.content[0], "text"):
                raise ValueError(
                    "Invalid API response format: missing 'text' attribute in mediation"
                )

            response_text = message.content[0].text

            # Extract JSON with validation
            response_text = self._extract_json_from_response(response_text)

            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"Failed to parse mediation result JSON: {e.msg} at position {e.pos}"
                )

            return result

        except json.JSONDecodeError as e:
            print(f"Mediation failed - JSON parsing error: {e}")
            return {
                "points_of_agreement": [],
                "differences": [],
                "suggested_compromise": "",
                "recommended_action": "TERMINATE",
                "reasoning": f"JSON parsing error: {e!s}",
                "revised_terms": {},
            }
        except ValueError as e:
            print(f"Mediation failed - validation error: {e}")
            return {
                "points_of_agreement": [],
                "differences": [],
                "suggested_compromise": "",
                "recommended_action": "TERMINATE",
                "reasoning": f"Validation error: {e!s}",
                "revised_terms": {},
            }
        except Exception as e:
            print(f"Mediation failed - unexpected error: {e}")
            return {
                "points_of_agreement": [],
                "differences": [],
                "suggested_compromise": "",
                "recommended_action": "TERMINATE",
                "reasoning": f"Unexpected error: {e!s}",
                "revised_terms": {},
            }
