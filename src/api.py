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
from semantic_diff import SemanticDriftDetector
from semantic_search import SemanticSearchEngine
from dialectic_consensus import DialecticConsensus
from contract_parser import ContractParser
from contract_matcher import ContractMatcher


# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False

# Initialize blockchain and validator
blockchain = NatLangChain()
llm_validator = None
hybrid_validator = None
drift_detector = None
search_engine = None
dialectic_validator = None
contract_parser = None
contract_matcher = None

# Data file for persistence
CHAIN_DATA_FILE = os.getenv("CHAIN_DATA_FILE", "chain_data.json")


def init_validators():
    """Initialize validators and advanced features if API key is available."""
    global llm_validator, hybrid_validator, drift_detector, search_engine, dialectic_validator, contract_parser, contract_matcher
    api_key = os.getenv("ANTHROPIC_API_KEY")

    # Initialize semantic search (doesn't require API key)
    try:
        search_engine = SemanticSearchEngine()
        print("Semantic search engine initialized")
    except Exception as e:
        print(f"Warning: Could not initialize semantic search: {e}")

    # Initialize LLM-based features if API key available
    if api_key and api_key != "your_api_key_here":
        try:
            llm_validator = ProofOfUnderstanding(api_key)
            hybrid_validator = HybridValidator(llm_validator)
            drift_detector = SemanticDriftDetector(api_key)
            dialectic_validator = DialecticConsensus(api_key)
            contract_parser = ContractParser(api_key)
            contract_matcher = ContractMatcher(api_key)
            print("LLM-based features initialized (including contract matching)")
        except Exception as e:
            print(f"Warning: Could not initialize LLM features: {e}")
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
    validation_mode = data.get("validation_mode", "standard")  # "standard", "multi", or "dialectic"

    if validate:
        if validation_mode == "dialectic" and dialectic_validator:
            # Use dialectic consensus validation
            dialectic_result = dialectic_validator.validate_entry(content, intent, author)
            validation_result = {
                "validation_mode": "dialectic",
                "dialectic_validation": dialectic_result,
                "overall_decision": dialectic_result.get("decision", "ERROR")
            }
        elif hybrid_validator:
            # Use standard or multi-validator mode
            validation_result = hybrid_validator.validate(
                content=content,
                intent=intent,
                author=author,
                use_llm=True,
                multi_validator=(validation_mode == "multi" or data.get("multi_validator", False))
            )
            validation_result["validation_mode"] = validation_mode

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

    Automatically finds and proposes matches for contract entries before mining.

    Request body (optional):
    {
        "difficulty": 2 (number of leading zeros in hash),
        "miner_id": "miner identifier" (optional, for contract matching)
    }

    Returns:
        Newly mined block with any contract proposals
    """
    if not blockchain.pending_entries:
        return jsonify({
            "error": "No pending entries to mine"
        }), 400

    data = request.get_json() or {}
    difficulty = data.get("difficulty", 2)
    miner_id = data.get("miner_id", "miner")

    # Find contract matches if matcher is available
    proposals = []
    if contract_matcher:
        try:
            proposals = contract_matcher.find_matches(
                blockchain,
                blockchain.pending_entries,
                miner_id
            )

            # Add proposals to pending entries
            for proposal in proposals:
                blockchain.add_entry(proposal)

        except Exception as e:
            print(f"Contract matching failed: {e}")

    # Mine the block
    mined_block = blockchain.mine_pending_entries(difficulty=difficulty)
    save_chain()

    return jsonify({
        "status": "success",
        "message": "Block mined successfully",
        "block": mined_block.to_dict(),
        "contract_proposals": len(proposals),
        "proposals": [p.to_dict() for p in proposals] if proposals else []
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

    # Count contracts
    total_contracts = 0
    open_contracts = 0
    matched_contracts = 0

    for block in blockchain.chain:
        for entry in block.entries:
            if entry.metadata.get("is_contract"):
                total_contracts += 1
                status = entry.metadata.get("status", "open")
                if status == "open":
                    open_contracts += 1
                elif status == "matched":
                    matched_contracts += 1

    return jsonify({
        "total_blocks": len(blockchain.chain),
        "total_entries": total_entries,
        "pending_entries": len(blockchain.pending_entries),
        "unique_authors": len(authors),
        "validated_entries": validated_count,
        "chain_valid": blockchain.validate_chain(),
        "latest_block_hash": blockchain.get_latest_block().hash,
        "llm_validation_enabled": llm_validator is not None,
        "semantic_search_enabled": search_engine is not None,
        "drift_detection_enabled": drift_detector is not None,
        "dialectic_consensus_enabled": dialectic_validator is not None,
        "contract_features_enabled": contract_parser is not None and contract_matcher is not None,
        "total_contracts": total_contracts,
        "open_contracts": open_contracts,
        "matched_contracts": matched_contracts
    })


# ========== Semantic Search Endpoints ==========

@app.route('/search/semantic', methods=['POST'])
def semantic_search():
    """
    Perform semantic search across blockchain entries.

    Request body:
    {
        "query": "natural language search query",
        "top_k": 5 (optional),
        "min_score": 0.0 (optional),
        "field": "content" | "intent" | "both" (optional)
    }

    Returns:
        List of semantically similar entries
    """
    if not search_engine:
        return jsonify({
            "error": "Semantic search not available",
            "reason": "Search engine not initialized"
        }), 503

    data = request.get_json()

    if not data or "query" not in data:
        return jsonify({
            "error": "Missing required field: query"
        }), 400

    query = data["query"]
    top_k = data.get("top_k", 5)
    min_score = data.get("min_score", 0.0)
    field = data.get("field", "content")

    try:
        if field in ["content", "intent", "both"]:
            results = search_engine.search_by_field(
                blockchain, query, field=field, top_k=top_k, min_score=min_score
            )
        else:
            results = search_engine.search(
                blockchain, query, top_k=top_k, min_score=min_score
            )

        return jsonify({
            "query": query,
            "field": field,
            "count": len(results),
            "results": results
        })

    except Exception as e:
        return jsonify({
            "error": "Search failed",
            "reason": str(e)
        }), 500


@app.route('/search/similar', methods=['POST'])
def find_similar():
    """
    Find entries similar to a given content.

    Request body:
    {
        "content": "content to find similar entries for",
        "top_k": 5 (optional),
        "exclude_exact": true (optional)
    }

    Returns:
        List of similar entries
    """
    if not search_engine:
        return jsonify({
            "error": "Semantic search not available"
        }), 503

    data = request.get_json()

    if not data or "content" not in data:
        return jsonify({
            "error": "Missing required field: content"
        }), 400

    content = data["content"]
    top_k = data.get("top_k", 5)
    exclude_exact = data.get("exclude_exact", True)

    try:
        results = search_engine.find_similar_entries(
            blockchain, content, top_k=top_k, exclude_exact=exclude_exact
        )

        return jsonify({
            "content": content,
            "count": len(results),
            "similar_entries": results
        })

    except Exception as e:
        return jsonify({
            "error": "Search failed",
            "reason": str(e)
        }), 500


# ========== Semantic Drift Detection Endpoints ==========

@app.route('/drift/check', methods=['POST'])
def check_drift():
    """
    Check semantic drift between intent and execution.

    Request body:
    {
        "on_chain_intent": "the canonical intent from blockchain",
        "execution_log": "the actual execution or action log"
    }

    Returns:
        Drift analysis with score and recommendations
    """
    if not drift_detector:
        return jsonify({
            "error": "Drift detection not available",
            "reason": "ANTHROPIC_API_KEY not configured"
        }), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    on_chain_intent = data.get("on_chain_intent")
    execution_log = data.get("execution_log")

    if not all([on_chain_intent, execution_log]):
        return jsonify({
            "error": "Missing required fields",
            "required": ["on_chain_intent", "execution_log"]
        }), 400

    result = drift_detector.check_alignment(on_chain_intent, execution_log)

    return jsonify(result)


@app.route('/drift/entry/<int:block_index>/<int:entry_index>', methods=['POST'])
def check_entry_drift(block_index: int, entry_index: int):
    """
    Check drift for a specific blockchain entry against an execution log.

    Args:
        block_index: Block index containing the entry
        entry_index: Entry index within the block

    Request body:
    {
        "execution_log": "the actual execution or action log"
    }

    Returns:
        Drift analysis for the specific entry
    """
    if not drift_detector:
        return jsonify({
            "error": "Drift detection not available"
        }), 503

    # Validate block index
    if block_index < 0 or block_index >= len(blockchain.chain):
        return jsonify({
            "error": "Block not found",
            "valid_range": f"0-{len(blockchain.chain) - 1}"
        }), 404

    block = blockchain.chain[block_index]

    # Validate entry index
    if entry_index < 0 or entry_index >= len(block.entries):
        return jsonify({
            "error": "Entry not found",
            "valid_range": f"0-{len(block.entries) - 1}"
        }), 404

    entry = block.entries[entry_index]

    # Get execution log from request
    data = request.get_json()
    if not data or "execution_log" not in data:
        return jsonify({
            "error": "Missing required field: execution_log"
        }), 400

    execution_log = data["execution_log"]

    # Check drift
    result = drift_detector.check_entry_execution_alignment(
        entry.content, entry.intent, execution_log
    )

    result["entry_info"] = {
        "block_index": block_index,
        "entry_index": entry_index,
        "author": entry.author,
        "intent": entry.intent
    }

    return jsonify(result)


# ========== Dialectic Consensus Endpoint ==========

@app.route('/validate/dialectic', methods=['POST'])
def validate_dialectic():
    """
    Validate an entry using dialectic consensus (Skeptic/Facilitator debate).

    Request body:
    {
        "content": "content to validate",
        "author": "author identifier",
        "intent": "intent description"
    }

    Returns:
        Dialectic validation result with both perspectives
    """
    if not dialectic_validator:
        return jsonify({
            "error": "Dialectic consensus not available",
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

    result = dialectic_validator.validate_entry(content, intent, author)

    return jsonify(result)


# ========== Live Contract Endpoints ==========

@app.route('/contract/post', methods=['POST'])
def post_contract():
    """
    Post a new live contract (offer or seek).

    Request body:
    {
        "content": "Natural language contract description",
        "author": "author identifier",
        "intent": "Contract intent",
        "contract_type": "offer" | "seek",
        "terms": {"key": "value"},  (optional, will be extracted if not provided)
        "auto_mine": true/false (optional)
    }

    Returns:
        Contract entry with validation results
    """
    if not contract_parser:
        return jsonify({
            "error": "Contract features not available",
            "reason": "ANTHROPIC_API_KEY not configured"
        }), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    content = data.get("content")
    author = data.get("author")
    intent = data.get("intent")
    contract_type = data.get("contract_type", ContractParser.TYPE_OFFER)

    if not all([content, author, intent]):
        return jsonify({
            "error": "Missing required fields",
            "required": ["content", "author", "intent"]
        }), 400

    try:
        # Parse contract
        contract_data = contract_parser.parse_contract(content, use_llm=True)

        # Override type if provided
        if contract_type:
            contract_data["contract_type"] = contract_type

        # Override terms if provided
        if "terms" in data:
            contract_data["terms"] = data["terms"]

        # Validate clarity
        is_valid, reason = contract_parser.validate_contract_clarity(content)
        if not is_valid:
            return jsonify({
                "error": "Contract validation failed",
                "reason": reason
            }), 400

        # Create entry with contract metadata
        entry = NaturalLanguageEntry(
            content=content,
            author=author,
            intent=intent,
            metadata=contract_data
        )

        entry.validation_status = "valid"

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
            "contract_metadata": contract_data
        }

        if mined_block:
            response["mined_block"] = {
                "index": mined_block.index,
                "hash": mined_block.hash
            }

        return jsonify(response), 201

    except Exception as e:
        return jsonify({
            "error": "Contract posting failed",
            "reason": str(e)
        }), 500


@app.route('/contract/list', methods=['GET'])
def list_contracts():
    """
    List all contracts, optionally filtered by status or type.

    Query params:
        status: Filter by status (open, matched, negotiating, closed, cancelled)
        type: Filter by type (offer, seek, proposal)
        author: Filter by author

    Returns:
        List of contract entries
    """
    status_filter = request.args.get('status')
    type_filter = request.args.get('type')
    author_filter = request.args.get('author')

    contracts = []

    for block in blockchain.chain:
        for entry in block.entries:
            # Skip if not a contract
            if not entry.metadata.get("is_contract"):
                continue

            # Apply filters
            if status_filter and entry.metadata.get("status") != status_filter:
                continue

            if type_filter and entry.metadata.get("contract_type") != type_filter:
                continue

            if author_filter and entry.author != author_filter:
                continue

            contracts.append({
                "block_index": block.index,
                "block_hash": block.hash,
                "entry": entry.to_dict()
            })

    return jsonify({
        "count": len(contracts),
        "contracts": contracts
    })


@app.route('/contract/respond', methods=['POST'])
def respond_to_contract():
    """
    Respond to a contract proposal or create a counter-offer.

    Request body:
    {
        "to_block": block_index,
        "to_entry": entry_index,
        "response_content": "Natural language response",
        "author": "author identifier",
        "response_type": "accept" | "counter" | "reject",
        "counter_terms": {"key": "value"} (optional, for counter-offers)
    }

    Returns:
        Response entry with mediation if counter-offer
    """
    if not contract_parser or not contract_matcher:
        return jsonify({
            "error": "Contract features not available"
        }), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    to_block = data.get("to_block")
    to_entry = data.get("to_entry")
    response_content = data.get("response_content")
    author = data.get("author")
    response_type = data.get("response_type", "counter")

    if not all([to_block is not None, to_entry is not None, response_content, author]):
        return jsonify({
            "error": "Missing required fields",
            "required": ["to_block", "to_entry", "response_content", "author"]
        }), 400

    # Get original entry
    if to_block < 0 or to_block >= len(blockchain.chain):
        return jsonify({"error": "Block not found"}), 404

    block = blockchain.chain[to_block]

    if to_entry < 0 or to_entry >= len(block.entries):
        return jsonify({"error": "Entry not found"}), 404

    original_entry = block.entries[to_entry]

    # Create response entry
    response_metadata = {
        "is_contract": True,
        "contract_type": ContractParser.TYPE_RESPONSE,
        "response_type": response_type,
        "links": [block.hash],  # Link to original
        "terms": data.get("counter_terms", {})
    }

    # If counter-offer, get mediation
    mediation_result = None
    if response_type == "counter" and contract_matcher:
        mediation_result = contract_matcher.mediate_negotiation(
            original_entry.content,
            original_entry.metadata.get("terms", {}),
            response_content,
            data.get("counter_terms", {}),
            original_entry.metadata.get("negotiation_round", 0) + 1
        )

        response_metadata["mediation"] = mediation_result
        response_metadata["negotiation_round"] = original_entry.metadata.get("negotiation_round", 0) + 1

    response_entry = NaturalLanguageEntry(
        content=f"[RESPONSE TO: {block.hash[:8]}] {response_content}",
        author=author,
        intent=f"Response to contract: {response_type}",
        metadata=response_metadata
    )

    blockchain.add_entry(response_entry)

    return jsonify({
        "status": "success",
        "response": response_entry.to_dict(),
        "mediation": mediation_result
    }), 201


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
