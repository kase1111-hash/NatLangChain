"""
NatLangChain - Semantic Oracles
Verifies external events against contract spirit using LLM reasoning
Enables intent-based OTC settlement and conditional contract execution
"""

import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from anthropic import Anthropic


class SemanticOracle:
    """
    Semantic Oracle for verifying external events against contract intent.

    Unlike traditional oracles that check price data, semantic oracles verify
    whether real-world events trigger the *spirit* of contract conditions.

    Example: Contract says "if geopolitical instability in the Middle East"
    - Traditional oracle: Can't evaluate vague terms
    - Semantic oracle: Uses LLM to assess whether current events match intent

    As described in Future.md: "uses Semantic Oracles to verify if the event
    triggers the spirit of the 'Geopolitical Contingency' written in the entry"
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize semantic oracle.

        Args:
            api_key: Anthropic API key for LLM reasoning
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY required for semantic oracles")

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"

    def verify_event_trigger(
        self,
        contract_condition: str,
        contract_intent: str,
        event_description: str,
        event_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Verify if an external event triggers a contract condition.

        Uses LLM to assess semantic match between condition and event.

        Args:
            contract_condition: Original contract condition (prose)
            contract_intent: Intent behind the condition
            event_description: Description of external event
            event_data: Optional structured data about event

        Returns:
            Oracle result with trigger decision and reasoning
        """
        try:
            prompt = f"""You are a Semantic Oracle verifying whether an external event triggers a contract condition.

CONTRACT CONDITION (Original Prose):
{contract_condition}

CONTRACT INTENT (Spirit of the Clause):
{contract_intent}

EXTERNAL EVENT:
{event_description}

EVENT DATA:
{json.dumps(event_data or {}, indent=2)}

Task: Determine if this event triggers the contract condition by:
1. Understanding the SPIRIT of the condition (not just literal words)
2. Assessing whether the event matches the underlying intent
3. Considering context and reasonable interpretation
4. Identifying any ambiguities

Example: If condition says "significant market volatility" and event is
"S&P 500 down 5% in one day", you should verify if 5% constitutes
"significant" in the context of the contract's apparent purpose.

Return JSON:
{{
    "triggers_condition": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "detailed explanation of decision",
    "spirit_match": "how event aligns with contract spirit",
    "ambiguities": ["any unclear aspects"],
    "recommended_action": "EXECUTE/HOLD/CLARIFY"
}}"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            # Extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            result = json.loads(response_text)

            return {
                "status": "success",
                "oracle_type": "semantic",
                "verification_timestamp": datetime.utcnow().isoformat(),
                "contract_condition": contract_condition,
                "event_description": event_description,
                "result": result
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "oracle_type": "semantic",
                "result": {
                    "triggers_condition": None,
                    "recommended_action": "ERROR"
                }
            }

    def verify_contingency_clause(
        self,
        contract_prose: str,
        contingency_type: str,
        current_situation: str
    ) -> Dict[str, Any]:
        """
        Verify if a contingency clause has been triggered.

        Common contingencies:
        - Force majeure
        - Material adverse change
        - Geopolitical events
        - Market conditions

        Args:
            contract_prose: Full contract prose
            contingency_type: Type of contingency
            current_situation: Description of current situation

        Returns:
            Contingency verification result
        """
        try:
            prompt = f"""Analyze whether a contingency clause has been triggered.

FULL CONTRACT:
{contract_prose}

CONTINGENCY TYPE: {contingency_type}

CURRENT SITUATION:
{current_situation}

Assess:
1. What was the contract's intended protection?
2. Does the current situation fall within that protection?
3. Would a reasonable party have anticipated this scenario?
4. Is this the kind of event the contingency was meant to cover?

Return JSON:
{{
    "contingency_triggered": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "detailed analysis",
    "contract_intent": "what parties likely intended",
    "current_situation_analysis": "how situation relates to intent",
    "precedent_analogy": "similar cases if applicable",
    "recommended_action": "INVOKE_CLAUSE/CONTINUE/DISPUTE"
}}"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=768,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            # Extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            result = json.loads(response_text)

            return {
                "status": "success",
                "oracle_type": "contingency",
                "contingency_type": contingency_type,
                "verification_timestamp": datetime.utcnow().isoformat(),
                "result": result
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "oracle_type": "contingency"
            }

    def check_otc_settlement_condition(
        self,
        derivative_contract: str,
        market_event: str,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify OTC derivative settlement conditions.

        For interest rate swaps, credit default swaps, etc.
        Checks if market events trigger settlement per contract spirit.

        Args:
            derivative_contract: OTC contract prose
            market_event: Description of market event
            market_data: Relevant market data

        Returns:
            Settlement verification
        """
        try:
            prompt = f"""Verify if an OTC derivative should settle based on a market event.

OTC DERIVATIVE CONTRACT:
{derivative_contract}

MARKET EVENT:
{market_event}

MARKET DATA:
{json.dumps(market_data, indent=2)}

Critical Assessment:
1. What market condition was this derivative hedging against?
2. Has that condition materialized?
3. Does the market data support settlement?
4. Are there any ambiguities in the contract terms?

For example: If contract says "settle if rates rise significantly" and
market shows 2% increase, determine if 2% is "significant" given the
contract's apparent hedging intent.

Return JSON:
{{
    "should_settle": true/false,
    "settlement_amount": "if calculable from contract",
    "confidence": 0.0-1.0,
    "reasoning": "detailed analysis",
    "hedge_intent": "what risk was being hedged",
    "condition_met": "whether that risk materialized",
    "data_supports_settlement": true/false,
    "recommended_action": "SETTLE/HOLD/REVIEW"
}}"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=768,
                messages=[{"role": "user", "content": prompt}]
            )

            response_text = message.content[0].text

            # Extract JSON
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            result = json.loads(response_text)

            return {
                "status": "success",
                "oracle_type": "otc_settlement",
                "verification_timestamp": datetime.utcnow().isoformat(),
                "derivative_contract": derivative_contract,
                "market_event": market_event,
                "result": result
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "oracle_type": "otc_settlement"
            }

    def multi_oracle_consensus(
        self,
        condition: str,
        event: str,
        num_oracles: int = 3
    ) -> Dict[str, Any]:
        """
        Achieve consensus across multiple oracle evaluations.

        Reduces risk of single-oracle error or bias.

        Args:
            condition: Contract condition
            event: External event
            num_oracles: Number of oracle evaluations

        Returns:
            Consensus result
        """
        evaluations = []

        for i in range(num_oracles):
            result = self.verify_event_trigger(
                contract_condition=condition,
                contract_intent="Evaluate condition semantically",
                event_description=event
            )

            if result["status"] == "success":
                evaluations.append(result["result"])

        if not evaluations:
            return {
                "consensus": "FAILED",
                "reason": "All oracle evaluations failed"
            }

        # Count trigger decisions
        trigger_count = sum(1 for e in evaluations if e.get("triggers_condition"))
        no_trigger_count = len(evaluations) - trigger_count

        # Calculate average confidence
        avg_confidence = sum(e.get("confidence", 0.5) for e in evaluations) / len(evaluations)

        # Determine consensus
        if trigger_count > num_oracles / 2:
            consensus_decision = True
        elif no_trigger_count > num_oracles / 2:
            consensus_decision = False
        else:
            consensus_decision = None  # No consensus

        return {
            "consensus_triggers": consensus_decision,
            "oracle_count": num_oracles,
            "trigger_votes": trigger_count,
            "no_trigger_votes": no_trigger_count,
            "average_confidence": round(avg_confidence, 3),
            "evaluations": evaluations,
            "recommended_action": "EXECUTE" if consensus_decision else "HOLD" if consensus_decision == False else "REVIEW"
        }


class SemanticCircuitBreaker:
    """
    Semantic circuit breaker for agent safety.

    Monitors agent actions against stated intent and triggers halts
    when semantic drift exceeds threshold.

    As described in Future.md: "monitors the trade-narrative of Agent-OS bots.
    If an agent's actions drift from its 'Stated Intent'... triggers immediate block"
    """

    def __init__(
        self,
        oracle: SemanticOracle,
        drift_threshold: float = 0.7
    ):
        """
        Initialize circuit breaker.

        Args:
            oracle: Semantic oracle for evaluations
            drift_threshold: Drift score threshold for triggering (0.0-1.0)
        """
        self.oracle = oracle
        self.drift_threshold = drift_threshold
        self.violations = []

    def check_agent_action(
        self,
        stated_intent: str,
        proposed_action: str,
        agent_id: str
    ) -> Dict[str, Any]:
        """
        Check if proposed agent action aligns with stated intent.

        Args:
            stated_intent: Agent's stated intent from blockchain
            proposed_action: Action agent wants to take
            agent_id: Agent identifier

        Returns:
            Circuit breaker decision
        """
        # Use oracle to check semantic alignment
        result = self.oracle.verify_event_trigger(
            contract_condition=stated_intent,
            contract_intent="Agent authorization scope",
            event_description=f"Agent {agent_id} proposes: {proposed_action}"
        )

        if result["status"] != "success":
            return {
                "allowed": False,
                "reason": "Oracle evaluation failed",
                "circuit_breaker_triggered": True
            }

        oracle_result = result["result"]

        # Check if action aligns with intent
        aligns = oracle_result.get("triggers_condition", False)
        confidence = oracle_result.get("confidence", 0.0)

        # Calculate drift (inverse of alignment)
        drift_score = 1.0 - confidence if aligns else confidence

        # Trigger if drift exceeds threshold
        triggered = drift_score > self.drift_threshold

        if triggered:
            violation = {
                "timestamp": datetime.utcnow().isoformat(),
                "agent_id": agent_id,
                "stated_intent": stated_intent,
                "proposed_action": proposed_action,
                "drift_score": drift_score,
                "reasoning": oracle_result.get("reasoning")
            }
            self.violations.append(violation)

        return {
            "allowed": not triggered,
            "drift_score": round(drift_score, 3),
            "threshold": self.drift_threshold,
            "circuit_breaker_triggered": triggered,
            "reasoning": oracle_result.get("reasoning"),
            "recommended_action": "BLOCK" if triggered else "ALLOW",
            "violation_logged": triggered
        }
