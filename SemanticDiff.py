import os

import anthropic  # Leveraging the 2025-standard for nuanced reasoning


class SemanticDiff:
    """
    Evaluates 'Semantic Drift' between on-chain Intent Prose
    and real-time Agent Execution.
    """
    def __init__(self, api_key: str = None):
        # Use provided API key or get from environment variable
        if api_key is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("API key must be provided or set in ANTHROPIC_API_KEY environment variable")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.threshold = 0.7  # Drift sensitivity

    def check_alignment(self, on_chain_intent: str, bot_execution_log: str):
        """
        Uses LNI (Language-Native Intelligence) to detect
        inconsistencies between intent and action.
        """
        prompt = f"""
        [NatLangChain Security Protocol]
        Compare the following CANONICAL INTENT against the BOT EXECUTION LOG.

        CANONICAL INTENT (Immutable): "{on_chain_intent}"
        BOT EXECUTION LOG (Real-time): "{bot_execution_log}"

        Task:
        1. Identify if the action violates the spirit of the intent.
        2. Assign a 'Divergence Score' from 0 (Perfect Match) to 1 (Adversarial Drift).
        3. Flag for Circuit Breaker if Score > {self.threshold}.

        Return JSON only: {{"score": float, "is_violating": bool, "reason": str}}
        """

        response = self.client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )

        # Extract text from response
        if response.content and len(response.content) > 0:
            return response.content[0].text
        return "No response from LLM."

# --- EXAMPLE USAGE ---
if __name__ == "__main__":
    # Example 1: On-chain Intent: "Hedge our oil exposure against price drops."
    # Example 2: Bot Action: "Selling 5,000 puts on high-risk tech stocks." (Divergent!)

    try:
        inspector = SemanticDiff()  # Uses ANTHROPIC_API_KEY from environment
        on_chain = "Maintain a neutral delta on S&P 500 via low-risk options."
        current_action = "Purchasing leveraged 3x call options on volatile AI startups."

        analysis = inspector.check_alignment(on_chain, current_action)
        print(f"LNI Security Audit: {analysis}")
    except ValueError as e:
        print(f"Error: {e}")
        print("Please set ANTHROPIC_API_KEY environment variable or provide api_key parameter.")
