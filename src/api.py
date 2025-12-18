"""
NatLangChain - REST API
API endpoints for Agent OS to interact with the blockchain
"""

import os
import json
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify
from dotenv import load_dotenv

from blockchain import NatLangChain, NaturalLanguageEntry, Block
from validator import ProofOfUnderstanding, HybridValidator


# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Initialize blockchain and validator
blockchain = NatLangChain()
llm_validator = None
hybrid_validator = None

# Data file for persistence
CHAIN_DATA_FILE = os.getenv("CHAIN_DATA_FILE", "chain_data.json")


def init_validators():
    """Initialize validators if API key is available."""
    global llm_validator, hybrid_validator
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key and api_key != "your_api_key_here":
        try:
            llm_validator = ProofOfUnderstanding(api_key)
            hybrid_validator = HybridValidator(llm_validator)
        except Exception as e:
            print(f"Warning: Could not initialize LLM validator: {e}")
            print("API will operate without LLM validation")


def load_chain():
    """Load blockchain from file if it exists."""
    global blockchain
    if os.path.exists(CHAIN_DATA_FILE):
        try:
            with open(CHAIN_DATA_FILE, 'r') as f:
                data = json.load(f)
                blockchain = NatLangChain.from_dict(data)
                print(f"Loaded blockchain with {len(blockchain.chain)} blocks")
        except Exception as e:
            print(f"Error loading chain data: {e}")
            print("Starting with fresh blockchain")


def save_chain():
    """Save blockchain to file."""
    try:
        with open(CHAIN_DATA_FILE, 'w') as f:
            json.dump(blockchain.to_dict(), f, indent=2)
    except Exception as e:
        print(f"Error saving chain data: {e}")


# Initialize on startup
init_validators()
load_chain()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "NatLangChain API",
        "llm_validation_available": llm_validator is not None,
        "blocks": len(blockchain.chain),
        "pending_entries": len(blockchain.pending_entries)
    })


@app.route('/chain', methods=['GET'])
def get_chain():
    """
    Get the entire blockchain.

    Returns:
        Full blockchain data
    """
    return jsonify({
        "length": len(blockchain.chain),
        "chain": blockchain.to_dict(),
        "valid": blockchain.validate_chain()
    })


@app.route('/chain/narrative', methods=['GET'])
def get_narrative():
    """
    Get the full narrative history as human-readable text.

    This is a key feature: the entire ledger as readable prose.

    Returns:
        Complete narrative of all entries
    """
    narrative = blockchain.get_full_narrative()
    return narrative, 200, {'Content-Type': 'text/plain; charset=utf-8'}


@app.route('/entry', methods=['POST'])
def add_entry():
    """
    Add a new natural language entry to the blockchain.

    Request body:
    {
        "content": "Natural language description of the transaction/event",
        "author": "identifier of the creator",
        "intent": "brief summary of purpose",
        "metadata": {} (optional),
        "validate": true/false (optional, default true),
        "auto_mine": true/false (optional, default false)
    }

    Returns:
        Entry status and validation results
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Required fields
    content = data.get("content")
    author = data.get("author")
    intent = data.get("intent")

    if not all([content, author, intent]):
        return jsonify({
            "error": "Missing required fields",
            "required": ["content", "author", "intent"]
        }), 400

    # Create entry
    entry = NaturalLanguageEntry(
        content=content,
        author=author,
        intent=intent,
        metadata=data.get("metadata", {})
    )

    # Validate if requested
    validate = data.get("validate", True)
    validation_result = None

    if validate and hybrid_validator:
        validation_result = hybrid_validator.validate(
            content=content,
            intent=intent,
            author=author,
            use_llm=True,
            multi_validator=data.get("multi_validator", False)
        )

        # Update entry with validation results
        decision = validation_result.get("overall_decision", "PENDING")
        entry.validation_status = decision.lower()

        if validation_result.get("llm_validation"):
            llm_val = validation_result["llm_validation"]
            if "validations" in llm_val:
                # Multi-validator consensus
                entry.validation_paraphrases = llm_val.get("paraphrases", [])
            elif "validation" in llm_val:
                # Single validator
                entry.validation_paraphrases = [
                    llm_val["validation"].get("paraphrase", "")
                ]

    # Add to blockchain
    result = blockchain.add_entry(entry)

    # Auto-mine if requested
    auto_mine = data.get("auto_mine", False)
    mined_block = None
    if auto_mine:
        mined_block = blockchain.mine_pending_entries()
        save_chain()

    response = {
        "status": "success",
        "entry": result,
        "validation": validation_result
    }

    if mined_block:
        response["mined_block"] = {
            "index": mined_block.index,
            "hash": mined_block.hash
        }

    return jsonify(response), 201


@app.route('/entry/validate', methods=['POST'])
def validate_entry():
    """
    Validate an entry without adding it to the blockchain.

    Request body:
    {
        "content": "content to validate",
        "author": "author identifier",
        "intent": "intent description",
        "multi_validator": true/false (optional)
    }

    Returns:
        Validation results
    """
    if not hybrid_validator:
        return jsonify({
            "error": "LLM validation not available",
            "reason": "ANTHROPIC_API_KEY not configured"
        }), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    content = data.get("content")
    author = data.get("author")
    intent = data.get("intent")

    if not all([content, author, intent]):
        return jsonify({
            "error": "Missing required fields",
            "required": ["content", "author", "intent"]
        }), 400

    validation_result = hybrid_validator.validate(
        content=content,
        intent=intent,
        author=author,
        use_llm=True,
        multi_validator=data.get("multi_validator", False)
    )

    return jsonify(validation_result)


@app.route('/mine', methods=['POST'])
def mine_block():
    """
    Mine pending entries into a new block.

    Request body (optional):
    {
        "difficulty": 2 (number of leading zeros in hash)
    }

    Returns:
        Newly mined block
    """
    if not blockchain.pending_entries:
        return jsonify({
            "error": "No pending entries to mine"
        }), 400

    data = request.get_json() or {}
    difficulty = data.get("difficulty", 2)

    mined_block = blockchain.mine_pending_entries(difficulty=difficulty)
    save_chain()

    return jsonify({
        "status": "success",
        "message": "Block mined successfully",
        "block": mined_block.to_dict()
    })


@app.route('/block/<int:index>', methods=['GET'])
def get_block(index: int):
    """
    Get a specific block by index.

    Args:
        index: Block index

    Returns:
        Block data
    """
    if index < 0 or index >= len(blockchain.chain):
        return jsonify({
            "error": "Block not found",
            "valid_range": f"0-{len(blockchain.chain) - 1}"
        }), 404

    block = blockchain.chain[index]
    return jsonify(block.to_dict())


@app.route('/entries/author/<author>', methods=['GET'])
def get_entries_by_author(author: str):
    """
    Get all entries by a specific author.

    Args:
        author: Author identifier

    Returns:
        List of entries by the author
    """
    entries = blockchain.get_entries_by_author(author)
    return jsonify({
        "author": author,
        "count": len(entries),
        "entries": entries
    })


@app.route('/entries/search', methods=['GET'])
def search_entries():
    """
    Search for entries by intent keyword.

    Query params:
        intent: Keyword to search for in intent field

    Returns:
        List of matching entries
    """
    intent_keyword = request.args.get('intent')

    if not intent_keyword:
        return jsonify({
            "error": "Missing 'intent' query parameter"
        }), 400

    entries = blockchain.get_entries_by_intent(intent_keyword)
    return jsonify({
        "keyword": intent_keyword,
        "count": len(entries),
        "entries": entries
    })


@app.route('/validate/chain', methods=['GET'])
def validate_blockchain():
    """
    Validate the entire blockchain for integrity.

    Returns:
        Validation status
    """
    is_valid = blockchain.validate_chain()
    return jsonify({
        "valid": is_valid,
        "blocks": len(blockchain.chain),
        "message": "Blockchain is valid" if is_valid else "Blockchain integrity compromised"
    })


@app.route('/pending', methods=['GET'])
def get_pending_entries():
    """
    Get all pending entries awaiting mining.

    Returns:
        List of pending entries
    """
    return jsonify({
        "count": len(blockchain.pending_entries),
        "entries": [entry.to_dict() for entry in blockchain.pending_entries]
    })


@app.route('/stats', methods=['GET'])
def get_stats():
    """
    Get blockchain statistics.

    Returns:
        Various statistics about the blockchain
    """
    total_entries = sum(len(block.entries) for block in blockchain.chain)

    authors = set()
    validated_count = 0
    for block in blockchain.chain:
        for entry in block.entries:
            authors.add(entry.author)
            if entry.validation_status == "validated" or entry.validation_status == "valid":
                validated_count += 1

    return jsonify({
        "total_blocks": len(blockchain.chain),
        "total_entries": total_entries,
        "pending_entries": len(blockchain.pending_entries),
        "unique_authors": len(authors),
        "validated_entries": validated_count,
        "chain_valid": blockchain.validate_chain(),
        "latest_block_hash": blockchain.get_latest_block().hash,
        "llm_validation_enabled": llm_validator is not None
    })


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    return jsonify({"error": "Internal server error"}), 500


def run_server():
    """Run the Flask development server."""
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 5000))

    print(f"\n{'='*60}")
    print("NatLangChain API Server")
    print(f"{'='*60}")
    print(f"Listening on: http://{host}:{port}")
    print(f"LLM Validation: {'Enabled' if llm_validator else 'Disabled'}")
    print(f"Blockchain: {len(blockchain.chain)} blocks loaded")
    print(f"{'='*60}\n")

    app.run(host=host, port=port, debug=True)


if __name__ == '__main__':
    run_server()
