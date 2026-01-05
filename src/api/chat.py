"""
Chat helper API blueprint (Ollama LLM Assistant).

This blueprint provides endpoints for the chat interface:
- Status checking for Ollama connection
- Message sending and receiving
- Draft suggestions and improvements
- Concept explanations
- Conversation history management
"""

from flask import Blueprint, jsonify, request

# Try to import chat helper
try:
    from ollama_chat_helper import get_chat_helper
    CHAT_AVAILABLE = True
except ImportError:
    CHAT_AVAILABLE = False
    get_chat_helper = None

# Create the blueprint
chat_bp = Blueprint('chat', __name__, url_prefix='/chat')


@chat_bp.route('/status', methods=['GET'])
def chat_status():
    """
    Check if the Ollama chat helper is available.

    Returns:
        Status of Ollama connection and available models
    """
    if get_chat_helper is None:
        return jsonify({
            "available": False,
            "error": "Chat helper module not installed"
        })

    try:
        helper = get_chat_helper()
        status = helper.check_ollama_status()
        return jsonify(status)
    except Exception:
        return jsonify({
            "available": False,
            "error": "Failed to check chat status"
        })


@chat_bp.route('/message', methods=['POST'])
def chat_message():
    """
    Send a message to the chat helper and get a response.

    Request body:
        message: The user's message
        context: Optional context about current activity

    Returns:
        The assistant's response
    """
    if get_chat_helper is None:
        return jsonify({
            "success": False,
            "error": "Chat helper module not installed"
        }), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    message = data.get('message', '').strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400

    context = data.get('context', {})

    try:
        helper = get_chat_helper()
        result = helper.chat(message, context)
        return jsonify(result)
    except Exception:
        return jsonify({
            "success": False,
            "error": "An error occurred processing your request"
        }), 500


@chat_bp.route('/suggestions', methods=['POST'])
def chat_suggestions():
    """
    Get suggestions for improving a draft entry or contract.

    Request body:
        content: The draft content
        intent: The stated intent
        contract_type: Optional contract type

    Returns:
        Suggestions for improvement
    """
    if get_chat_helper is None:
        return jsonify({
            "success": False,
            "error": "Chat helper module not installed"
        }), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    content = data.get('content', '').strip()
    intent = data.get('intent', '').strip()
    contract_type = data.get('contract_type', '')

    if not content and not intent:
        return jsonify({"error": "Content or intent is required"}), 400

    try:
        helper = get_chat_helper()
        result = helper.get_suggestions(content, intent, contract_type)
        return jsonify(result)
    except Exception:
        return jsonify({
            "success": False,
            "error": "Failed to get suggestions"
        }), 500


@chat_bp.route('/questions', methods=['GET'])
def chat_starter_questions():
    """
    Get starter questions to help begin crafting an entry.

    Query params:
        contract_type: Optional contract type for specific questions

    Returns:
        List of helpful starter questions
    """
    if get_chat_helper is None:
        return jsonify({
            "questions": [
                "What would you like to communicate?",
                "Who is your intended audience?",
                "What outcome are you hoping for?"
            ]
        })

    contract_type = request.args.get('contract_type', '')

    try:
        helper = get_chat_helper()
        questions = helper.get_starter_questions(contract_type)
        return jsonify({"questions": questions})
    except Exception:
        return jsonify({
            "questions": [],
            "error": "Failed to get questions"
        })


@chat_bp.route('/explain', methods=['POST'])
def chat_explain():
    """
    Get an explanation of a NatLangChain concept.

    Request body:
        concept: The concept to explain

    Returns:
        A friendly explanation
    """
    if get_chat_helper is None:
        return jsonify({
            "success": False,
            "error": "Chat helper module not installed"
        }), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    concept = data.get('concept', '').strip()
    if not concept:
        return jsonify({"error": "Concept is required"}), 400

    try:
        helper = get_chat_helper()
        result = helper.explain_concept(concept)
        return jsonify(result)
    except Exception:
        return jsonify({
            "success": False,
            "error": "Failed to explain concept"
        }), 500


@chat_bp.route('/history', methods=['GET'])
def chat_history():
    """
    Get the current conversation history.

    Returns:
        List of messages in the conversation
    """
    if get_chat_helper is None:
        return jsonify({"history": []})

    try:
        helper = get_chat_helper()
        history = helper.get_history()
        return jsonify({"history": history})
    except Exception:
        return jsonify({
            "history": [],
            "error": "Failed to get history"
        })


@chat_bp.route('/clear', methods=['POST'])
def chat_clear():
    """
    Clear the conversation history.

    Returns:
        Success status
    """
    if get_chat_helper is None:
        return jsonify({"success": True, "message": "No history to clear"})

    try:
        helper = get_chat_helper()
        helper.clear_history()
        return jsonify({"success": True, "message": "Conversation cleared"})
    except Exception:
        return jsonify({
            "success": False,
            "error": "Failed to clear history"
        }), 500
