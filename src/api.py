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
from temporal_fixity import TemporalFixity
from dispute import DisputeManager
from semantic_oracles import SemanticOracle, SemanticCircuitBreaker
from multi_model_consensus import MultiModelConsensus
from escalation_fork import EscalationForkManager, ForkStatus, TriggerReason
from observance_burn import ObservanceBurnManager, BurnReason
from anti_harassment import AntiHarassmentManager, InitiationPath, DisputeResolution
from treasury import NatLangChainTreasury, InflowType, SubsidyStatus
from fido2_auth import FIDO2AuthManager, SignatureType, UserVerification
from zk_privacy import ZKPrivacyManager, ProofStatus, VoteStatus
from negotiation_engine import AutomatedNegotiationEngine, NegotiationPhase, OfferType, ClauseType
from market_pricing import MarketAwarePricingManager, PricingStrategy, AssetClass, MarketCondition
from mobile_deployment import MobileDeploymentManager, DeviceType, WalletType, ConnectionState


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
temporal_fixity = None
semantic_oracle = None
circuit_breaker = None
multi_model_consensus = None
dispute_manager = None
escalation_fork_manager = None
observance_burn_manager = None
anti_harassment_manager = None
treasury = None
fido2_manager = None
zk_privacy_manager = None
negotiation_engine = None
market_pricing = None
mobile_deployment = None

# Data file for persistence
CHAIN_DATA_FILE = os.getenv("CHAIN_DATA_FILE", "chain_data.json")


def init_validators():
    """Initialize validators and advanced features if API key is available."""
    global llm_validator, hybrid_validator, drift_detector, search_engine, dialectic_validator, contract_parser, contract_matcher, temporal_fixity, semantic_oracle, circuit_breaker, multi_model_consensus, dispute_manager, escalation_fork_manager, observance_burn_manager, anti_harassment_manager, treasury, fido2_manager, zk_privacy_manager, negotiation_engine, market_pricing, mobile_deployment
    api_key = os.getenv("ANTHROPIC_API_KEY")

    # Initialize temporal fixity (doesn't require API key)
    try:
        temporal_fixity = TemporalFixity()
        print("Temporal fixity (T0 preservation) initialized")
    except Exception as e:
        print(f"Warning: Could not initialize temporal fixity: {e}")

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
            semantic_oracle = SemanticOracle(api_key)
            circuit_breaker = SemanticCircuitBreaker(semantic_oracle) if semantic_oracle else None
            multi_model_consensus = MultiModelConsensus(api_key)
            dispute_manager = DisputeManager(api_key)
            escalation_fork_manager = EscalationForkManager()
            observance_burn_manager = ObservanceBurnManager()
            anti_harassment_manager = AntiHarassmentManager(burn_manager=observance_burn_manager)
            treasury = NatLangChainTreasury(anti_harassment_manager=anti_harassment_manager)
            fido2_manager = FIDO2AuthManager()
            zk_privacy_manager = ZKPrivacyManager()
            negotiation_engine = AutomatedNegotiationEngine(api_key)
            market_pricing = MarketAwarePricingManager(api_key)
            mobile_deployment = MobileDeploymentManager()
            print("LLM-based features initialized (contracts, oracles, disputes, forks, burns, anti-harassment, treasury, FIDO2, ZK privacy, negotiation, market pricing, mobile deployment, multi-model consensus)")
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
        "dispute_features_enabled": dispute_manager is not None,
        "total_contracts": total_contracts,
        "open_contracts": open_contracts,
        "matched_contracts": matched_contracts,
        "total_disputes": sum(1 for block in blockchain.chain for entry in block.entries if entry.metadata.get("is_dispute") and entry.metadata.get("dispute_type") == "dispute_declaration"),
        "open_disputes": sum(1 for block in blockchain.chain for entry in block.entries if entry.metadata.get("is_dispute") and entry.metadata.get("dispute_type") == "dispute_declaration" and entry.metadata.get("status") == "open")
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


# ========== Dispute Protocol (MP-03) Endpoints ==========

@app.route('/dispute/file', methods=['POST'])
def file_dispute():
    """
    File a new dispute (MP-03 Dispute Declaration).

    Disputes are signals, not failures. Filing a dispute:
    1. Creates an immutable record of the dispute
    2. Freezes contested entries (prevents mutation)
    3. Establishes the escalation path

    Request body:
    {
        "claimant": "identifier of party filing dispute",
        "respondent": "identifier of party being disputed against",
        "contested_refs": [{"block": 1, "entry": 0}, ...],
        "description": "Natural language description of the dispute",
        "escalation_path": "mediator_node" | "external_arbitrator" | "legal_court" (optional),
        "supporting_evidence": ["hash1", "hash2", ...] (optional),
        "auto_mine": true/false (optional)
    }

    Returns:
        Dispute entry with frozen evidence confirmation
    """
    global dispute_manager
    if not dispute_manager:
        # Initialize basic dispute manager without LLM
        dispute_manager = DisputeManager()

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    claimant = data.get("claimant")
    respondent = data.get("respondent")
    contested_refs = data.get("contested_refs", [])
    description = data.get("description")

    if not all([claimant, respondent, description]):
        return jsonify({
            "error": "Missing required fields",
            "required": ["claimant", "respondent", "description"]
        }), 400

    if not contested_refs:
        return jsonify({
            "error": "No contested entries specified",
            "required": "contested_refs: [{\"block\": int, \"entry\": int}, ...]"
        }), 400

    # Validate contested refs exist
    for ref in contested_refs:
        block_idx = ref.get("block", -1)
        entry_idx = ref.get("entry", -1)

        if block_idx < 0 or block_idx >= len(blockchain.chain):
            return jsonify({
                "error": f"Invalid block reference: {block_idx}",
                "valid_range": f"0-{len(blockchain.chain) - 1}"
            }), 400

        block = blockchain.chain[block_idx]
        if entry_idx < 0 or entry_idx >= len(block.entries):
            return jsonify({
                "error": f"Invalid entry reference in block {block_idx}: {entry_idx}",
                "valid_range": f"0-{len(block.entries) - 1}"
            }), 400

    # Validate dispute clarity
    is_valid, reason = dispute_manager.validate_dispute_clarity(description)
    if not is_valid:
        return jsonify({
            "error": "Dispute validation failed",
            "reason": reason
        }), 400

    try:
        # Create dispute
        dispute_data = dispute_manager.create_dispute(
            claimant=claimant,
            respondent=respondent,
            contested_refs=contested_refs,
            description=description,
            escalation_path=data.get("escalation_path", DisputeManager.ESCALATION_MEDIATOR),
            supporting_evidence=data.get("supporting_evidence")
        )

        # Format dispute content
        formatted_content = dispute_manager.format_dispute_entry(
            DisputeManager.TYPE_DECLARATION,
            description,
            dispute_data["dispute_id"]
        )

        # Create blockchain entry
        entry = NaturalLanguageEntry(
            content=formatted_content,
            author=claimant,
            intent=f"File dispute against {respondent}",
            metadata=dispute_data
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
            "message": "Dispute filed successfully",
            "dispute_id": dispute_data["dispute_id"],
            "entry": result,
            "evidence_frozen": True,
            "frozen_entries_count": len(contested_refs)
        }

        if mined_block:
            response["mined_block"] = {
                "index": mined_block.index,
                "hash": mined_block.hash
            }

        return jsonify(response), 201

    except Exception as e:
        return jsonify({
            "error": "Failed to file dispute",
            "reason": str(e)
        }), 500


@app.route('/dispute/list', methods=['GET'])
def list_disputes():
    """
    List all disputes, optionally filtered.

    Query params:
        status: Filter by status (open, clarifying, escalated, resolved)
        claimant: Filter by claimant
        respondent: Filter by respondent

    Returns:
        List of dispute entries
    """
    status_filter = request.args.get('status')
    claimant_filter = request.args.get('claimant')
    respondent_filter = request.args.get('respondent')

    disputes = []

    for block in blockchain.chain:
        for entry_idx, entry in enumerate(block.entries):
            metadata = entry.metadata or {}

            # Skip if not a dispute declaration
            if not metadata.get("is_dispute"):
                continue
            if metadata.get("dispute_type") != DisputeManager.TYPE_DECLARATION:
                continue

            # Apply filters
            if status_filter and metadata.get("status") != status_filter:
                continue

            if claimant_filter and metadata.get("claimant") != claimant_filter:
                continue

            if respondent_filter and metadata.get("respondent") != respondent_filter:
                continue

            disputes.append({
                "block_index": block.index,
                "block_hash": block.hash,
                "entry_index": entry_idx,
                "dispute_id": metadata.get("dispute_id"),
                "claimant": metadata.get("claimant"),
                "respondent": metadata.get("respondent"),
                "status": metadata.get("status"),
                "created_at": metadata.get("created_at"),
                "entry": entry.to_dict()
            })

    return jsonify({
        "count": len(disputes),
        "disputes": disputes
    })


@app.route('/dispute/<dispute_id>', methods=['GET'])
def get_dispute(dispute_id: str):
    """
    Get detailed status of a specific dispute.

    Args:
        dispute_id: The dispute identifier

    Returns:
        Complete dispute status and history
    """
    if not dispute_manager:
        return jsonify({"error": "Dispute features not initialized"}), 503

    status = dispute_manager.get_dispute_status(dispute_id, blockchain)

    if not status:
        return jsonify({
            "error": "Dispute not found",
            "dispute_id": dispute_id
        }), 404

    return jsonify(status)


@app.route('/dispute/<dispute_id>/evidence', methods=['POST'])
def add_dispute_evidence(dispute_id: str):
    """
    Add evidence to an existing dispute.

    Evidence is append-only and timestamped.

    Request body:
    {
        "author": "who is submitting",
        "evidence_content": "description/content of evidence",
        "evidence_type": "document" | "testimony" | "receipt" | "screenshot" | "other",
        "evidence_hash": "hash of external file" (optional)
    }

    Returns:
        Evidence entry confirmation
    """
    if not dispute_manager:
        return jsonify({"error": "Dispute features not initialized"}), 503

    # Verify dispute exists
    status = dispute_manager.get_dispute_status(dispute_id, blockchain)
    if not status:
        return jsonify({
            "error": "Dispute not found",
            "dispute_id": dispute_id
        }), 404

    if status.get("is_resolved"):
        return jsonify({
            "error": "Cannot add evidence to resolved dispute",
            "dispute_id": dispute_id
        }), 400

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    author = data.get("author")
    evidence_content = data.get("evidence_content")

    if not all([author, evidence_content]):
        return jsonify({
            "error": "Missing required fields",
            "required": ["author", "evidence_content"]
        }), 400

    try:
        evidence_data = dispute_manager.add_evidence(
            dispute_id=dispute_id,
            author=author,
            evidence_content=evidence_content,
            evidence_type=data.get("evidence_type", "document"),
            evidence_hash=data.get("evidence_hash")
        )

        formatted_content = dispute_manager.format_dispute_entry(
            DisputeManager.TYPE_EVIDENCE,
            evidence_content,
            dispute_id
        )

        entry = NaturalLanguageEntry(
            content=formatted_content,
            author=author,
            intent=f"Submit evidence for dispute {dispute_id}",
            metadata=evidence_data
        )
        entry.validation_status = "valid"

        result = blockchain.add_entry(entry)

        return jsonify({
            "status": "success",
            "message": "Evidence added to dispute",
            "dispute_id": dispute_id,
            "evidence_hash": evidence_data.get("evidence_hash"),
            "entry": result
        }), 201

    except Exception as e:
        return jsonify({
            "error": "Failed to add evidence",
            "reason": str(e)
        }), 500


@app.route('/dispute/<dispute_id>/escalate', methods=['POST'])
def escalate_dispute(dispute_id: str):
    """
    Escalate a dispute to higher authority.

    Request body:
    {
        "escalating_party": "who is escalating",
        "escalation_path": "mediator_node" | "external_arbitrator" | "legal_court",
        "escalation_reason": "why escalation is needed",
        "escalation_authority": "specific authority if known" (optional)
    }

    Returns:
        Escalation entry confirmation
    """
    if not dispute_manager:
        return jsonify({"error": "Dispute features not initialized"}), 503

    # Verify dispute exists
    status = dispute_manager.get_dispute_status(dispute_id, blockchain)
    if not status:
        return jsonify({
            "error": "Dispute not found",
            "dispute_id": dispute_id
        }), 404

    if status.get("is_resolved"):
        return jsonify({
            "error": "Cannot escalate resolved dispute",
            "dispute_id": dispute_id
        }), 400

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    escalating_party = data.get("escalating_party")
    escalation_path = data.get("escalation_path")
    escalation_reason = data.get("escalation_reason")

    if not all([escalating_party, escalation_path, escalation_reason]):
        return jsonify({
            "error": "Missing required fields",
            "required": ["escalating_party", "escalation_path", "escalation_reason"]
        }), 400

    try:
        escalation_data = dispute_manager.escalate_dispute(
            dispute_id=dispute_id,
            escalating_party=escalating_party,
            escalation_path=escalation_path,
            escalation_reason=escalation_reason,
            escalation_authority=data.get("escalation_authority")
        )

        formatted_content = dispute_manager.format_dispute_entry(
            DisputeManager.TYPE_ESCALATION,
            escalation_reason,
            dispute_id
        )

        entry = NaturalLanguageEntry(
            content=formatted_content,
            author=escalating_party,
            intent=f"Escalate dispute {dispute_id} to {escalation_path}",
            metadata=escalation_data
        )
        entry.validation_status = "valid"

        result = blockchain.add_entry(entry)

        return jsonify({
            "status": "success",
            "message": f"Dispute escalated to {escalation_path}",
            "dispute_id": dispute_id,
            "escalation_path": escalation_path,
            "entry": result
        }), 201

    except Exception as e:
        return jsonify({
            "error": "Failed to escalate dispute",
            "reason": str(e)
        }), 500


@app.route('/dispute/<dispute_id>/resolve', methods=['POST'])
def resolve_dispute(dispute_id: str):
    """
    Record the resolution of a dispute.

    Note: Per Refusal Doctrine, this only RECORDS resolution.
    Actual resolution is determined by humans/authorities.

    Request body:
    {
        "resolution_authority": "who authorized the resolution",
        "resolution_type": "settled" | "arbitrated" | "adjudicated" | "withdrawn",
        "resolution_content": "Natural language resolution description",
        "findings": {"key": "value"} (optional),
        "remedies": ["remedy1", "remedy2", ...] (optional)
    }

    Returns:
        Resolution entry with unfrozen entries
    """
    if not dispute_manager:
        return jsonify({"error": "Dispute features not initialized"}), 503

    # Verify dispute exists
    status = dispute_manager.get_dispute_status(dispute_id, blockchain)
    if not status:
        return jsonify({
            "error": "Dispute not found",
            "dispute_id": dispute_id
        }), 404

    if status.get("is_resolved"):
        return jsonify({
            "error": "Dispute already resolved",
            "dispute_id": dispute_id
        }), 400

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    resolution_authority = data.get("resolution_authority")
    resolution_type = data.get("resolution_type")
    resolution_content = data.get("resolution_content")

    if not all([resolution_authority, resolution_type, resolution_content]):
        return jsonify({
            "error": "Missing required fields",
            "required": ["resolution_authority", "resolution_type", "resolution_content"]
        }), 400

    valid_resolution_types = ["settled", "arbitrated", "adjudicated", "withdrawn"]
    if resolution_type not in valid_resolution_types:
        return jsonify({
            "error": f"Invalid resolution_type. Must be one of: {valid_resolution_types}"
        }), 400

    try:
        resolution_data = dispute_manager.record_resolution(
            dispute_id=dispute_id,
            resolution_authority=resolution_authority,
            resolution_type=resolution_type,
            resolution_content=resolution_content,
            findings=data.get("findings"),
            remedies=data.get("remedies")
        )

        formatted_content = dispute_manager.format_dispute_entry(
            DisputeManager.TYPE_RESOLUTION,
            resolution_content,
            dispute_id
        )

        entry = NaturalLanguageEntry(
            content=formatted_content,
            author=resolution_authority,
            intent=f"Resolve dispute {dispute_id}: {resolution_type}",
            metadata=resolution_data
        )
        entry.validation_status = "valid"

        result = blockchain.add_entry(entry)
        save_chain()

        return jsonify({
            "status": "success",
            "message": f"Dispute resolved: {resolution_type}",
            "dispute_id": dispute_id,
            "entries_unfrozen": resolution_data.get("entries_unfrozen", 0),
            "entry": result
        }), 201

    except Exception as e:
        return jsonify({
            "error": "Failed to record resolution",
            "reason": str(e)
        }), 500


@app.route('/dispute/<dispute_id>/package', methods=['GET'])
def get_dispute_package(dispute_id: str):
    """
    Generate a complete dispute package for external arbitration.

    This package contains all information needed for an external
    authority to review and resolve the dispute.

    Query params:
        include_entries: true/false (whether to include full frozen entries, default true)

    Returns:
        Complete dispute package with integrity hash
    """
    if not dispute_manager:
        return jsonify({"error": "Dispute features not initialized"}), 503

    # Verify dispute exists
    status = dispute_manager.get_dispute_status(dispute_id, blockchain)
    if not status:
        return jsonify({
            "error": "Dispute not found",
            "dispute_id": dispute_id
        }), 404

    include_entries = request.args.get('include_entries', 'true').lower() == 'true'

    try:
        package = dispute_manager.generate_dispute_package(
            dispute_id=dispute_id,
            blockchain=blockchain,
            include_frozen_entries=include_entries
        )

        return jsonify(package)

    except Exception as e:
        return jsonify({
            "error": "Failed to generate dispute package",
            "reason": str(e)
        }), 500


@app.route('/dispute/<dispute_id>/analyze', methods=['GET'])
def analyze_dispute(dispute_id: str):
    """
    Get LLM analysis of a dispute (for understanding, not resolution).

    Note: Per Refusal Doctrine, this analysis is for UNDERSTANDING only.
    LLMs do not resolve disputes.

    Returns:
        Dispute analysis with key issues identified
    """
    if not dispute_manager or not dispute_manager.client:
        return jsonify({
            "error": "Dispute analysis not available",
            "reason": "LLM features not configured"
        }), 503

    # Verify dispute exists and get details
    status = dispute_manager.get_dispute_status(dispute_id, blockchain)
    if not status:
        return jsonify({
            "error": "Dispute not found",
            "dispute_id": dispute_id
        }), 404

    # Get the dispute description and contested content
    dispute_description = None
    contested_content = []

    for block in blockchain.chain:
        for entry in block.entries:
            metadata = entry.metadata or {}

            if metadata.get("dispute_id") == dispute_id:
                if metadata.get("dispute_type") == DisputeManager.TYPE_DECLARATION:
                    dispute_description = entry.content

                    # Get contested entries
                    for ref in metadata.get("contested_refs", []):
                        block_idx = ref.get("block", 0)
                        entry_idx = ref.get("entry", 0)
                        if block_idx < len(blockchain.chain):
                            contested_block = blockchain.chain[block_idx]
                            if entry_idx < len(contested_block.entries):
                                contested_entry = contested_block.entries[entry_idx]
                                contested_content.append(contested_entry.content)
                    break

    if not dispute_description:
        return jsonify({
            "error": "Could not find dispute description",
            "dispute_id": dispute_id
        }), 404

    try:
        analysis = dispute_manager.analyze_dispute(
            dispute_description=dispute_description,
            contested_content="\n\n---\n\n".join(contested_content)
        )

        if not analysis:
            return jsonify({
                "error": "Analysis failed",
                "reason": "LLM analysis returned empty result"
            }), 500

        return jsonify({
            "dispute_id": dispute_id,
            "analysis": analysis,
            "disclaimer": "This analysis is for understanding only. Per NatLangChain Refusal Doctrine, dispute resolution requires human judgment."
        })

    except Exception as e:
        return jsonify({
            "error": "Analysis failed",
            "reason": str(e)
        }), 500


@app.route('/entry/frozen/<int:block_index>/<int:entry_index>', methods=['GET'])
def check_entry_frozen(block_index: int, entry_index: int):
    """
    Check if an entry is frozen due to dispute.

    Args:
        block_index: Block index
        entry_index: Entry index

    Returns:
        Frozen status and dispute ID if frozen
    """
    if not dispute_manager:
        return jsonify({
            "frozen": False,
            "dispute_id": None,
            "message": "Dispute features not initialized"
        })

    is_frozen, dispute_id = dispute_manager.is_entry_frozen(block_index, entry_index)

    return jsonify({
        "block_index": block_index,
        "entry_index": entry_index,
        "frozen": is_frozen,
        "dispute_id": dispute_id
    })


# ========== Escalation Fork Endpoints ==========

@app.route('/fork/trigger', methods=['POST'])
def trigger_escalation_fork():
    """
    Trigger an Escalation Fork after failed mediation.

    Request body:
    {
        "dispute_id": "DISPUTE-XXX",
        "trigger_reason": "failed_ratification|refusal_to_mediate|timeout|mutual_request",
        "triggering_party": "alice",
        "original_mediator": "mediator_node_1",
        "original_pool": 100.0,
        "burn_tx_hash": "0x...",
        "evidence_of_failure": {...}  (optional)
    }

    Returns:
        Fork metadata
    """
    if not escalation_fork_manager:
        return jsonify({
            "error": "Escalation fork not available",
            "reason": "Features not initialized"
        }), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["dispute_id", "trigger_reason", "triggering_party",
                       "original_mediator", "original_pool", "burn_tx_hash"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    # Validate trigger reason
    try:
        trigger_reason = TriggerReason(data["trigger_reason"])
    except ValueError:
        return jsonify({
            "error": "Invalid trigger_reason",
            "valid_values": [r.value for r in TriggerReason]
        }), 400

    # Verify the observance burn if burn manager available
    if observance_burn_manager:
        is_valid, burn_result = observance_burn_manager.verify_escalation_burn(
            data["burn_tx_hash"],
            observance_burn_manager.calculate_escalation_burn(data["original_pool"]),
            data["dispute_id"]
        )
        if not is_valid:
            return jsonify({
                "error": "Observance burn verification failed",
                "details": burn_result
            }), 400

    fork_data = escalation_fork_manager.trigger_fork(
        dispute_id=data["dispute_id"],
        trigger_reason=trigger_reason,
        triggering_party=data["triggering_party"],
        original_mediator=data["original_mediator"],
        original_pool=data["original_pool"],
        burn_tx_hash=data["burn_tx_hash"],
        evidence_of_failure=data.get("evidence_of_failure")
    )

    return jsonify(fork_data)


@app.route('/fork/<fork_id>', methods=['GET'])
def get_fork_status(fork_id: str):
    """Get current status of an escalation fork."""
    if not escalation_fork_manager:
        return jsonify({"error": "Escalation fork not available"}), 503

    status = escalation_fork_manager.get_fork_status(fork_id)

    if not status:
        return jsonify({"error": "Fork not found"}), 404

    return jsonify(status)


@app.route('/fork/<fork_id>/submit-proposal', methods=['POST'])
def submit_fork_proposal(fork_id: str):
    """
    Submit a resolution proposal to an active fork.

    Request body:
    {
        "solver": "solver_id",
        "proposal_content": "Full proposal text (500+ words)",
        "addresses_concerns": ["concern1", "concern2"],
        "supporting_evidence": ["ref1", "ref2"]  (optional)
    }
    """
    if not escalation_fork_manager:
        return jsonify({"error": "Escalation fork not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["solver", "proposal_content", "addresses_concerns"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = escalation_fork_manager.submit_proposal(
        fork_id=fork_id,
        solver=data["solver"],
        proposal_content=data["proposal_content"],
        addresses_concerns=data["addresses_concerns"],
        supporting_evidence=data.get("supporting_evidence")
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/fork/<fork_id>/proposals', methods=['GET'])
def list_fork_proposals(fork_id: str):
    """List all proposals for a fork."""
    if not escalation_fork_manager:
        return jsonify({"error": "Escalation fork not available"}), 503

    if fork_id not in escalation_fork_manager.forks:
        return jsonify({"error": "Fork not found"}), 404

    proposals = escalation_fork_manager.proposals.get(fork_id, [])

    return jsonify({
        "fork_id": fork_id,
        "count": len(proposals),
        "proposals": proposals
    })


@app.route('/fork/<fork_id>/ratify', methods=['POST'])
def ratify_fork_proposal(fork_id: str):
    """
    Ratify a proposal (both parties must ratify for resolution).

    Request body:
    {
        "proposal_id": "PROP-XXX",
        "ratifying_party": "alice",
        "satisfaction_rating": 85,
        "comments": "Optional comments"
    }
    """
    if not escalation_fork_manager:
        return jsonify({"error": "Escalation fork not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["proposal_id", "ratifying_party", "satisfaction_rating"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = escalation_fork_manager.ratify_proposal(
        fork_id=fork_id,
        proposal_id=data["proposal_id"],
        ratifying_party=data["ratifying_party"],
        satisfaction_rating=data["satisfaction_rating"],
        comments=data.get("comments")
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/fork/<fork_id>/veto', methods=['POST'])
def veto_fork_proposal(fork_id: str):
    """
    Veto a proposal with documented reasoning.

    Request body:
    {
        "proposal_id": "PROP-XXX",
        "vetoing_party": "bob",
        "veto_reason": "Reason (100+ words)",
        "evidence_refs": ["ref1", "ref2"]  (optional)
    }
    """
    if not escalation_fork_manager:
        return jsonify({"error": "Escalation fork not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["proposal_id", "vetoing_party", "veto_reason"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = escalation_fork_manager.veto_proposal(
        fork_id=fork_id,
        proposal_id=data["proposal_id"],
        vetoing_party=data["vetoing_party"],
        veto_reason=data["veto_reason"],
        evidence_refs=data.get("evidence_refs")
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/fork/<fork_id>/distribution', methods=['GET'])
def get_fork_distribution(fork_id: str):
    """Get bounty distribution for a resolved fork."""
    if not escalation_fork_manager:
        return jsonify({"error": "Escalation fork not available"}), 503

    if fork_id not in escalation_fork_manager.forks:
        return jsonify({"error": "Fork not found"}), 404

    fork = escalation_fork_manager.forks[fork_id]

    if fork["status"] not in [ForkStatus.RESOLVED.value, ForkStatus.TIMEOUT.value]:
        return jsonify({
            "error": "Fork not yet resolved",
            "status": fork["status"]
        }), 400

    return jsonify({
        "fork_id": fork_id,
        "status": fork["status"],
        "bounty_pool": fork["bounty_pool"],
        "distribution": fork.get("distribution", {})
    })


@app.route('/fork/<fork_id>/audit', methods=['GET'])
def get_fork_audit_trail(fork_id: str):
    """Get complete audit trail for a fork."""
    if not escalation_fork_manager:
        return jsonify({"error": "Escalation fork not available"}), 503

    trail = escalation_fork_manager.get_fork_audit_trail(fork_id)

    if not trail:
        return jsonify({"error": "Fork not found"}), 404

    return jsonify({
        "fork_id": fork_id,
        "audit_count": len(trail),
        "audit_trail": trail
    })


@app.route('/fork/active', methods=['GET'])
def list_active_forks():
    """List all active escalation forks."""
    if not escalation_fork_manager:
        return jsonify({"error": "Escalation fork not available"}), 503

    forks = escalation_fork_manager.list_active_forks()

    return jsonify({
        "count": len(forks),
        "active_forks": forks
    })


# ========== Observance Burn Endpoints ==========

@app.route('/burn/observance', methods=['POST'])
def perform_observance_burn():
    """
    Perform an Observance Burn.

    Request body:
    {
        "burner": "0xAddress",
        "amount": 5.0,
        "reason": "VoluntarySignal|EscalationCommitment|RateLimitExcess|ProtocolViolation|CommunityDirective",
        "intent_hash": "0x..." (optional, required for EscalationCommitment),
        "epitaph": "Optional message (max 280 chars)"
    }

    Returns:
        Burn confirmation with redistribution effect
    """
    if not observance_burn_manager:
        return jsonify({
            "error": "Observance burn not available",
            "reason": "Features not initialized"
        }), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["burner", "amount", "reason"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    # Validate reason
    try:
        reason = BurnReason(data["reason"])
    except ValueError:
        return jsonify({
            "error": "Invalid reason",
            "valid_values": [r.value for r in BurnReason]
        }), 400

    # Escalation commitment requires intent_hash
    if reason == BurnReason.ESCALATION_COMMITMENT and not data.get("intent_hash"):
        return jsonify({
            "error": "intent_hash required for EscalationCommitment burns"
        }), 400

    success, result = observance_burn_manager.perform_burn(
        burner=data["burner"],
        amount=data["amount"],
        reason=reason,
        intent_hash=data.get("intent_hash"),
        epitaph=data.get("epitaph")
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/burn/voluntary', methods=['POST'])
def perform_voluntary_burn():
    """
    Perform a voluntary signal burn (simplified endpoint).

    Request body:
    {
        "burner": "0xAddress",
        "amount": 1.0,
        "epitaph": "For the health of NatLangChain"  (optional)
    }
    """
    if not observance_burn_manager:
        return jsonify({"error": "Observance burn not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "burner" not in data or "amount" not in data:
        return jsonify({
            "error": "Missing required fields",
            "required": ["burner", "amount"]
        }), 400

    success, result = observance_burn_manager.perform_voluntary_burn(
        burner=data["burner"],
        amount=data["amount"],
        epitaph=data.get("epitaph")
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/burn/history', methods=['GET'])
def get_burn_history():
    """
    Get paginated burn history.

    Query params:
        limit: Maximum burns to return (default 50)
        offset: Starting offset (default 0)
    """
    if not observance_burn_manager:
        return jsonify({"error": "Observance burn not available"}), 503

    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    history = observance_burn_manager.get_burn_history(limit=limit, offset=offset)

    return jsonify(history)


@app.route('/burn/stats', methods=['GET'])
def get_burn_statistics():
    """Get burn statistics."""
    if not observance_burn_manager:
        return jsonify({"error": "Observance burn not available"}), 503

    stats = observance_burn_manager.get_statistics()

    return jsonify(stats)


@app.route('/burn/<tx_hash>', methods=['GET'])
def get_burn_by_hash(tx_hash: str):
    """Get specific burn by transaction hash."""
    if not observance_burn_manager:
        return jsonify({"error": "Observance burn not available"}), 503

    burn = observance_burn_manager.get_burn_by_tx_hash(tx_hash)

    if not burn:
        return jsonify({"error": "Burn not found"}), 404

    return jsonify(burn)


@app.route('/burn/address/<address>', methods=['GET'])
def get_burns_by_address(address: str):
    """Get all burns by a specific address."""
    if not observance_burn_manager:
        return jsonify({"error": "Observance burn not available"}), 503

    burns = observance_burn_manager.get_burns_by_address(address)

    return jsonify({
        "address": address,
        "count": len(burns),
        "burns": burns
    })


@app.route('/burn/ledger', methods=['GET'])
def get_observance_ledger():
    """
    Get Observance Ledger data for explorer display.

    Query params:
        limit: Number of recent burns to include (default 20)
    """
    if not observance_burn_manager:
        return jsonify({"error": "Observance burn not available"}), 503

    limit = request.args.get("limit", 20, type=int)

    ledger = observance_burn_manager.get_observance_ledger(limit=limit)

    return jsonify(ledger)


@app.route('/burn/calculate-escalation', methods=['GET'])
def calculate_escalation_burn():
    """
    Calculate required burn for escalation commitment.

    Query params:
        stake: Mediation stake amount
    """
    if not observance_burn_manager:
        return jsonify({"error": "Observance burn not available"}), 503

    stake = request.args.get("stake", type=float)

    if not stake:
        return jsonify({
            "error": "Missing required parameter: stake"
        }), 400

    burn_amount = observance_burn_manager.calculate_escalation_burn(stake)

    return jsonify({
        "mediation_stake": stake,
        "burn_percentage": observance_burn_manager.DEFAULT_ESCALATION_BURN_PERCENTAGE * 100,
        "required_burn": burn_amount,
        "message": f"To escalate, you must burn {burn_amount} tokens (5% of stake)"
    })


# ========== Anti-Harassment Economic Layer Endpoints ==========

@app.route('/harassment/breach-dispute', methods=['POST'])
def initiate_breach_dispute():
    """
    Initiate a Breach/Drift Dispute with symmetric staking.

    This path requires evidence of violation/drift and symmetric staking.
    Initiator MUST stake first. Counterparty can match or decline.

    Request body:
    {
        "initiator": "alice",
        "counterparty": "bob",
        "contract_ref": "CONTRACT-123",
        "stake_amount": 100.0,
        "evidence_refs": [{"block": 1, "entry": 0}],
        "description": "Bob violated the delivery terms..."
    }

    Returns:
        Escrow details with stake window
    """
    if not anti_harassment_manager:
        return jsonify({
            "error": "Anti-harassment features not available",
            "reason": "Features not initialized"
        }), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["initiator", "counterparty", "contract_ref", "stake_amount", "evidence_refs", "description"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = anti_harassment_manager.initiate_breach_dispute(
        initiator=data["initiator"],
        counterparty=data["counterparty"],
        contract_ref=data["contract_ref"],
        stake_amount=data["stake_amount"],
        evidence_refs=data["evidence_refs"],
        description=data["description"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/harassment/match-stake', methods=['POST'])
def match_dispute_stake():
    """
    Match stake to enter symmetric dispute resolution.

    Request body:
    {
        "escrow_id": "ESCROW-XXX",
        "counterparty": "bob",
        "stake_amount": 100.0
    }
    """
    if not anti_harassment_manager:
        return jsonify({"error": "Anti-harassment features not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["escrow_id", "counterparty", "stake_amount"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = anti_harassment_manager.match_stake(
        escrow_id=data["escrow_id"],
        counterparty=data["counterparty"],
        stake_amount=data["stake_amount"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/harassment/decline-stake', methods=['POST'])
def decline_dispute_stake():
    """
    Decline to match stake (FREE for counterparty, resolves to fallback).

    This is the harassment-resistant path: counterparty pays nothing,
    initiator gets no leverage, and initiator enters cooldown.

    Request body:
    {
        "escrow_id": "ESCROW-XXX",
        "counterparty": "bob"
    }
    """
    if not anti_harassment_manager:
        return jsonify({"error": "Anti-harassment features not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "escrow_id" not in data or "counterparty" not in data:
        return jsonify({
            "error": "Missing required fields",
            "required": ["escrow_id", "counterparty"]
        }), 400

    success, result = anti_harassment_manager.decline_stake(
        escrow_id=data["escrow_id"],
        counterparty=data["counterparty"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/harassment/voluntary-request', methods=['POST'])
def initiate_voluntary_request():
    """
    Initiate a Voluntary Request (can be ignored at zero cost by recipient).

    Request body:
    {
        "initiator": "alice",
        "recipient": "bob",
        "request_type": "negotiation|amendment|reconciliation",
        "description": "I'd like to discuss...",
        "burn_fee": 0.1  (optional)
    }
    """
    if not anti_harassment_manager:
        return jsonify({"error": "Anti-harassment features not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["initiator", "recipient", "request_type", "description"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = anti_harassment_manager.initiate_voluntary_request(
        initiator=data["initiator"],
        recipient=data["recipient"],
        request_type=data["request_type"],
        description=data["description"],
        burn_fee=data.get("burn_fee")
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/harassment/respond-request', methods=['POST'])
def respond_to_voluntary_request():
    """
    Respond to a voluntary request (optional - ignoring is free).

    Request body:
    {
        "request_id": "VREQ-XXX",
        "recipient": "bob",
        "response": "I accept...",
        "accept": true
    }
    """
    if not anti_harassment_manager:
        return jsonify({"error": "Anti-harassment features not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["request_id", "recipient", "response", "accept"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = anti_harassment_manager.respond_to_voluntary_request(
        request_id=data["request_id"],
        recipient=data["recipient"],
        response=data["response"],
        accept=data["accept"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/harassment/counter-proposal', methods=['POST'])
def submit_counter_proposal():
    """
    Submit a counter-proposal with exponential fee enforcement.

    Counter-proposals are limited (default 3 per party).
    Fees increase exponentially: base_fee × 2ⁿ

    Request body:
    {
        "dispute_ref": "BREACH-XXX",
        "party": "alice",
        "proposal_content": "My counter-proposal is..."
    }
    """
    if not anti_harassment_manager:
        return jsonify({"error": "Anti-harassment features not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["dispute_ref", "party", "proposal_content"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = anti_harassment_manager.submit_counter_proposal(
        dispute_ref=data["dispute_ref"],
        party=data["party"],
        proposal_content=data["proposal_content"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/harassment/counter-status/<dispute_ref>/<party>', methods=['GET'])
def get_counter_proposal_status(dispute_ref: str, party: str):
    """
    Get counter-proposal status for a party in a dispute.

    Shows remaining counters and upcoming fees.
    """
    if not anti_harassment_manager:
        return jsonify({"error": "Anti-harassment features not available"}), 503

    status = anti_harassment_manager.get_counter_proposal_status(dispute_ref, party)
    return jsonify(status)


@app.route('/harassment/score/<address>', methods=['GET'])
def get_harassment_score(address: str):
    """
    Get harassment score and profile for an address.

    Higher scores indicate patterns of non-resolving behavior.
    Scores affect stake requirements and initiation costs.
    """
    if not anti_harassment_manager:
        return jsonify({"error": "Anti-harassment features not available"}), 503

    profile = anti_harassment_manager.get_harassment_score(address)
    return jsonify(profile)


@app.route('/harassment/escrow/<escrow_id>', methods=['GET'])
def get_escrow_status(escrow_id: str):
    """Get status of a stake escrow."""
    if not anti_harassment_manager:
        return jsonify({"error": "Anti-harassment features not available"}), 503

    if escrow_id not in anti_harassment_manager.escrows:
        return jsonify({"error": "Escrow not found"}), 404

    escrow = anti_harassment_manager.escrows[escrow_id]

    return jsonify({
        "escrow_id": escrow.escrow_id,
        "dispute_ref": escrow.dispute_ref,
        "initiator": escrow.initiator,
        "counterparty": escrow.counterparty,
        "initiator_stake": escrow.stake_amount,
        "counterparty_stake": escrow.counterparty_stake,
        "status": escrow.status,
        "resolution": escrow.resolution,
        "stake_window_ends": escrow.stake_window_ends,
        "created_at": escrow.created_at
    })


@app.route('/harassment/resolve', methods=['POST'])
def resolve_harassment_dispute():
    """
    Resolve a matched dispute.

    Request body:
    {
        "escrow_id": "ESCROW-XXX",
        "resolution": "mutual|escalated|withdrawn",
        "resolver": "mediator_node_1",
        "details": "Both parties agreed to..."
    }
    """
    if not anti_harassment_manager:
        return jsonify({"error": "Anti-harassment features not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["escrow_id", "resolution", "resolver", "details"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    try:
        resolution = DisputeResolution(data["resolution"])
    except ValueError:
        return jsonify({
            "error": "Invalid resolution type",
            "valid_values": [r.value for r in DisputeResolution]
        }), 400

    success, result = anti_harassment_manager.resolve_dispute(
        escrow_id=data["escrow_id"],
        resolution=resolution,
        resolver=data["resolver"],
        resolution_details=data["details"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/harassment/check-timeouts', methods=['POST'])
def check_stake_timeouts():
    """
    Check for stake window timeouts and resolve to fallback.

    This should be called periodically by a cron job or similar.
    """
    if not anti_harassment_manager:
        return jsonify({"error": "Anti-harassment features not available"}), 503

    resolved = anti_harassment_manager.check_stake_timeouts()

    return jsonify({
        "timeouts_resolved": len(resolved),
        "escrows": resolved
    })


@app.route('/harassment/stats', methods=['GET'])
def get_harassment_stats():
    """Get anti-harassment system statistics."""
    if not anti_harassment_manager:
        return jsonify({"error": "Anti-harassment features not available"}), 503

    stats = anti_harassment_manager.get_statistics()
    return jsonify(stats)


@app.route('/harassment/audit', methods=['GET'])
def get_harassment_audit_trail():
    """
    Get anti-harassment audit trail.

    Query params:
        limit: Maximum entries (default 100)
    """
    if not anti_harassment_manager:
        return jsonify({"error": "Anti-harassment features not available"}), 503

    limit = request.args.get("limit", 100, type=int)

    trail = anti_harassment_manager.get_audit_trail(limit=limit)

    return jsonify({
        "count": len(trail),
        "audit_trail": trail
    })


# ========== Treasury System Endpoints ==========

@app.route('/treasury/balance', methods=['GET'])
def get_treasury_balance():
    """
    Get current treasury balance and statistics.

    Returns:
        Balance details including available for subsidies
    """
    if not treasury:
        return jsonify({
            "error": "Treasury not available",
            "reason": "Features not initialized"
        }), 503

    balance = treasury.get_balance()
    return jsonify(balance)


@app.route('/treasury/deposit', methods=['POST'])
def deposit_to_treasury():
    """
    Deposit funds into treasury.

    Request body:
    {
        "amount": 100.0,
        "inflow_type": "timeout_burn|counter_fee|escalated_stake|voluntary_burn|protocol_fee|donation",
        "source": "DISPUTE-123 or address",
        "tx_hash": "0x..." (optional),
        "metadata": {} (optional)
    }
    """
    if not treasury:
        return jsonify({"error": "Treasury not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["amount", "inflow_type", "source"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    try:
        inflow_type = InflowType(data["inflow_type"])
    except ValueError:
        return jsonify({
            "error": "Invalid inflow_type",
            "valid_values": [t.value for t in InflowType]
        }), 400

    success, result = treasury.deposit(
        amount=data["amount"],
        inflow_type=inflow_type,
        source=data["source"],
        tx_hash=data.get("tx_hash"),
        metadata=data.get("metadata")
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/treasury/deposit/timeout-burn', methods=['POST'])
def deposit_timeout_burn():
    """
    Deposit from a dispute timeout burn.

    Request body:
    {
        "dispute_id": "DISPUTE-123",
        "amount": 50.0,
        "initiator": "alice"
    }
    """
    if not treasury:
        return jsonify({"error": "Treasury not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["dispute_id", "amount", "initiator"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = treasury.deposit_timeout_burn(
        dispute_id=data["dispute_id"],
        amount=data["amount"],
        initiator=data["initiator"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/treasury/deposit/counter-fee', methods=['POST'])
def deposit_counter_fee():
    """
    Deposit from counter-proposal fee burn.

    Request body:
    {
        "dispute_id": "DISPUTE-123",
        "amount": 2.0,
        "party": "alice",
        "counter_number": 2
    }
    """
    if not treasury:
        return jsonify({"error": "Treasury not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["dispute_id", "amount", "party", "counter_number"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = treasury.deposit_counter_fee(
        dispute_id=data["dispute_id"],
        amount=data["amount"],
        party=data["party"],
        counter_number=data["counter_number"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/treasury/inflows', methods=['GET'])
def get_treasury_inflows():
    """
    Get treasury inflow history.

    Query params:
        limit: Maximum inflows (default 50)
        type: Filter by inflow type (optional)
    """
    if not treasury:
        return jsonify({"error": "Treasury not available"}), 503

    limit = request.args.get("limit", 50, type=int)
    inflow_type_str = request.args.get("type")

    inflow_type = None
    if inflow_type_str:
        try:
            inflow_type = InflowType(inflow_type_str)
        except ValueError:
            return jsonify({
                "error": "Invalid inflow type",
                "valid_values": [t.value for t in InflowType]
            }), 400

    history = treasury.get_inflow_history(limit=limit, inflow_type=inflow_type)
    return jsonify(history)


@app.route('/treasury/subsidy/request', methods=['POST'])
def request_treasury_subsidy():
    """
    Request a defensive stake subsidy.

    Eligibility:
    - Must be target of dispute (not initiator)
    - Must have good on-chain dispute history
    - Dispute must not already be subsidized
    - Must not exceed per-participant cap

    Request body:
    {
        "dispute_id": "DISPUTE-123",
        "requester": "bob",
        "stake_required": 100.0,
        "is_dispute_target": true
    }
    """
    if not treasury:
        return jsonify({"error": "Treasury not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["dispute_id", "requester", "stake_required"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = treasury.request_subsidy(
        dispute_id=data["dispute_id"],
        requester=data["requester"],
        stake_required=data["stake_required"],
        is_dispute_target=data.get("is_dispute_target", True)
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/treasury/subsidy/disburse', methods=['POST'])
def disburse_treasury_subsidy():
    """
    Disburse an approved subsidy to the stake escrow.

    Request body:
    {
        "request_id": "SUBSIDY-XXX",
        "escrow_address": "0x..."
    }
    """
    if not treasury:
        return jsonify({"error": "Treasury not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "request_id" not in data or "escrow_address" not in data:
        return jsonify({
            "error": "Missing required fields",
            "required": ["request_id", "escrow_address"]
        }), 400

    success, result = treasury.disburse_subsidy(
        request_id=data["request_id"],
        escrow_address=data["escrow_address"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/treasury/subsidy/<request_id>', methods=['GET'])
def get_subsidy_request(request_id: str):
    """Get details of a subsidy request."""
    if not treasury:
        return jsonify({"error": "Treasury not available"}), 503

    request_data = treasury.get_subsidy_request(request_id)

    if not request_data:
        return jsonify({"error": "Subsidy request not found"}), 404

    return jsonify(request_data)


@app.route('/treasury/subsidy/simulate', methods=['POST'])
def simulate_subsidy():
    """
    Simulate a subsidy request without creating a record.
    Useful for UI to show potential subsidy before committing.

    Request body:
    {
        "requester": "bob",
        "stake_required": 100.0
    }
    """
    if not treasury:
        return jsonify({"error": "Treasury not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "requester" not in data or "stake_required" not in data:
        return jsonify({
            "error": "Missing required fields",
            "required": ["requester", "stake_required"]
        }), 400

    result = treasury.simulate_subsidy(
        requester=data["requester"],
        stake_required=data["stake_required"]
    )

    return jsonify(result)


@app.route('/treasury/participant/<address>', methods=['GET'])
def get_participant_subsidy_status(address: str):
    """
    Get subsidy status for a participant.

    Shows eligibility, usage, and remaining cap.
    """
    if not treasury:
        return jsonify({"error": "Treasury not available"}), 503

    status = treasury.get_participant_subsidy_status(address)
    return jsonify(status)


@app.route('/treasury/dispute/<dispute_id>/subsidized', methods=['GET'])
def check_dispute_subsidized(dispute_id: str):
    """Check if a dispute has been subsidized."""
    if not treasury:
        return jsonify({"error": "Treasury not available"}), 503

    is_subsidized, request_id = treasury.is_dispute_subsidized(dispute_id)

    return jsonify({
        "dispute_id": dispute_id,
        "is_subsidized": is_subsidized,
        "subsidy_request_id": request_id
    })


@app.route('/treasury/stats', methods=['GET'])
def get_treasury_stats():
    """Get comprehensive treasury statistics."""
    if not treasury:
        return jsonify({"error": "Treasury not available"}), 503

    stats = treasury.get_statistics()
    return jsonify(stats)


@app.route('/treasury/audit', methods=['GET'])
def get_treasury_audit():
    """
    Get treasury audit trail.

    Query params:
        limit: Maximum entries (default 100)
    """
    if not treasury:
        return jsonify({"error": "Treasury not available"}), 503

    limit = request.args.get("limit", 100, type=int)

    trail = treasury.get_audit_trail(limit=limit)

    return jsonify({
        "count": len(trail),
        "audit_trail": trail
    })


@app.route('/treasury/cleanup', methods=['POST'])
def cleanup_treasury_records():
    """
    Clean up expired usage records.
    Should be called periodically by a cron job.
    """
    if not treasury:
        return jsonify({"error": "Treasury not available"}), 503

    removed = treasury.cleanup_expired_usage()

    return jsonify({
        "status": "cleanup_complete",
        "records_removed": removed
    })


# ========== FIDO2/WebAuthn Endpoints ==========

@app.route('/fido2/register/begin', methods=['POST'])
def begin_fido2_registration():
    """
    Begin FIDO2 credential registration (WebAuthn).

    Generates a challenge for the authenticator to sign during registration.

    Request body:
    {
        "user_id": "alice",
        "user_name": "alice@example.com",
        "display_name": "Alice Smith",
        "authenticator_attachment": "platform|cross-platform" (optional),
        "user_verification": "required|preferred|discouraged" (optional)
    }

    Returns:
        Registration options to pass to WebAuthn API
    """
    if not fido2_manager:
        return jsonify({
            "error": "FIDO2 authentication not available",
            "reason": "Features not initialized"
        }), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["user_id", "user_name", "display_name"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    # Parse user verification preference
    user_verification = None
    if data.get("user_verification"):
        try:
            user_verification = UserVerification(data["user_verification"])
        except ValueError:
            return jsonify({
                "error": "Invalid user_verification",
                "valid_values": [v.value for v in UserVerification]
            }), 400

    success, result = fido2_manager.begin_registration(
        user_id=data["user_id"],
        user_name=data["user_name"],
        display_name=data["display_name"],
        authenticator_attachment=data.get("authenticator_attachment"),
        user_verification=user_verification
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/fido2/register/complete', methods=['POST'])
def complete_fido2_registration():
    """
    Complete FIDO2 credential registration.

    Verifies the authenticator response and stores the credential.

    Request body:
    {
        "challenge_id": "CHALLENGE-XXX",
        "credential_id": "base64-encoded-credential-id",
        "public_key": "base64-encoded-public-key",
        "attestation_object": "base64-encoded-attestation",
        "client_data_json": "base64-encoded-client-data",
        "device_name": "My YubiKey 5" (optional)
    }

    Returns:
        Credential confirmation with fingerprint
    """
    if not fido2_manager:
        return jsonify({"error": "FIDO2 authentication not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["challenge_id", "credential_id", "public_key", "attestation_object", "client_data_json"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = fido2_manager.complete_registration(
        challenge_id=data["challenge_id"],
        credential_id=data["credential_id"],
        public_key=data["public_key"],
        attestation_object=data["attestation_object"],
        client_data_json=data["client_data_json"],
        device_name=data.get("device_name")
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/fido2/authenticate/begin', methods=['POST'])
def begin_fido2_authentication():
    """
    Begin FIDO2 authentication challenge.

    Request body:
    {
        "user_id": "alice",
        "user_verification": "required|preferred|discouraged" (optional)
    }

    Returns:
        Authentication options to pass to WebAuthn API
    """
    if not fido2_manager:
        return jsonify({"error": "FIDO2 authentication not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "user_id" not in data:
        return jsonify({
            "error": "Missing required field: user_id"
        }), 400

    # Parse user verification preference
    user_verification = None
    if data.get("user_verification"):
        try:
            user_verification = UserVerification(data["user_verification"])
        except ValueError:
            return jsonify({
                "error": "Invalid user_verification",
                "valid_values": [v.value for v in UserVerification]
            }), 400

    success, result = fido2_manager.begin_authentication(
        user_id=data["user_id"],
        user_verification=user_verification
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/fido2/authenticate/verify', methods=['POST'])
def verify_fido2_authentication():
    """
    Verify FIDO2 authentication response.

    Request body:
    {
        "challenge_id": "CHALLENGE-XXX",
        "credential_id": "base64-encoded-credential-id",
        "authenticator_data": "base64-encoded-auth-data",
        "client_data_json": "base64-encoded-client-data",
        "signature": "base64-encoded-signature"
    }

    Returns:
        Authentication result with session token
    """
    if not fido2_manager:
        return jsonify({"error": "FIDO2 authentication not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["challenge_id", "credential_id", "authenticator_data", "client_data_json", "signature"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = fido2_manager.verify_authentication(
        challenge_id=data["challenge_id"],
        credential_id=data["credential_id"],
        authenticator_data=data["authenticator_data"],
        client_data_json=data["client_data_json"],
        signature=data["signature"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/fido2/sign/proposal', methods=['POST'])
def sign_proposal_with_fido2():
    """
    Sign a proposal with FIDO2 hardware key.

    Used for acceptProposal and submitLLMProposal operations
    requiring hardware-backed authorization.

    Request body:
    {
        "user_id": "alice",
        "credential_id": "base64-encoded-credential-id",
        "proposal_hash": "0x...",
        "proposal_content": "Full proposal text",
        "signature": "base64-encoded-signature",
        "authenticator_data": "base64-encoded-auth-data",
        "client_data_json": "base64-encoded-client-data"
    }

    Returns:
        Signed proposal with verification proof
    """
    if not fido2_manager:
        return jsonify({"error": "FIDO2 authentication not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["user_id", "credential_id", "proposal_hash", "proposal_content",
                       "signature", "authenticator_data", "client_data_json"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = fido2_manager.sign_proposal(
        user_id=data["user_id"],
        credential_id=data["credential_id"],
        proposal_hash=data["proposal_hash"],
        proposal_content=data["proposal_content"],
        signature=data["signature"],
        authenticator_data=data["authenticator_data"],
        client_data_json=data["client_data_json"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/fido2/sign/contract', methods=['POST'])
def sign_contract_with_fido2():
    """
    Sign a contract with FIDO2 hardware key.

    Provides hardware-backed authorization for contract execution.

    Request body:
    {
        "user_id": "alice",
        "credential_id": "base64-encoded-credential-id",
        "contract_hash": "0x...",
        "contract_content": "Full contract text",
        "counterparty": "bob",
        "signature": "base64-encoded-signature",
        "authenticator_data": "base64-encoded-auth-data",
        "client_data_json": "base64-encoded-client-data"
    }

    Returns:
        Signed contract with verification proof
    """
    if not fido2_manager:
        return jsonify({"error": "FIDO2 authentication not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["user_id", "credential_id", "contract_hash", "contract_content",
                       "counterparty", "signature", "authenticator_data", "client_data_json"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = fido2_manager.sign_contract(
        user_id=data["user_id"],
        credential_id=data["credential_id"],
        contract_hash=data["contract_hash"],
        contract_content=data["contract_content"],
        counterparty=data["counterparty"],
        signature=data["signature"],
        authenticator_data=data["authenticator_data"],
        client_data_json=data["client_data_json"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/fido2/delegation/begin', methods=['POST'])
def begin_agent_delegation():
    """
    Begin hardware-authorized agent delegation.

    Creates a challenge for authorizing an agent to act on user's behalf
    with specified permissions and limits.

    Request body:
    {
        "user_id": "alice",
        "agent_id": "agent-bot-1",
        "permissions": ["submit_proposals", "sign_contracts"],
        "spending_limit": 1000.0 (optional),
        "expires_in_hours": 24 (optional),
        "contract_refs": ["CONTRACT-123"] (optional, limit to specific contracts)
    }

    Returns:
        Delegation challenge to sign
    """
    if not fido2_manager:
        return jsonify({"error": "FIDO2 authentication not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["user_id", "agent_id", "permissions"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = fido2_manager.begin_agent_delegation(
        user_id=data["user_id"],
        agent_id=data["agent_id"],
        permissions=data["permissions"],
        spending_limit=data.get("spending_limit"),
        expires_in_hours=data.get("expires_in_hours", 24),
        contract_refs=data.get("contract_refs")
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/fido2/delegation/complete', methods=['POST'])
def complete_agent_delegation():
    """
    Complete agent delegation with hardware signature.

    Request body:
    {
        "challenge_id": "CHALLENGE-XXX",
        "credential_id": "base64-encoded-credential-id",
        "signature": "base64-encoded-signature",
        "authenticator_data": "base64-encoded-auth-data",
        "client_data_json": "base64-encoded-client-data"
    }

    Returns:
        Active delegation with token
    """
    if not fido2_manager:
        return jsonify({"error": "FIDO2 authentication not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["challenge_id", "credential_id", "signature", "authenticator_data", "client_data_json"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = fido2_manager.complete_agent_delegation(
        challenge_id=data["challenge_id"],
        credential_id=data["credential_id"],
        signature=data["signature"],
        authenticator_data=data["authenticator_data"],
        client_data_json=data["client_data_json"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/fido2/delegation/<delegation_id>', methods=['GET'])
def get_agent_delegation(delegation_id: str):
    """Get details of an agent delegation."""
    if not fido2_manager:
        return jsonify({"error": "FIDO2 authentication not available"}), 503

    delegation = fido2_manager.get_delegation(delegation_id)

    if not delegation:
        return jsonify({"error": "Delegation not found"}), 404

    return jsonify(delegation)


@app.route('/fido2/delegation/<delegation_id>/revoke', methods=['POST'])
def revoke_agent_delegation(delegation_id: str):
    """
    Revoke an agent delegation.

    Request body:
    {
        "user_id": "alice",
        "reason": "Optional revocation reason"
    }

    Returns:
        Revocation confirmation
    """
    if not fido2_manager:
        return jsonify({"error": "FIDO2 authentication not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "user_id" not in data:
        return jsonify({
            "error": "Missing required field: user_id"
        }), 400

    success, result = fido2_manager.revoke_delegation(
        delegation_id=delegation_id,
        user_id=data["user_id"],
        reason=data.get("reason")
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/fido2/delegation/user/<user_id>', methods=['GET'])
def get_user_delegations(user_id: str):
    """
    Get all delegations for a user.

    Query params:
        active_only: true/false (default true)
    """
    if not fido2_manager:
        return jsonify({"error": "FIDO2 authentication not available"}), 503

    active_only = request.args.get("active_only", "true").lower() == "true"

    delegations = fido2_manager.get_user_delegations(user_id, active_only=active_only)

    return jsonify({
        "user_id": user_id,
        "count": len(delegations),
        "delegations": delegations
    })


@app.route('/fido2/delegation/verify', methods=['POST'])
def verify_agent_action():
    """
    Verify an agent action against its delegation.

    Request body:
    {
        "delegation_id": "DELEG-XXX",
        "agent_id": "agent-bot-1",
        "action": "submit_proposals|sign_contracts|...",
        "spending_amount": 50.0 (optional),
        "contract_ref": "CONTRACT-123" (optional)
    }

    Returns:
        Verification result
    """
    if not fido2_manager:
        return jsonify({"error": "FIDO2 authentication not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["delegation_id", "agent_id", "action"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    is_valid, result = fido2_manager.verify_agent_action(
        delegation_id=data["delegation_id"],
        agent_id=data["agent_id"],
        action=data["action"],
        spending_amount=data.get("spending_amount"),
        contract_ref=data.get("contract_ref")
    )

    return jsonify({
        "valid": is_valid,
        "result": result
    })


@app.route('/fido2/credentials/<user_id>', methods=['GET'])
def get_user_credentials(user_id: str):
    """Get all FIDO2 credentials for a user."""
    if not fido2_manager:
        return jsonify({"error": "FIDO2 authentication not available"}), 503

    credentials = fido2_manager.get_user_credentials(user_id)

    return jsonify({
        "user_id": user_id,
        "count": len(credentials),
        "credentials": credentials
    })


@app.route('/fido2/credentials/<user_id>/<credential_id>', methods=['DELETE'])
def remove_user_credential(user_id: str, credential_id: str):
    """
    Remove a FIDO2 credential.

    Note: User must have at least one remaining credential.
    """
    if not fido2_manager:
        return jsonify({"error": "FIDO2 authentication not available"}), 503

    success, result = fido2_manager.remove_credential(user_id, credential_id)

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/fido2/signatures/<user_id>', methods=['GET'])
def get_signature_history(user_id: str):
    """
    Get signature history for a user.

    Query params:
        limit: Maximum signatures (default 50)
        signature_type: proposal|contract|delegation|authentication (optional)
    """
    if not fido2_manager:
        return jsonify({"error": "FIDO2 authentication not available"}), 503

    limit = request.args.get("limit", 50, type=int)
    sig_type_str = request.args.get("signature_type")

    signature_type = None
    if sig_type_str:
        try:
            signature_type = SignatureType(sig_type_str)
        except ValueError:
            return jsonify({
                "error": "Invalid signature_type",
                "valid_values": [t.value for t in SignatureType]
            }), 400

    history = fido2_manager.get_signature_history(
        user_id=user_id,
        limit=limit,
        signature_type=signature_type
    )

    return jsonify({
        "user_id": user_id,
        "count": len(history),
        "signatures": history
    })


@app.route('/fido2/stats', methods=['GET'])
def get_fido2_stats():
    """Get FIDO2 authentication statistics."""
    if not fido2_manager:
        return jsonify({"error": "FIDO2 authentication not available"}), 503

    stats = fido2_manager.get_statistics()
    return jsonify(stats)


@app.route('/fido2/audit', methods=['GET'])
def get_fido2_audit():
    """
    Get FIDO2 audit trail.

    Query params:
        limit: Maximum entries (default 100)
    """
    if not fido2_manager:
        return jsonify({"error": "FIDO2 authentication not available"}), 503

    limit = request.args.get("limit", 100, type=int)

    trail = fido2_manager.get_audit_trail(limit=limit)

    return jsonify({
        "count": len(trail),
        "audit_trail": trail
    })


# ========== ZK Privacy Infrastructure Endpoints ==========

# ----- Phase 14A: Dispute Membership Circuit -----

@app.route('/zk/identity/commitment', methods=['POST'])
def generate_identity_commitment():
    """
    Generate identity commitment for on-chain registration.

    Creates a secret and its Poseidon hash for privacy-preserving
    dispute membership proofs.

    Request body:
    {
        "user_address": "0x...",
        "salt": "optional-salt-hex" (optional)
    }

    Returns:
        Identity secret and hash for on-chain commitment
    """
    if not zk_privacy_manager:
        return jsonify({
            "error": "ZK privacy not available",
            "reason": "Features not initialized"
        }), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "user_address" not in data:
        return jsonify({
            "error": "Missing required field: user_address"
        }), 400

    result = zk_privacy_manager.generate_identity_commitment(
        user_address=data["user_address"],
        salt=data.get("salt")
    )

    return jsonify(result), 201


@app.route('/zk/identity/proof', methods=['POST'])
def generate_identity_proof():
    """
    Generate ZK proof of dispute membership.

    Proves "I know a secret that hashes to the on-chain identity"
    without revealing the secret or address.

    Request body:
    {
        "dispute_id": "DISPUTE-XXX",
        "prover_address": "0x...",
        "identity_secret": "salt:address",
        "identity_manager": "0x..." (on-chain hash)
    }

    Returns:
        ZK proof components (a, b, c) and public signals
    """
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["dispute_id", "prover_address", "identity_secret", "identity_manager"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = zk_privacy_manager.generate_identity_proof(
        dispute_id=data["dispute_id"],
        prover_address=data["prover_address"],
        identity_secret=data["identity_secret"],
        identity_manager=data["identity_manager"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/zk/identity/verify', methods=['POST'])
def verify_identity_proof():
    """
    Verify ZK identity proof on-chain (simulated).

    Request body:
    {
        "proof_id": "PROOF-XXX",
        "expected_identity_hash": "0x..." (from dispute struct)
    }

    Returns:
        Verification result
    """
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "proof_id" not in data or "expected_identity_hash" not in data:
        return jsonify({
            "error": "Missing required fields",
            "required": ["proof_id", "expected_identity_hash"]
        }), 400

    success, result = zk_privacy_manager.verify_identity_proof(
        proof_id=data["proof_id"],
        expected_identity_hash=data["expected_identity_hash"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/zk/identity/proof/<proof_id>', methods=['GET'])
def get_identity_proof(proof_id: str):
    """Get identity proof details."""
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    proof = zk_privacy_manager.membership_circuit.get_proof(proof_id)

    if not proof:
        return jsonify({"error": "Proof not found"}), 404

    return jsonify(proof)


# ----- Phase 14B: Viewing Key Infrastructure -----

@app.route('/zk/viewing-key/create', methods=['POST'])
def create_viewing_key():
    """
    Create a viewing key for dispute metadata.

    Generates ECIES keypair, encrypts metadata, and splits
    the private key via Shamir's Secret Sharing.

    Request body:
    {
        "dispute_id": "DISPUTE-XXX",
        "metadata": {"evidence": "...", "parties": [...]},
        "share_holders": ["holder1", "holder2", ...] (optional),
        "threshold": 3 (optional)
    }

    Returns:
        Key info, encrypted metadata, and share distribution
    """
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "dispute_id" not in data or "metadata" not in data:
        return jsonify({
            "error": "Missing required fields",
            "required": ["dispute_id", "metadata"]
        }), 400

    success, result = zk_privacy_manager.create_viewing_key(
        dispute_id=data["dispute_id"],
        metadata=data["metadata"],
        share_holders=data.get("share_holders"),
        threshold=data.get("threshold", 3)
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/zk/viewing-key/share', methods=['POST'])
def submit_viewing_key_share():
    """
    Submit a key share for reconstruction.

    Share holders submit their shares when key reconstruction
    is authorized (e.g., legal warrant).

    Request body:
    {
        "key_id": "VKEY-XXX",
        "holder": "holder_address",
        "share_data": "0x..."
    }

    Returns:
        Share submission status
    """
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["key_id", "holder", "share_data"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = zk_privacy_manager.submit_key_share(
        key_id=data["key_id"],
        holder=data["holder"],
        share_data=data["share_data"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/zk/viewing-key/reconstruct', methods=['POST'])
def reconstruct_viewing_key():
    """
    Reconstruct viewing key from submitted shares.

    Requires sufficient shares (m-of-n) and valid authorization.

    Request body:
    {
        "key_id": "VKEY-XXX",
        "authorization": "warrant_hash_or_approval_id"
    }

    Returns:
        Reconstructed private key
    """
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "key_id" not in data or "authorization" not in data:
        return jsonify({
            "error": "Missing required fields",
            "required": ["key_id", "authorization"]
        }), 400

    success, result = zk_privacy_manager.reconstruct_viewing_key(
        key_id=data["key_id"],
        authorization=data["authorization"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/zk/viewing-key/<key_id>', methods=['GET'])
def get_viewing_key_status(key_id: str):
    """Get viewing key status."""
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    status = zk_privacy_manager.viewing_keys.get_key_status(key_id)

    if not status:
        return jsonify({"error": "Viewing key not found"}), 404

    return jsonify(status)


# ----- Phase 14C: Inference Attack Mitigations -----

@app.route('/zk/batch/submit', methods=['POST'])
def submit_to_batch():
    """
    Submit transaction to batching queue.

    Transactions are aggregated and released in batches
    to prevent timing correlation attacks.

    Request body:
    {
        "tx_type": "identity_proof|viewing_key|...",
        "tx_data": {...}
    }

    Returns:
        Batch assignment info
    """
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "tx_type" not in data or "tx_data" not in data:
        return jsonify({
            "error": "Missing required fields",
            "required": ["tx_type", "tx_data"]
        }), 400

    success, result = zk_privacy_manager.submit_to_batch(
        tx_type=data["tx_type"],
        tx_data=data["tx_data"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/zk/batch/advance', methods=['POST'])
def advance_block_release():
    """
    Advance block and release ready batches.

    Also potentially generates dummy transactions.

    Request body:
    {
        "new_block": 12345
    }

    Returns:
        Released transactions
    """
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    data = request.get_json()

    if not data or "new_block" not in data:
        return jsonify({
            "error": "Missing required field: new_block"
        }), 400

    released = zk_privacy_manager.advance_block(data["new_block"])

    return jsonify({
        "block": data["new_block"],
        "released_count": len(released),
        "transactions": released
    })


@app.route('/zk/batch/<batch_id>', methods=['GET'])
def get_batch_status(batch_id: str):
    """Get batch status."""
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    status = zk_privacy_manager.batching_queue.get_batch_status(batch_id)

    if not status:
        return jsonify({"error": "Batch not found"}), 404

    return jsonify(status)


@app.route('/zk/dummy/generate', methods=['POST'])
def generate_dummy_transaction():
    """
    Manually generate a dummy transaction.

    Normally automated via Chainlink, but available for testing.

    Returns:
        Generated dummy transaction
    """
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    dummy = zk_privacy_manager.dummy_generator.generate_dummy()

    return jsonify(dummy)


@app.route('/zk/dummy/stats', methods=['GET'])
def get_dummy_stats():
    """Get dummy transaction statistics."""
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    stats = zk_privacy_manager.dummy_generator.get_statistics()
    return jsonify(stats)


# ----- Phase 14D: Threshold Decryption / Compliance -----

@app.route('/zk/compliance/request', methods=['POST'])
def submit_compliance_request():
    """
    Submit compliance request for key disclosure.

    Initiates voting by the Compliance Council.

    Request body:
    {
        "key_id": "VKEY-XXX",
        "requester": "legal_authority",
        "warrant_hash": "0x...",
        "justification": "Court order #12345..."
    }

    Returns:
        Request info with voting requirements
    """
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["key_id", "requester", "warrant_hash", "justification"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = zk_privacy_manager.submit_compliance_request(
        key_id=data["key_id"],
        requester=data["requester"],
        warrant_hash=data["warrant_hash"],
        justification=data["justification"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/zk/compliance/vote', methods=['POST'])
def submit_compliance_vote():
    """
    Submit vote on compliance request.

    Council members vote to approve or reject key disclosure.

    Request body:
    {
        "request_id": "CREQ-XXX",
        "voter": "council_member_address",
        "approve": true/false,
        "signature": "BLS_signature"
    }

    Returns:
        Vote status and current tally
    """
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["request_id", "voter", "approve", "signature"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = zk_privacy_manager.submit_compliance_vote(
        request_id=data["request_id"],
        voter=data["voter"],
        approve=data["approve"],
        signature=data["signature"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/zk/compliance/<request_id>', methods=['GET'])
def get_compliance_request_status(request_id: str):
    """Get compliance request status."""
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    status = zk_privacy_manager.get_compliance_status(request_id)

    if not status:
        return jsonify({"error": "Compliance request not found"}), 404

    return jsonify(status)


@app.route('/zk/compliance/threshold-sign', methods=['POST'])
def generate_threshold_signature():
    """
    Generate threshold signature for approved request.

    Aggregates partial BLS signatures from approving council members.

    Request body:
    {
        "request_id": "CREQ-XXX",
        "message": "message to sign"
    }

    Returns:
        Aggregated threshold signature
    """
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "request_id" not in data or "message" not in data:
        return jsonify({
            "error": "Missing required fields",
            "required": ["request_id", "message"]
        }), 400

    success, result = zk_privacy_manager.threshold_decryption.generate_threshold_signature(
        request_id=data["request_id"],
        message=data["message"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/zk/compliance/council', methods=['GET'])
def get_compliance_council():
    """Get compliance council members."""
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    council = zk_privacy_manager.threshold_decryption.council_members
    public_keys = zk_privacy_manager.threshold_decryption.member_public_keys

    return jsonify({
        "council_size": len(council),
        "default_threshold": zk_privacy_manager.threshold_decryption.DEFAULT_THRESHOLD,
        "members": [
            {"address": m, "public_key": public_keys.get(m, "unknown")}
            for m in council
        ]
    })


# ----- ZK Privacy General -----

@app.route('/zk/stats', methods=['GET'])
def get_zk_privacy_stats():
    """Get ZK privacy infrastructure statistics."""
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    stats = zk_privacy_manager.get_statistics()
    return jsonify(stats)


@app.route('/zk/audit', methods=['GET'])
def get_zk_privacy_audit():
    """
    Get ZK privacy audit trail.

    Query params:
        limit: Maximum entries (default 100)
    """
    if not zk_privacy_manager:
        return jsonify({"error": "ZK privacy not available"}), 503

    limit = request.args.get("limit", 100, type=int)

    trail = zk_privacy_manager.get_audit_trail(limit=limit)

    return jsonify({
        "count": len(trail),
        "audit_trail": trail
    })


# ========== Automated Negotiation Engine Endpoints ==========

@app.route('/negotiation/session', methods=['POST'])
def initiate_negotiation_session():
    """
    Initiate a new negotiation session.

    Request body:
    {
        "initiator": "alice",
        "counterparty": "bob",
        "subject": "Software development contract",
        "initiator_statement": "I want to hire a developer for 3 months...",
        "initial_terms": {"budget": "50000", "timeline": "3 months"} (optional)
    }

    Returns:
        Session info with ID and next steps
    """
    if not negotiation_engine:
        return jsonify({
            "error": "Negotiation engine not available",
            "reason": "Features not initialized"
        }), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["initiator", "counterparty", "subject", "initiator_statement"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    success, result = negotiation_engine.initiate_session(
        initiator=data["initiator"],
        counterparty=data["counterparty"],
        subject=data["subject"],
        initiator_statement=data["initiator_statement"],
        initial_terms=data.get("initial_terms")
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/negotiation/session/<session_id>/join', methods=['POST'])
def join_negotiation_session(session_id: str):
    """
    Counterparty joins a negotiation session.

    Request body:
    {
        "counterparty": "bob",
        "counterparty_statement": "I'm available for contract work..."
    }

    Returns:
        Alignment analysis and next steps
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "counterparty" not in data or "counterparty_statement" not in data:
        return jsonify({
            "error": "Missing required fields",
            "required": ["counterparty", "counterparty_statement"]
        }), 400

    success, result = negotiation_engine.join_session(
        session_id=session_id,
        counterparty=data["counterparty"],
        counterparty_statement=data["counterparty_statement"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/negotiation/session/<session_id>', methods=['GET'])
def get_negotiation_session(session_id: str):
    """Get negotiation session details."""
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    session = negotiation_engine.get_session(session_id)

    if not session:
        return jsonify({"error": "Session not found"}), 404

    return jsonify(session)


@app.route('/negotiation/session/<session_id>/advance', methods=['POST'])
def advance_negotiation_phase(session_id: str):
    """
    Advance session to next phase.

    Request body:
    {
        "party": "alice"
    }

    Returns:
        Phase transition info
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    data = request.get_json()

    if not data or "party" not in data:
        return jsonify({"error": "Missing required field: party"}), 400

    success, result = negotiation_engine.advance_phase(
        session_id=session_id,
        party=data["party"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/negotiation/session/<session_id>/clause', methods=['POST'])
def add_negotiation_clause(session_id: str):
    """
    Add a clause to the session.

    Request body:
    {
        "clause_type": "payment|delivery|quality|timeline|...",
        "parameters": {"amount": "50000", "method": "wire transfer", ...},
        "proposed_by": "alice"
    }

    Returns:
        Generated clause with alternatives
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["clause_type", "parameters", "proposed_by"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    try:
        clause_type = ClauseType(data["clause_type"])
    except ValueError:
        return jsonify({
            "error": "Invalid clause_type",
            "valid_values": [t.value for t in ClauseType]
        }), 400

    success, result = negotiation_engine.add_clause(
        session_id=session_id,
        clause_type=clause_type,
        parameters=data["parameters"],
        proposed_by=data["proposed_by"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/negotiation/session/<session_id>/clause/<clause_id>/respond', methods=['POST'])
def respond_to_negotiation_clause(session_id: str, clause_id: str):
    """
    Respond to a proposed clause.

    Request body:
    {
        "party": "bob",
        "response": "accept|reject|modify",
        "modified_content": "New clause text..." (required if modify)
    }

    Returns:
        Clause status update
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "party" not in data or "response" not in data:
        return jsonify({
            "error": "Missing required fields",
            "required": ["party", "response"]
        }), 400

    if data["response"] not in ["accept", "reject", "modify"]:
        return jsonify({
            "error": "Invalid response",
            "valid_values": ["accept", "reject", "modify"]
        }), 400

    success, result = negotiation_engine.respond_to_clause(
        session_id=session_id,
        clause_id=clause_id,
        party=data["party"],
        response=data["response"],
        modified_content=data.get("modified_content")
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/negotiation/session/<session_id>/clauses', methods=['GET'])
def get_negotiation_clauses(session_id: str):
    """Get all clauses in a session."""
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    clauses = negotiation_engine.get_session_clauses(session_id)

    return jsonify({
        "session_id": session_id,
        "count": len(clauses),
        "clauses": clauses
    })


@app.route('/negotiation/session/<session_id>/offer', methods=['POST'])
def make_negotiation_offer(session_id: str):
    """
    Make an offer in the negotiation.

    Request body:
    {
        "from_party": "alice",
        "terms": {"price": "45000", "timeline": "2.5 months", ...},
        "message": "I've adjusted the timeline to accommodate...",
        "offer_type": "initial|counter|final" (optional, default initial)
    }

    Returns:
        Offer confirmation
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["from_party", "terms", "message"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    offer_type = OfferType.INITIAL
    if data.get("offer_type"):
        try:
            offer_type = OfferType(data["offer_type"])
        except ValueError:
            return jsonify({
                "error": "Invalid offer_type",
                "valid_values": [t.value for t in OfferType]
            }), 400

    success, result = negotiation_engine.make_offer(
        session_id=session_id,
        from_party=data["from_party"],
        terms=data["terms"],
        message=data["message"],
        offer_type=offer_type
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/negotiation/session/<session_id>/offer/<offer_id>/respond', methods=['POST'])
def respond_to_negotiation_offer(session_id: str, offer_id: str):
    """
    Respond to an offer.

    Request body:
    {
        "party": "bob",
        "response": "accept|reject|counter",
        "counter_terms": {...} (required if counter),
        "message": "Response message..." (optional)
    }

    Returns:
        Response result (agreement if accepted)
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "party" not in data or "response" not in data:
        return jsonify({
            "error": "Missing required fields",
            "required": ["party", "response"]
        }), 400

    if data["response"] not in ["accept", "reject", "counter"]:
        return jsonify({
            "error": "Invalid response",
            "valid_values": ["accept", "reject", "counter"]
        }), 400

    success, result = negotiation_engine.respond_to_offer(
        session_id=session_id,
        offer_id=offer_id,
        party=data["party"],
        response=data["response"],
        counter_terms=data.get("counter_terms"),
        message=data.get("message")
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/negotiation/session/<session_id>/offers', methods=['GET'])
def get_negotiation_offers(session_id: str):
    """Get all offers in a session."""
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    offers = negotiation_engine.get_session_offers(session_id)

    return jsonify({
        "session_id": session_id,
        "count": len(offers),
        "offers": offers
    })


@app.route('/negotiation/session/<session_id>/auto-counter', methods=['POST'])
def auto_draft_counter_offer(session_id: str):
    """
    Automatically draft a counter-offer using AI.

    Request body:
    {
        "party": "bob",
        "strategy": "aggressive|balanced|cooperative" (optional, default balanced)
    }

    Returns:
        AI-drafted counter-offer
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    data = request.get_json()

    if not data or "party" not in data:
        return jsonify({"error": "Missing required field: party"}), 400

    strategy = data.get("strategy", "balanced")
    if strategy not in ["aggressive", "balanced", "cooperative"]:
        return jsonify({
            "error": "Invalid strategy",
            "valid_values": ["aggressive", "balanced", "cooperative"]
        }), 400

    success, result = negotiation_engine.auto_draft_counter(
        session_id=session_id,
        party=data["party"],
        strategy=strategy
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result), 201


@app.route('/negotiation/session/<session_id>/strategies', methods=['GET'])
def get_alignment_strategies(session_id: str):
    """
    Get alignment strategies for a party.

    Query params:
        party: Party to get strategies for
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    party = request.args.get("party")
    if not party:
        return jsonify({"error": "Missing required query param: party"}), 400

    strategies = negotiation_engine.get_alignment_strategies(session_id, party)

    return jsonify({
        "session_id": session_id,
        "party": party,
        "strategies": strategies
    })


@app.route('/negotiation/session/<session_id>/finalize', methods=['POST'])
def finalize_negotiation_agreement(session_id: str):
    """
    Finalize an agreed negotiation into a contract.

    Request body:
    {
        "party": "alice"
    }

    Returns:
        Final contract document
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    data = request.get_json()

    if not data or "party" not in data:
        return jsonify({"error": "Missing required field: party"}), 400

    success, result = negotiation_engine.finalize_agreement(
        session_id=session_id,
        party=data["party"]
    )

    if not success:
        return jsonify(result), 400

    return jsonify(result)


@app.route('/negotiation/stats', methods=['GET'])
def get_negotiation_stats():
    """Get negotiation engine statistics."""
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    stats = negotiation_engine.get_statistics()
    return jsonify(stats)


@app.route('/negotiation/audit', methods=['GET'])
def get_negotiation_audit():
    """
    Get negotiation audit trail.

    Query params:
        limit: Maximum entries (default 100)
    """
    if not negotiation_engine:
        return jsonify({"error": "Negotiation engine not available"}), 503

    limit = request.args.get("limit", 100, type=int)

    trail = negotiation_engine.get_audit_trail(limit=limit)

    return jsonify({
        "count": len(trail),
        "audit_trail": trail
    })


@app.route('/negotiation/clause-types', methods=['GET'])
def get_clause_types():
    """Get available clause types."""
    return jsonify({
        "clause_types": [
            {
                "value": t.value,
                "name": t.name,
                "description": {
                    "payment": "Payment terms and conditions",
                    "delivery": "Delivery location and timing",
                    "quality": "Quality standards and verification",
                    "timeline": "Project timeline and milestones",
                    "liability": "Liability limits and exclusions",
                    "termination": "Contract termination conditions",
                    "dispute_resolution": "Dispute resolution method",
                    "confidentiality": "Confidentiality and NDA terms",
                    "custom": "Custom clause"
                }.get(t.value, "Contract clause")
            }
            for t in ClauseType
        ]
    })


# ========== Market-Aware Pricing Endpoints ==========

@app.route('/market/price/<asset>', methods=['GET'])
def get_market_price(asset: str):
    """
    Get current price for an asset.

    Path params:
        asset: Asset symbol (e.g., BTC, ETH, EUR/USD, GOLD)

    Returns:
        Current price data
    """
    if not market_pricing:
        return jsonify({
            "error": "Market pricing not available",
            "reason": "Features not initialized"
        }), 503

    price = market_pricing.get_price(asset)

    if not price:
        return jsonify({"error": f"Price not found for asset: {asset}"}), 404

    return jsonify(price)


@app.route('/market/prices', methods=['POST'])
def get_market_prices():
    """
    Get prices for multiple assets.

    Request body:
    {
        "assets": ["BTC", "ETH", "GOLD", ...]
    }

    Returns:
        Prices for all requested assets
    """
    if not market_pricing:
        return jsonify({"error": "Market pricing not available"}), 503

    data = request.get_json()

    if not data or "assets" not in data:
        return jsonify({"error": "Missing required field: assets"}), 400

    prices = market_pricing.get_prices(data["assets"])

    return jsonify({
        "count": len(prices),
        "prices": prices
    })


@app.route('/market/analyze/<asset>', methods=['GET'])
def analyze_market_asset(asset: str):
    """
    Get market analysis for an asset.

    Path params:
        asset: Asset to analyze

    Returns:
        Market analysis (condition, trend, volatility, etc.)
    """
    if not market_pricing:
        return jsonify({"error": "Market pricing not available"}), 503

    analysis = market_pricing.analyze_market(asset)

    return jsonify(analysis)


@app.route('/market/summary', methods=['POST'])
def get_market_summary():
    """
    Get market summary for multiple assets.

    Request body:
    {
        "assets": ["BTC", "ETH", "SPX", ...]
    }

    Returns:
        Summary with analysis for each asset
    """
    if not market_pricing:
        return jsonify({"error": "Market pricing not available"}), 503

    data = request.get_json()

    if not data or "assets" not in data:
        return jsonify({"error": "Missing required field: assets"}), 400

    summary = market_pricing.get_market_summary(data["assets"])

    return jsonify(summary)


@app.route('/market/suggest-price', methods=['POST'])
def suggest_market_price():
    """
    Get a price suggestion for a negotiation.

    Request body:
    {
        "asset_or_service": "BTC" or "Software Development",
        "base_amount": 1.5,
        "currency": "USD" (optional),
        "strategy": "market|premium|discount|anchored|competitive|value_based" (optional),
        "context": "Optional negotiation context" (optional)
    }

    Returns:
        Price suggestion with range and reasoning
    """
    if not market_pricing:
        return jsonify({"error": "Market pricing not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "asset_or_service" not in data or "base_amount" not in data:
        return jsonify({
            "error": "Missing required fields",
            "required": ["asset_or_service", "base_amount"]
        }), 400

    suggestion = market_pricing.suggest_price(
        asset_or_service=data["asset_or_service"],
        base_amount=data["base_amount"],
        currency=data.get("currency", "USD"),
        strategy=data.get("strategy", "market"),
        context=data.get("context")
    )

    return jsonify(suggestion)


@app.route('/market/adjust-price', methods=['POST'])
def adjust_market_price():
    """
    Adjust a price based on market conditions.

    Request body:
    {
        "base_price": 50000.0,
        "asset": "BTC",
        "adjustment_type": "auto|conservative|aggressive" (optional)
    }

    Returns:
        Adjusted price with reasoning
    """
    if not market_pricing:
        return jsonify({"error": "Market pricing not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "base_price" not in data or "asset" not in data:
        return jsonify({
            "error": "Missing required fields",
            "required": ["base_price", "asset"]
        }), 400

    result = market_pricing.adjust_price(
        base_price=data["base_price"],
        asset=data["asset"],
        adjustment_type=data.get("adjustment_type", "auto")
    )

    return jsonify(result)


@app.route('/market/counteroffer', methods=['POST'])
def generate_market_counteroffer():
    """
    Generate a market-aware counter-offer price.

    Request body:
    {
        "their_offer": 45000.0,
        "your_target": 50000.0,
        "asset": "BTC",
        "round_number": 2,
        "max_rounds": 10 (optional)
    }

    Returns:
        Counter-offer price with reasoning
    """
    if not market_pricing:
        return jsonify({"error": "Market pricing not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ["their_offer", "your_target", "asset", "round_number"]
    missing = [f for f in required_fields if f not in data]

    if missing:
        return jsonify({
            "error": "Missing required fields",
            "missing": missing
        }), 400

    result = market_pricing.generate_counteroffer(
        their_offer=data["their_offer"],
        your_target=data["your_target"],
        asset=data["asset"],
        round_number=data["round_number"],
        max_rounds=data.get("max_rounds", 10)
    )

    return jsonify(result)


@app.route('/market/history/<asset>', methods=['GET'])
def get_price_history(asset: str):
    """
    Get price history with statistics.

    Path params:
        asset: Asset symbol

    Query params:
        hours: Hours of history (default 168 = 7 days)

    Returns:
        Price history with statistics
    """
    if not market_pricing:
        return jsonify({"error": "Market pricing not available"}), 503

    hours = request.args.get("hours", 168, type=int)

    history = market_pricing.get_price_history(asset, hours)

    return jsonify(history)


@app.route('/market/benchmark/<asset>', methods=['GET'])
def get_price_benchmark(asset: str):
    """
    Get price benchmark analysis.

    Path params:
        asset: Asset to benchmark

    Query params:
        days: Benchmark period in days (default 30)

    Returns:
        Benchmark analysis
    """
    if not market_pricing:
        return jsonify({"error": "Market pricing not available"}), 503

    days = request.args.get("days", 30, type=int)

    benchmark = market_pricing.get_price_benchmark(asset, days)

    return jsonify(benchmark)


@app.route('/market/similar-prices', methods=['POST'])
def find_similar_market_prices():
    """
    Find historical periods with similar prices.

    Request body:
    {
        "asset": "BTC",
        "target_price": 42000.0,
        "tolerance": 0.05 (optional, default 5%)
    }

    Returns:
        Historical periods with similar prices
    """
    if not market_pricing:
        return jsonify({"error": "Market pricing not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "asset" not in data or "target_price" not in data:
        return jsonify({
            "error": "Missing required fields",
            "required": ["asset", "target_price"]
        }), 400

    result = market_pricing.find_similar_prices(
        asset=data["asset"],
        target_price=data["target_price"],
        tolerance=data.get("tolerance", 0.05)
    )

    return jsonify(result)


@app.route('/market/asset', methods=['POST'])
def add_custom_market_asset():
    """
    Add a custom asset for pricing.

    Request body:
    {
        "asset": "CUSTOM_TOKEN",
        "price": 100.0,
        "asset_class": "crypto|forex|commodity|equity|service|custom" (optional),
        "currency": "USD" (optional),
        "volatility": 0.02 (optional)
    }

    Returns:
        Confirmation of asset addition
    """
    if not market_pricing:
        return jsonify({"error": "Market pricing not available"}), 503

    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    if "asset" not in data or "price" not in data:
        return jsonify({
            "error": "Missing required fields",
            "required": ["asset", "price"]
        }), 400

    result = market_pricing.add_custom_asset(
        asset=data["asset"],
        price=data["price"],
        asset_class=data.get("asset_class", "custom"),
        currency=data.get("currency", "USD"),
        volatility=data.get("volatility", 0.02)
    )

    return jsonify(result), 201


@app.route('/market/assets', methods=['GET'])
def get_available_market_assets():
    """Get list of available assets."""
    if not market_pricing:
        return jsonify({"error": "Market pricing not available"}), 503

    assets = market_pricing.get_available_assets()

    return jsonify({
        "count": len(assets),
        "assets": assets
    })


@app.route('/market/strategies', methods=['GET'])
def get_pricing_strategies():
    """Get available pricing strategies."""
    return jsonify({
        "strategies": [
            {
                "value": s.value,
                "name": s.name,
                "description": {
                    "market": "Follow current market price",
                    "premium": "Price above market (10% premium)",
                    "discount": "Price below market (10% discount)",
                    "anchored": "Use provided anchor price",
                    "competitive": "Slightly below market for competitiveness",
                    "value_based": "Based on fair value analysis"
                }.get(s.value, "Pricing strategy")
            }
            for s in PricingStrategy
        ]
    })


@app.route('/market/conditions', methods=['GET'])
def get_market_conditions():
    """Get market condition types."""
    return jsonify({
        "conditions": [
            {
                "value": c.value,
                "name": c.name,
                "description": {
                    "bullish": "Strong upward trend",
                    "bearish": "Strong downward trend",
                    "neutral": "Sideways/stable market",
                    "volatile": "High volatility, no clear direction",
                    "trending_up": "Moderate upward movement",
                    "trending_down": "Moderate downward movement"
                }.get(c.value, "Market condition")
            }
            for c in MarketCondition
        ]
    })


@app.route('/market/stats', methods=['GET'])
def get_market_pricing_stats():
    """Get market pricing statistics."""
    if not market_pricing:
        return jsonify({"error": "Market pricing not available"}), 503

    stats = market_pricing.get_statistics()
    return jsonify(stats)


@app.route('/market/audit', methods=['GET'])
def get_market_pricing_audit():
    """
    Get market pricing audit trail.

    Query params:
        limit: Maximum entries (default 100)
    """
    if not market_pricing:
        return jsonify({"error": "Market pricing not available"}), 503

    limit = request.args.get("limit", 100, type=int)

    trail = market_pricing.get_audit_trail(limit=limit)

    return jsonify({
        "count": len(trail),
        "audit_trail": trail
    })


# ============================================================
# Mobile Deployment Endpoints (Plan 17)
# ============================================================

@app.route('/mobile/device/register', methods=['POST'])
def register_device():
    """
    Register a new mobile device.

    Request body:
        device_type: Type of device (ios, android, web, desktop)
        device_name: User-friendly device name
        capabilities: Dict of device capabilities
    """
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    device_type_str = data.get("device_type", "web")
    device_name = data.get("device_name", "Unknown Device")
    capabilities = data.get("capabilities", {})

    try:
        device_type = DeviceType[device_type_str.upper()]
    except KeyError:
        return jsonify({"error": f"Invalid device_type. Valid: {[t.name.lower() for t in DeviceType]}"}), 400

    device_id = mobile_deployment.register_device(
        device_type=device_type,
        device_name=device_name,
        capabilities=capabilities
    )

    return jsonify({
        "device_id": device_id,
        "device_type": device_type_str,
        "device_name": device_name,
        "registered": True
    })


@app.route('/mobile/device/<device_id>', methods=['GET'])
def get_device_info(device_id: str):
    """Get information about a registered device."""
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    device = mobile_deployment.portable.devices.get(device_id)
    if not device:
        return jsonify({"error": "Device not found"}), 404

    return jsonify({
        "device_id": device.device_id,
        "device_type": device.device_type.name.lower(),
        "device_name": device.device_name,
        "capabilities": device.capabilities,
        "registered_at": device.registered_at.isoformat(),
        "last_sync": device.last_sync.isoformat() if device.last_sync else None,
        "is_active": device.is_active,
        "platform_version": device.platform_version
    })


@app.route('/mobile/device/<device_id>/features', methods=['GET'])
def get_device_features(device_id: str):
    """Get feature flags for a specific device."""
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    features = mobile_deployment.get_device_features(device_id)
    if not features:
        return jsonify({"error": "Device not found"}), 404

    return jsonify({
        "device_id": device_id,
        "features": features
    })


@app.route('/mobile/edge/model/load', methods=['POST'])
def load_edge_model():
    """
    Load an AI model for edge inference.

    Request body:
        model_id: Unique identifier for the model
        model_type: Type of model (contract_parser, intent_classifier, etc.)
        model_path: Path to model file
        device_id: Device to load model on
    """
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    model_id = data.get("model_id")
    model_type = data.get("model_type", "generic")
    model_path = data.get("model_path")
    device_id = data.get("device_id")

    if not model_id:
        return jsonify({"error": "model_id required"}), 400

    success = mobile_deployment.load_edge_model(
        model_id=model_id,
        model_type=model_type,
        model_path=model_path,
        device_id=device_id
    )

    return jsonify({
        "model_id": model_id,
        "loaded": success,
        "device_id": device_id
    })


@app.route('/mobile/edge/inference', methods=['POST'])
def run_edge_inference():
    """
    Run inference on a loaded edge model.

    Request body:
        model_id: ID of loaded model
        input_data: Input data for inference
        device_id: Device to run inference on
    """
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    model_id = data.get("model_id")
    input_data = data.get("input_data")
    device_id = data.get("device_id")

    if not model_id or input_data is None:
        return jsonify({"error": "model_id and input_data required"}), 400

    result = mobile_deployment.run_inference(
        model_id=model_id,
        input_data=input_data,
        device_id=device_id
    )

    return jsonify(result)


@app.route('/mobile/edge/models', methods=['GET'])
def list_edge_models():
    """List all loaded edge models."""
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    models = []
    for model_id, config in mobile_deployment.edge_ai.loaded_models.items():
        models.append({
            "model_id": model_id,
            "model_type": config.model_type,
            "is_quantized": config.is_quantized,
            "loaded_at": config.loaded_at.isoformat(),
            "inference_count": config.inference_count
        })

    return jsonify({
        "count": len(models),
        "models": models
    })


@app.route('/mobile/edge/resources', methods=['GET'])
def get_edge_resources():
    """Get current edge AI resource usage."""
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    resources = mobile_deployment.edge_ai.resource_limits
    stats = mobile_deployment.edge_ai.get_statistics()

    return jsonify({
        "limits": {
            "max_memory_mb": resources.max_memory_mb,
            "max_cpu_percent": resources.max_cpu_percent,
            "max_battery_drain_percent": resources.max_battery_drain_percent,
            "prefer_wifi": resources.prefer_wifi
        },
        "current": stats
    })


@app.route('/mobile/wallet/connect', methods=['POST'])
def connect_mobile_wallet():
    """
    Connect a mobile wallet.

    Request body:
        wallet_type: Type of wallet (walletconnect, metamask, coinbase, native, hardware)
        device_id: Device connecting the wallet
        wallet_address: Wallet address (optional for some types)
    """
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    wallet_type_str = data.get("wallet_type", "walletconnect")
    device_id = data.get("device_id")
    wallet_address = data.get("wallet_address")

    try:
        wallet_type = WalletType[wallet_type_str.upper()]
    except KeyError:
        return jsonify({"error": f"Invalid wallet_type. Valid: {[t.name.lower() for t in WalletType]}"}), 400

    connection_id = mobile_deployment.connect_wallet(
        wallet_type=wallet_type,
        device_id=device_id,
        wallet_address=wallet_address
    )

    if not connection_id:
        return jsonify({"error": "Failed to connect wallet"}), 500

    return jsonify({
        "connection_id": connection_id,
        "wallet_type": wallet_type_str,
        "device_id": device_id,
        "connected": True
    })


@app.route('/mobile/wallet/<connection_id>', methods=['GET'])
def get_wallet_connection(connection_id: str):
    """Get wallet connection details."""
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    connection = mobile_deployment.wallet_manager.connections.get(connection_id)
    if not connection:
        return jsonify({"error": "Connection not found"}), 404

    return jsonify({
        "connection_id": connection.connection_id,
        "wallet_type": connection.wallet_type.name.lower(),
        "wallet_address": connection.wallet_address,
        "chain_id": connection.chain_id,
        "state": connection.state.name.lower(),
        "connected_at": connection.connected_at.isoformat() if connection.connected_at else None,
        "device_id": connection.device_id
    })


@app.route('/mobile/wallet/<connection_id>/disconnect', methods=['POST'])
def disconnect_mobile_wallet(connection_id: str):
    """Disconnect a mobile wallet."""
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    success = mobile_deployment.disconnect_wallet(connection_id)

    return jsonify({
        "connection_id": connection_id,
        "disconnected": success
    })


@app.route('/mobile/wallet/<connection_id>/sign', methods=['POST'])
def sign_with_wallet(connection_id: str):
    """
    Sign a message with connected wallet.

    Request body:
        message: Message to sign
        sign_type: Type of signature (personal, typed_data, transaction)
    """
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    message = data.get("message")
    sign_type = data.get("sign_type", "personal")

    if not message:
        return jsonify({"error": "message required"}), 400

    result = mobile_deployment.sign_message(
        connection_id=connection_id,
        message=message,
        sign_type=sign_type
    )

    return jsonify(result)


@app.route('/mobile/wallet/list', methods=['GET'])
def list_wallet_connections():
    """List all wallet connections."""
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    device_id = request.args.get("device_id")

    connections = []
    for conn_id, conn in mobile_deployment.wallet_manager.connections.items():
        if device_id and conn.device_id != device_id:
            continue
        connections.append({
            "connection_id": conn.connection_id,
            "wallet_type": conn.wallet_type.name.lower(),
            "wallet_address": conn.wallet_address,
            "state": conn.state.name.lower(),
            "device_id": conn.device_id
        })

    return jsonify({
        "count": len(connections),
        "connections": connections
    })


@app.route('/mobile/offline/state/save', methods=['POST'])
def save_offline_state():
    """
    Save state for offline access.

    Request body:
        device_id: Device to save state for
        state_type: Type of state (contracts, entries, settings)
        state_data: State data to save
    """
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    device_id = data.get("device_id")
    state_type = data.get("state_type", "general")
    state_data = data.get("state_data", {})

    if not device_id:
        return jsonify({"error": "device_id required"}), 400

    state_id = mobile_deployment.save_offline_state(
        device_id=device_id,
        state_type=state_type,
        state_data=state_data
    )

    return jsonify({
        "state_id": state_id,
        "device_id": device_id,
        "state_type": state_type,
        "saved": True
    })


@app.route('/mobile/offline/state/<device_id>', methods=['GET'])
def get_offline_state(device_id: str):
    """Get offline state for a device."""
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    state_type = request.args.get("state_type")

    state = mobile_deployment.get_offline_state(device_id, state_type)

    return jsonify({
        "device_id": device_id,
        "state": state
    })


@app.route('/mobile/offline/queue/add', methods=['POST'])
def add_to_sync_queue():
    """
    Add an operation to the offline sync queue.

    Request body:
        device_id: Device adding the operation
        operation_type: Type of operation (create, update, delete)
        resource_type: Type of resource (contract, entry, etc.)
        resource_data: Data for the operation
    """
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    device_id = data.get("device_id")
    operation_type = data.get("operation_type")
    resource_type = data.get("resource_type")
    resource_data = data.get("resource_data", {})

    if not device_id or not operation_type or not resource_type:
        return jsonify({"error": "device_id, operation_type, and resource_type required"}), 400

    operation_id = mobile_deployment.queue_offline_operation(
        device_id=device_id,
        operation_type=operation_type,
        resource_type=resource_type,
        resource_data=resource_data
    )

    return jsonify({
        "operation_id": operation_id,
        "device_id": device_id,
        "queued": True
    })


@app.route('/mobile/offline/sync', methods=['POST'])
def sync_offline_data():
    """
    Synchronize offline data with server.

    Request body:
        device_id: Device to sync
        force: Force sync even if conflicts exist
    """
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    device_id = data.get("device_id")
    force = data.get("force", False)

    if not device_id:
        return jsonify({"error": "device_id required"}), 400

    result = mobile_deployment.sync_device(device_id, force=force)

    return jsonify(result)


@app.route('/mobile/offline/queue/<device_id>', methods=['GET'])
def get_sync_queue(device_id: str):
    """Get pending sync operations for a device."""
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    queue = mobile_deployment.get_sync_queue(device_id)

    return jsonify({
        "device_id": device_id,
        "pending_count": len(queue),
        "operations": queue
    })


@app.route('/mobile/offline/conflicts/<device_id>', methods=['GET'])
def get_sync_conflicts(device_id: str):
    """Get sync conflicts for a device."""
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    conflicts = mobile_deployment.get_conflicts(device_id)

    return jsonify({
        "device_id": device_id,
        "conflict_count": len(conflicts),
        "conflicts": conflicts
    })


@app.route('/mobile/offline/conflict/resolve', methods=['POST'])
def resolve_sync_conflict():
    """
    Resolve a sync conflict.

    Request body:
        conflict_id: ID of conflict to resolve
        resolution: Resolution strategy (local, remote, merge)
        merged_data: Merged data if using merge strategy
    """
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body required"}), 400

    conflict_id = data.get("conflict_id")
    resolution = data.get("resolution", "remote")
    merged_data = data.get("merged_data")

    if not conflict_id:
        return jsonify({"error": "conflict_id required"}), 400

    success = mobile_deployment.resolve_conflict(
        conflict_id=conflict_id,
        resolution=resolution,
        merged_data=merged_data
    )

    return jsonify({
        "conflict_id": conflict_id,
        "resolved": success,
        "resolution": resolution
    })


@app.route('/mobile/stats', methods=['GET'])
def get_mobile_stats():
    """Get mobile deployment statistics."""
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    stats = mobile_deployment.get_statistics()

    return jsonify(stats)


@app.route('/mobile/audit', methods=['GET'])
def get_mobile_audit():
    """
    Get mobile deployment audit trail.

    Query params:
        limit: Maximum entries (default 100)
    """
    if not mobile_deployment:
        return jsonify({"error": "Mobile deployment not available"}), 503

    limit = request.args.get("limit", 100, type=int)

    trail = mobile_deployment.get_audit_trail(limit=limit)

    return jsonify({
        "count": len(trail),
        "audit_trail": trail
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
