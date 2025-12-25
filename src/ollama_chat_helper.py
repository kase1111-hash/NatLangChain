"""
NatLangChain - Ollama Chat Helper
A friendly AI assistant that helps users craft clear, well-structured contracts.
This is a quality helper, not an enforcer - it asks questions and offers suggestions.
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ChatMessage:
    """Represents a single message in the conversation."""
    role: str  # 'user' or 'assistant'
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ConversationContext:
    """Context about the current user activity."""
    current_view: str = "dashboard"
    selected_entries: List[str] = field(default_factory=list)
    draft_content: str = ""
    draft_intent: str = ""
    is_contract: bool = False
    contract_type: str = ""


class OllamaChatHelper:
    """
    A friendly AI assistant that helps users create clear, well-structured contracts.
    Uses Ollama for local LLM inference.
    """

    # Default Ollama endpoint
    DEFAULT_OLLAMA_URL = "http://localhost:11434"

    # Default model - mistral is good for conversation, llama2 is also available
    DEFAULT_MODEL = "mistral"

    # System prompt that guides the helper's behavior
    SYSTEM_PROMPT = """You are a friendly and helpful contract writing assistant for NatLangChain, a natural language blockchain platform. Your role is to GUIDE users in creating clear, well-structured contracts - NOT to write contracts for them.

CRITICAL RULES - YOU MUST FOLLOW THESE:
1. NEVER write a complete contract or entry for the user
2. NEVER provide copy-paste ready contract text
3. NEVER draft full terms, clauses, or agreements
4. If asked to "write my contract" or similar, politely refuse and explain why

Instead, you should:
- Ask clarifying questions to help users think through their needs
- Suggest what elements they should include (but don't write them)
- Point out what's missing or unclear in their drafts
- Explain concepts and give brief examples (1 sentence max)
- Guide them to express their OWN intent in their OWN words

WHY THIS MATTERS (explain to users if they ask):
Per NCIP-004, contracts require "Proof of Understanding" - you must be able to explain the contract in your own words. Copy-pasting defeats this requirement and could invalidate your agreement. The contract must genuinely reflect YOUR understanding and intent.

You are a HELPER, not a ghostwriter. Your approach should be:
- Ask clarifying questions to understand what the user wants to achieve
- Point out what details are missing: "Have you considered specifying...?"
- Identify ambiguities: "The phrase 'soon' could mean different things..."
- Suggest structure: "You might want to cover: scope, timeline, payment, what-ifs"
- Encourage: "That's a good start! Now consider adding..."

Key concepts in NatLangChain:
- **Entry**: A natural language statement recorded on the blockchain
- **Intent**: The purpose or goal behind an entry
- **Contract**: A special entry type that represents an offer, request, or agreement
- **Contract Types**: offer (providing something), seek (requesting something), proposal, response, closure
- **Proof of Understanding**: You must demonstrate YOU understand what you're agreeing to

When helping with contracts, ASK about:
1. What exactly are you offering or seeking?
2. Who is this for? Any restrictions?
3. What's the timeline or deadline?
4. What's the price/exchange/compensation?
5. What happens if something goes wrong?
6. How will you both know it's complete?

Respond in a conversational, friendly tone. Keep responses concise.
Focus on QUESTIONS and GUIDANCE, not providing ready-made text.

GOOD response: "What timeline are you thinking? A week? A month? Be specific."
BAD response: "Here's what you should write: 'I will deliver within 2 weeks...'"

If the user shares draft content, point out what's good and what needs clarification."""

    def __init__(
        self,
        ollama_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize the chat helper.

        Args:
            ollama_url: URL for the Ollama API (default: http://localhost:11434)
            model: Model to use (default: mistral)
        """
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", self.DEFAULT_OLLAMA_URL)
        self.model = model or os.getenv("OLLAMA_MODEL", self.DEFAULT_MODEL)
        self.conversation_history: List[ChatMessage] = []
        self.context = ConversationContext()

    def set_context(self, context: Dict[str, Any]) -> None:
        """
        Update the conversation context.

        Args:
            context: Dictionary with context information
        """
        self.context = ConversationContext(
            current_view=context.get("current_view", "dashboard"),
            selected_entries=context.get("selected_entries", []),
            draft_content=context.get("draft_content", ""),
            draft_intent=context.get("draft_intent", ""),
            is_contract=context.get("is_contract", False),
            contract_type=context.get("contract_type", "")
        )

    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.conversation_history = []

    def _build_context_prompt(self) -> str:
        """Build a context-aware addition to the system prompt."""
        context_parts = []

        if self.context.current_view:
            view_descriptions = {
                "dashboard": "viewing the blockchain dashboard",
                "explorer": "exploring the blockchain",
                "submit": "creating a new entry",
                "contracts": "viewing contracts",
                "search": "searching the blockchain"
            }
            view_desc = view_descriptions.get(
                self.context.current_view,
                f"on the {self.context.current_view} page"
            )
            context_parts.append(f"The user is currently {view_desc}.")

        if self.context.draft_content:
            context_parts.append(f"\nTheir current draft content is:\n\"{self.context.draft_content}\"")

        if self.context.draft_intent:
            context_parts.append(f"\nTheir stated intent is: \"{self.context.draft_intent}\"")

        if self.context.is_contract:
            context_parts.append(f"\nThis is a contract of type: {self.context.contract_type}")

        if context_parts:
            return "\n\nCurrent context:\n" + "\n".join(context_parts)
        return ""

    def _build_messages(self, user_message: str) -> List[Dict[str, str]]:
        """Build the message list for the Ollama API."""
        messages = []

        # Add system prompt with context
        system_content = self.SYSTEM_PROMPT + self._build_context_prompt()
        messages.append({"role": "system", "content": system_content})

        # Add conversation history
        for msg in self.conversation_history[-10:]:  # Keep last 10 messages for context
            messages.append({"role": msg.role, "content": msg.content})

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        return messages

    def check_ollama_status(self) -> Dict[str, Any]:
        """
        Check if Ollama is running and accessible.

        Returns:
            Status dictionary with 'available' boolean and 'models' list
        """
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                return {
                    "available": True,
                    "models": models,
                    "current_model": self.model,
                    "model_available": self.model in models or any(self.model in m for m in models)
                }
        except requests.exceptions.RequestException:
            pass

        return {
            "available": False,
            "models": [],
            "current_model": self.model,
            "model_available": False
        }

    def chat(self, user_message: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a message and get a response.

        Args:
            user_message: The user's message
            context: Optional context update

        Returns:
            Dictionary with 'success', 'response', and optional 'error'
        """
        if context:
            self.set_context(context)

        # Add user message to history
        self.conversation_history.append(ChatMessage(role="user", content=user_message))

        try:
            # Build messages for Ollama
            messages = self._build_messages(user_message)

            # Call Ollama API
            response = requests.post(
                f"{self.ollama_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                    }
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                assistant_message = data.get("message", {}).get("content", "")

                # Add assistant response to history
                self.conversation_history.append(
                    ChatMessage(role="assistant", content=assistant_message)
                )

                return {
                    "success": True,
                    "response": assistant_message,
                    "model": self.model
                }
            else:
                error_msg = f"Ollama returned status {response.status_code}"
                return {
                    "success": False,
                    "response": None,
                    "error": error_msg
                }

        except requests.exceptions.ConnectionError:
            return {
                "success": False,
                "response": None,
                "error": "Cannot connect to Ollama. Make sure Ollama is running (ollama serve)"
            }
        except requests.exceptions.Timeout:
            return {
                "success": False,
                "response": None,
                "error": "Request timed out. The model might be loading or busy."
            }
        except Exception as e:
            return {
                "success": False,
                "response": None,
                "error": str(e)
            }

    def get_suggestions(self, content: str, intent: str, contract_type: str = "") -> Dict[str, Any]:
        """
        Get specific suggestions for improving a contract or entry.

        Args:
            content: The draft content
            intent: The stated intent
            contract_type: Type of contract (if applicable)

        Returns:
            Dictionary with suggestions
        """
        # Update context
        self.set_context({
            "current_view": "submit",
            "draft_content": content,
            "draft_intent": intent,
            "is_contract": bool(contract_type),
            "contract_type": contract_type
        })

        # Craft a specific request for suggestions
        prompt = f"""Please analyze this draft and provide specific suggestions to improve clarity:

Content: "{content}"
Intent: "{intent}"
{"Contract Type: " + contract_type if contract_type else ""}

Provide 2-3 specific, actionable suggestions. For each suggestion:
1. Identify what could be improved
2. Explain why it matters
3. Give a concrete example of how to fix it

Be friendly and constructive."""

        return self.chat(prompt)

    def get_starter_questions(self, contract_type: str = "") -> List[str]:
        """
        Get starter questions to help the user begin crafting their entry.

        Args:
            contract_type: Type of contract being created

        Returns:
            List of helpful starter questions
        """
        general_questions = [
            "What's the main thing you want to communicate or achieve?",
            "Who is this intended for?",
            "Are there any deadlines or timeframes involved?",
        ]

        contract_questions = {
            "offer": [
                "What service or product are you offering?",
                "What are your terms or conditions?",
                "How should interested parties reach you?",
            ],
            "seek": [
                "What exactly are you looking for?",
                "What's your budget or what can you offer in exchange?",
                "When do you need this by?",
            ],
            "proposal": [
                "What problem does your proposal solve?",
                "What are the key deliverables?",
                "What's the timeline and compensation structure?",
            ],
            "response": [
                "Which offer or request are you responding to?",
                "Do you accept, counter, or decline?",
                "What modifications or conditions do you want to add?",
            ],
            "closure": [
                "What was the original agreement?",
                "Has the work been completed satisfactorily?",
                "Are there any final notes or acknowledgments?",
            ],
        }

        if contract_type and contract_type in contract_questions:
            return contract_questions[contract_type]
        return general_questions

    def explain_concept(self, concept: str) -> Dict[str, Any]:
        """
        Explain a NatLangChain concept in simple terms.

        Args:
            concept: The concept to explain

        Returns:
            Dictionary with explanation
        """
        prompt = f"""Please explain the NatLangChain concept of "{concept}" in simple, friendly terms.

Keep your explanation:
- Brief (2-3 sentences for the main explanation)
- Accessible to non-technical users
- Focused on why it matters to the user

If you're not sure about a specific concept, explain what it might mean in the context of a natural language blockchain."""

        return self.chat(prompt)

    def get_history(self) -> List[Dict[str, str]]:
        """
        Get the conversation history.

        Returns:
            List of message dictionaries
        """
        return [
            {"role": msg.role, "content": msg.content, "timestamp": msg.timestamp}
            for msg in self.conversation_history
        ]


# Singleton instance for the API to use
_chat_helper_instance: Optional[OllamaChatHelper] = None


def get_chat_helper() -> OllamaChatHelper:
    """Get or create the chat helper singleton."""
    global _chat_helper_instance
    if _chat_helper_instance is None:
        _chat_helper_instance = OllamaChatHelper()
    return _chat_helper_instance
