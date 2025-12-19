"""
FIE Asset Directive Integration Tests
Tests that Finite-Intent-Executor can put assets on NatLangChain blockchain
for execution by designated executors through defined directives.
"""

import sys
import os
import unittest
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from blockchain import NatLangChain, NaturalLanguageEntry


class TestFIEAssetDirectives(unittest.TestCase):
    """Test FIE asset directive recording and executor access."""

    def setUp(self):
        """Set up test fixtures."""
        self.blockchain = NatLangChain()

    def test_record_crypto_wallet_directive(self):
        """Test recording directive for crypto wallet transfer."""
        entry = NaturalLanguageEntry(
            content="Asset Directive: Upon my passing, transfer all cryptocurrency assets "
                    "in wallet 0xMyWallet123 to my daughter Sarah (0xSarahWallet456). "
                    "This includes ETH, BTC, and all ERC-20 tokens. The transfer should "
                    "occur within 30 days of verified death.",
            author="john_doe",
            intent="Posthumous crypto transfer",
            metadata={
                "is_delayed_intent": True,
                "delayed_intent_type": "posthumous",
                "asset_directive": True,
                "assets": [
                    {
                        "asset_type": "crypto_wallet",
                        "wallet_address": "0xMyWallet123",
                        "chain": "ethereum",
                        "includes": ["ETH", "all_erc20"]
                    },
                    {
                        "asset_type": "crypto_wallet",
                        "wallet_address": "bc1qmywallet789",
                        "chain": "bitcoin"
                    }
                ],
                "beneficiary": {
                    "name": "Sarah Doe",
                    "relationship": "daughter",
                    "wallet": "0xSarahWallet456"
                },
                "trigger": {
                    "type": "death",
                    "verification_method": "death_certificate_oracle",
                    "minimum_confirmations": 2
                },
                "executor": {
                    "primary": "finite_intent_executor_mainnet",
                    "authorized_executors": ["fie_node_1", "fie_node_2"]
                },
                "execution_window": {
                    "min_days_after_trigger": 7,
                    "max_days_after_trigger": 30
                },
                "revocation": {
                    "revocable": True,
                    "revocation_method": "author_multisig"
                }
            }
        )
        entry.validation_status = "valid"

        result = self.blockchain.add_entry(entry)
        self.assertEqual(result["status"], "pending")

        block = self.blockchain.mine_pending_entries()
        self.assertIsNotNone(block)

        stored = block.entries[0]
        self.assertTrue(stored.metadata.get("asset_directive"))
        self.assertEqual(len(stored.metadata["assets"]), 2)
        self.assertEqual(stored.metadata["beneficiary"]["name"], "Sarah Doe")

    def test_record_ip_rights_directive(self):
        """Test recording directive for intellectual property transfer."""
        entry = NaturalLanguageEntry(
            content="IP Rights Directive: I hereby direct that upon my death, all intellectual "
                    "property rights to my software projects shall be transferred as follows: "
                    "(1) ProjectAlpha to the Apache Foundation under Apache 2.0 license, "
                    "(2) ProjectBeta to my co-founder Mike under existing partnership terms, "
                    "(3) All remaining projects to public domain. Any registered patents "
                    "shall be dedicated to defensive patent pools.",
            author="inventor_alice",
            intent="Posthumous IP distribution",
            metadata={
                "is_delayed_intent": True,
                "delayed_intent_type": "posthumous",
                "asset_directive": True,
                "assets": [
                    {
                        "asset_type": "intellectual_property",
                        "ip_type": "software",
                        "identifier": "github.com/alice/ProjectAlpha",
                        "transfer_to": "apache_foundation",
                        "license": "Apache-2.0"
                    },
                    {
                        "asset_type": "intellectual_property",
                        "ip_type": "software",
                        "identifier": "github.com/alice/ProjectBeta",
                        "transfer_to": "mike_cofounder",
                        "terms": "existing_partnership_agreement"
                    },
                    {
                        "asset_type": "intellectual_property",
                        "ip_type": "patents",
                        "identifier": "all_registered_patents",
                        "transfer_to": "defensive_patent_pool"
                    }
                ],
                "trigger": {
                    "type": "death",
                    "minimum_confirmations": 2
                },
                "executor": {
                    "primary": "finite_intent_executor_mainnet",
                    "legal_executor": "ip_law_firm_llc"
                }
            }
        )
        entry.validation_status = "valid"

        self.blockchain.add_entry(entry)
        block = self.blockchain.mine_pending_entries()

        stored = block.entries[0]
        self.assertEqual(len(stored.metadata["assets"]), 3)
        self.assertEqual(stored.metadata["assets"][0]["license"], "Apache-2.0")

    def test_record_physical_asset_directive(self):
        """Test recording directive for physical assets with digital proof."""
        entry = NaturalLanguageEntry(
            content="Physical Asset Directive: My art collection, documented in Memory Vault "
                    "reference MV-ART-001, shall be donated to the Metropolitan Museum upon "
                    "my passing. The NFT certificates of authenticity shall be transferred "
                    "to the museum's wallet. Physical transfer shall be coordinated by "
                    "Christie's auction house as designated handler.",
            author="art_collector",
            intent="Posthumous art donation",
            metadata={
                "is_delayed_intent": True,
                "delayed_intent_type": "posthumous",
                "asset_directive": True,
                "assets": [
                    {
                        "asset_type": "physical_with_digital_proof",
                        "category": "art_collection",
                        "vault_reference": "MV-ART-001",
                        "item_count": 47,
                        "appraised_value": {"amount": 2500000, "currency": "USD"},
                        "nft_certificates": ["NFT-ART-001", "NFT-ART-002"],
                        "physical_handler": "christies_auction_house"
                    }
                ],
                "beneficiary": {
                    "name": "Metropolitan Museum of Art",
                    "identifier": "met_museum",
                    "wallet": "0xMetMuseum..."
                },
                "trigger": {
                    "type": "death",
                    "minimum_confirmations": 2
                },
                "executor": {
                    "primary": "finite_intent_executor_mainnet",
                    "physical_coordinator": "christies_auction_house"
                }
            }
        )
        entry.validation_status = "valid"

        self.blockchain.add_entry(entry)
        block = self.blockchain.mine_pending_entries()

        stored = block.entries[0]
        self.assertEqual(stored.metadata["assets"][0]["category"], "art_collection")
        self.assertEqual(stored.metadata["assets"][0]["item_count"], 47)


class TestExecutorAssetAccess(unittest.TestCase):
    """Test that executors can find and access asset directives."""

    def setUp(self):
        """Set up blockchain with multiple asset directives."""
        self.blockchain = NatLangChain()
        self._populate_test_directives()

    def _populate_test_directives(self):
        """Add various asset directives to the blockchain."""
        directives = [
            {
                "author": "user_a",
                "executor": "fie_node_1",
                "asset_type": "crypto",
                "triggered": False
            },
            {
                "author": "user_b",
                "executor": "fie_node_1",
                "asset_type": "ip_rights",
                "triggered": False
            },
            {
                "author": "user_c",
                "executor": "fie_node_2",
                "asset_type": "crypto",
                "triggered": True  # Already triggered
            },
            {
                "author": "user_d",
                "executor": "fie_node_1",
                "asset_type": "physical",
                "triggered": False
            }
        ]

        for d in directives:
            entry = NaturalLanguageEntry(
                content=f"Asset directive from {d['author']} for {d['asset_type']}",
                author=d["author"],
                intent="Asset directive",
                metadata={
                    "is_delayed_intent": True,
                    "asset_directive": True,
                    "asset_type": d["asset_type"],
                    "executor": {"primary": d["executor"]},
                    "triggered": d["triggered"],
                    "trigger": {"type": "death"}
                }
            )
            entry.validation_status = "valid"
            self.blockchain.add_entry(entry)

        self.blockchain.mine_pending_entries()

    def test_executor_query_assigned_directives(self):
        """Test that executor can find all directives assigned to them."""
        executor_id = "fie_node_1"
        assigned_directives = []

        for block in self.blockchain.chain:
            for entry in block.entries:
                if entry.metadata:
                    executor = entry.metadata.get("executor", {})
                    if executor.get("primary") == executor_id:
                        assigned_directives.append({
                            "author": entry.author,
                            "asset_type": entry.metadata.get("asset_type"),
                            "triggered": entry.metadata.get("triggered", False)
                        })

        # fie_node_1 should have 3 directives
        self.assertEqual(len(assigned_directives), 3)

        # Filter untriggered (pending execution)
        pending = [d for d in assigned_directives if not d["triggered"]]
        self.assertEqual(len(pending), 3)

    def test_executor_query_by_asset_type(self):
        """Test querying directives by asset type."""
        crypto_directives = []

        for block in self.blockchain.chain:
            for entry in block.entries:
                if entry.metadata:
                    if entry.metadata.get("asset_type") == "crypto":
                        crypto_directives.append(entry)

        self.assertEqual(len(crypto_directives), 2)

    def test_executor_query_pending_only(self):
        """Test querying only untriggered directives."""
        pending_directives = []

        for block in self.blockchain.chain:
            for entry in block.entries:
                if entry.metadata:
                    if (entry.metadata.get("asset_directive") and
                            not entry.metadata.get("triggered", False)):
                        pending_directives.append(entry)

        self.assertEqual(len(pending_directives), 3)


class TestExecutorRecordsExecution(unittest.TestCase):
    """Test that executors can record execution proofs."""

    def setUp(self):
        """Set up blockchain with a directive ready for execution."""
        self.blockchain = NatLangChain()

        # Record initial directive
        self.directive_entry = NaturalLanguageEntry(
            content="Transfer 10 ETH from 0xSource to 0xBeneficiary upon my death.",
            author="original_owner",
            intent="Posthumous ETH transfer",
            metadata={
                "is_delayed_intent": True,
                "delayed_intent_id": "DI-ETH-001",
                "asset_directive": True,
                "assets": [{
                    "asset_type": "crypto",
                    "amount": 10,
                    "currency": "ETH",
                    "source": "0xSource",
                    "destination": "0xBeneficiary"
                }],
                "trigger": {"type": "death"},
                "executor": {"primary": "fie_mainnet"}
            }
        )
        self.directive_entry.validation_status = "valid"
        self.blockchain.add_entry(self.directive_entry)
        self.blockchain.mine_pending_entries()

    def test_executor_records_trigger_verification(self):
        """Test executor recording trigger verification."""
        verification_entry = NaturalLanguageEntry(
            content="Trigger Verification for DI-ETH-001: Death of original_owner verified "
                    "through Social Security Death Index (SSDI-12345) and legal executor "
                    "declaration from Law Firm XYZ. Two independent confirmations received.",
            author="fie_mainnet",
            intent="Record trigger verification",
            metadata={
                "is_trigger_verification": True,
                "delayed_intent_ref": "DI-ETH-001",
                "verification_id": "VERIFY-ETH-001",
                "trigger_type": "death",
                "evidence": [
                    {
                        "source": "social_security_death_index",
                        "record_id": "SSDI-12345",
                        "verified": True
                    },
                    {
                        "source": "legal_executor_declaration",
                        "executor": "law_firm_xyz",
                        "notarized": True
                    }
                ],
                "confirmations": 2,
                "verification_timestamp": datetime.utcnow().isoformat()
            }
        )
        verification_entry.validation_status = "valid"

        self.blockchain.add_entry(verification_entry)
        block = self.blockchain.mine_pending_entries()

        stored = block.entries[0]
        self.assertTrue(stored.metadata.get("is_trigger_verification"))
        self.assertEqual(stored.metadata["confirmations"], 2)

    def test_executor_records_execution_proof(self):
        """Test executor recording execution proof."""
        execution_entry = NaturalLanguageEntry(
            content="Execution Record for DI-ETH-001: On 2035-06-20, following verified death "
                    "of original_owner, 10 ETH was transferred from 0xSource to 0xBeneficiary. "
                    "Transaction hash: 0xTxHash123. Execution performed by fie_mainnet in "
                    "accordance with original directive.",
            author="fie_mainnet",
            intent="Record execution proof",
            metadata={
                "is_execution_record": True,
                "delayed_intent_ref": "DI-ETH-001",
                "execution_id": "EXEC-ETH-001",
                "verification_ref": "VERIFY-ETH-001",
                "actions_completed": [
                    {
                        "action": "crypto_transfer",
                        "asset": "ETH",
                        "amount": 10,
                        "from": "0xSource",
                        "to": "0xBeneficiary",
                        "tx_hash": "0xTxHash123",
                        "status": "confirmed",
                        "block_number": 18500000
                    }
                ],
                "execution_timestamp": "2035-06-20T10:00:00Z",
                "executor_node": "fie_mainnet",
                "legal_certificate_hash": "SHA256:LegalCert..."
            }
        )
        execution_entry.validation_status = "valid"

        self.blockchain.add_entry(execution_entry)
        block = self.blockchain.mine_pending_entries()

        stored = block.entries[0]
        self.assertTrue(stored.metadata.get("is_execution_record"))
        self.assertEqual(stored.metadata["execution_id"], "EXEC-ETH-001")
        self.assertEqual(stored.metadata["actions_completed"][0]["status"], "confirmed")


class TestMultiAssetDirective(unittest.TestCase):
    """Test complex multi-asset directives."""

    def setUp(self):
        """Set up blockchain."""
        self.blockchain = NatLangChain()

    def test_estate_distribution_directive(self):
        """Test comprehensive estate distribution directive."""
        entry = NaturalLanguageEntry(
            content="Complete Estate Distribution Directive: Upon my death, distribute my "
                    "digital estate as follows: "
                    "(1) Crypto assets: 50% to spouse, 25% each to children. "
                    "(2) NFT collection: All to spouse. "
                    "(3) Software IP: Open source under MIT. "
                    "(4) Digital photos: Family shared vault. "
                    "(5) Social media: Memorial mode. "
                    "Executor shall complete within 60 days.",
            author="estate_owner",
            intent="Complete estate distribution",
            metadata={
                "is_delayed_intent": True,
                "delayed_intent_id": "DI-ESTATE-001",
                "asset_directive": True,
                "estate_plan": True,
                "assets": [
                    {
                        "category": "cryptocurrency",
                        "distribution": [
                            {"beneficiary": "spouse", "percentage": 50},
                            {"beneficiary": "child_1", "percentage": 25},
                            {"beneficiary": "child_2", "percentage": 25}
                        ],
                        "wallets": ["0xMainWallet", "0xTradingWallet"]
                    },
                    {
                        "category": "nft_collection",
                        "vault_ref": "MV-NFT-001",
                        "distribution": [{"beneficiary": "spouse", "percentage": 100}]
                    },
                    {
                        "category": "software_ip",
                        "repos": ["github.com/owner/*"],
                        "action": "open_source",
                        "license": "MIT"
                    },
                    {
                        "category": "digital_media",
                        "type": "photos",
                        "vault_ref": "MV-PHOTOS-001",
                        "action": "transfer_to_family_vault"
                    },
                    {
                        "category": "social_accounts",
                        "platforms": ["twitter", "linkedin", "facebook"],
                        "action": "memorial_mode"
                    }
                ],
                "trigger": {
                    "type": "death",
                    "minimum_confirmations": 3
                },
                "executor": {
                    "primary": "fie_mainnet",
                    "backup": "fie_backup",
                    "legal_executor": "estate_attorney_llc"
                },
                "execution_deadline_days": 60,
                "witnesses": [
                    {"name": "witness_1", "signature": "sig1"},
                    {"name": "witness_2", "signature": "sig2"}
                ]
            }
        )
        entry.validation_status = "valid"

        self.blockchain.add_entry(entry)
        block = self.blockchain.mine_pending_entries()

        stored = block.entries[0]
        self.assertTrue(stored.metadata.get("estate_plan"))
        self.assertEqual(len(stored.metadata["assets"]), 5)

        # Verify crypto distribution adds up to 100%
        crypto_asset = stored.metadata["assets"][0]
        total_pct = sum(d["percentage"] for d in crypto_asset["distribution"])
        self.assertEqual(total_pct, 100)


class TestConditionalAssetDirectives(unittest.TestCase):
    """Test conditional asset directives with specific trigger conditions."""

    def setUp(self):
        """Set up blockchain."""
        self.blockchain = NatLangChain()

    def test_incapacity_directive(self):
        """Test directive triggered by incapacity declaration."""
        entry = NaturalLanguageEntry(
            content="Incapacity Directive: If I am declared mentally incapacitated by "
                    "two licensed physicians, transfer control of my crypto assets to "
                    "my designated power of attorney (spouse). This is not a full transfer "
                    "but grants management rights until recovery or death.",
            author="prudent_owner",
            intent="Incapacity asset management",
            metadata={
                "is_delayed_intent": True,
                "delayed_intent_type": "incapacity",
                "asset_directive": True,
                "assets": [{
                    "asset_type": "crypto_management_rights",
                    "wallets": ["0xAllWallets"],
                    "rights_granted": ["view", "transfer", "stake"],
                    "rights_withheld": ["close_accounts"]
                }],
                "trigger": {
                    "type": "incapacity",
                    "verification_method": "medical_declaration",
                    "required_physicians": 2,
                    "reversible": True
                },
                "beneficiary": {
                    "name": "Spouse",
                    "role": "power_of_attorney",
                    "wallet": "0xSpouseWallet"
                },
                "executor": {"primary": "fie_mainnet"}
            }
        )
        entry.validation_status = "valid"

        self.blockchain.add_entry(entry)
        block = self.blockchain.mine_pending_entries()

        stored = block.entries[0]
        self.assertEqual(stored.metadata["delayed_intent_type"], "incapacity")
        self.assertTrue(stored.metadata["trigger"]["reversible"])

    def test_time_locked_directive(self):
        """Test time-locked asset release directive."""
        release_date = (datetime.utcnow() + timedelta(days=365*5)).isoformat()

        entry = NaturalLanguageEntry(
            content="Time-Locked Release: On my child's 25th birthday (2030-03-15), "
                    "release the trust fund of 100 ETH to their wallet. Until then, "
                    "the assets remain locked and cannot be accessed by anyone.",
            author="parent",
            intent="Time-locked trust release",
            metadata={
                "is_delayed_intent": True,
                "delayed_intent_type": "time_delayed",
                "asset_directive": True,
                "assets": [{
                    "asset_type": "crypto",
                    "amount": 100,
                    "currency": "ETH",
                    "locked_in": "trust_contract_0x123"
                }],
                "trigger": {
                    "type": "datetime",
                    "trigger_at": "2030-03-15T00:00:00Z",
                    "timezone": "UTC"
                },
                "beneficiary": {
                    "name": "Child",
                    "wallet": "0xChildWallet"
                },
                "executor": {"primary": "fie_mainnet"},
                "revocation": {
                    "revocable": True,
                    "revocation_deadline": "2030-03-14T23:59:59Z"
                }
            }
        )
        entry.validation_status = "valid"

        self.blockchain.add_entry(entry)
        block = self.blockchain.mine_pending_entries()

        stored = block.entries[0]
        self.assertEqual(stored.metadata["delayed_intent_type"], "time_delayed")
        self.assertEqual(stored.metadata["trigger"]["trigger_at"], "2030-03-15T00:00:00Z")


class TestFullFIEWorkflow(unittest.TestCase):
    """Test complete FIE workflow from directive to execution."""

    def setUp(self):
        """Set up blockchain."""
        self.blockchain = NatLangChain()

    def test_complete_asset_directive_workflow(self):
        """Test full workflow: directive → trigger → execution → proof."""
        print("\n" + "="*60)
        print("FIE ASSET DIRECTIVE WORKFLOW TEST")
        print("="*60)

        # Step 1: Owner records asset directive
        print("\n[STEP 1] Owner records asset directive...")
        directive = NaturalLanguageEntry(
            content="I direct that upon my death, my crypto portfolio (approx 50 ETH, "
                    "10000 USDC) be liquidated and distributed: 70% to spouse, "
                    "15% each to two children. Executor: FIE Mainnet.",
            author="crypto_holder",
            intent="Posthumous crypto distribution",
            metadata={
                "is_delayed_intent": True,
                "delayed_intent_id": "DI-CRYPTO-999",
                "asset_directive": True,
                "assets": [
                    {"currency": "ETH", "amount": 50},
                    {"currency": "USDC", "amount": 10000}
                ],
                "distribution": [
                    {"beneficiary": "spouse", "percentage": 70},
                    {"beneficiary": "child_1", "percentage": 15},
                    {"beneficiary": "child_2", "percentage": 15}
                ],
                "trigger": {"type": "death", "minimum_confirmations": 2},
                "executor": {"primary": "fie_mainnet"}
            }
        )
        directive.validation_status = "valid"
        self.blockchain.add_entry(directive)
        block1 = self.blockchain.mine_pending_entries()
        directive_block = block1.index
        print(f"   ✓ Directive recorded on block {directive_block}")

        # Step 2: Years later, trigger occurs - executor verifies
        print("\n[STEP 2] Trigger verification by executor...")
        verification = NaturalLanguageEntry(
            content="Death verification for crypto_holder confirmed via SSDI and "
                    "legal executor declaration. Ready for execution.",
            author="fie_mainnet",
            intent="Verify death trigger",
            metadata={
                "is_trigger_verification": True,
                "delayed_intent_ref": "DI-CRYPTO-999",
                "original_block": directive_block,
                "verification_id": "VER-999",
                "confirmations": 2,
                "verified_at": datetime.utcnow().isoformat()
            }
        )
        verification.validation_status = "valid"
        self.blockchain.add_entry(verification)
        block2 = self.blockchain.mine_pending_entries()
        print(f"   ✓ Trigger verified on block {block2.index}")

        # Step 3: Executor performs asset distribution
        print("\n[STEP 3] Executor records execution...")
        execution = NaturalLanguageEntry(
            content="Execution complete for DI-CRYPTO-999. Assets distributed: "
                    "35 ETH + 7000 USDC to spouse, 7.5 ETH + 1500 USDC to each child. "
                    "All transactions confirmed on Ethereum mainnet.",
            author="fie_mainnet",
            intent="Record execution",
            metadata={
                "is_execution_record": True,
                "delayed_intent_ref": "DI-CRYPTO-999",
                "verification_ref": "VER-999",
                "execution_id": "EXEC-999",
                "transactions": [
                    {"to": "spouse", "eth": 35, "usdc": 7000, "tx": "0xTx1"},
                    {"to": "child_1", "eth": 7.5, "usdc": 1500, "tx": "0xTx2"},
                    {"to": "child_2", "eth": 7.5, "usdc": 1500, "tx": "0xTx3"}
                ],
                "executed_at": datetime.utcnow().isoformat(),
                "all_actions_complete": True
            }
        )
        execution.validation_status = "valid"
        self.blockchain.add_entry(execution)
        block3 = self.blockchain.mine_pending_entries()
        print(f"   ✓ Execution recorded on block {block3.index}")

        # Step 4: Verify chain integrity
        print("\n[STEP 4] Verifying blockchain integrity...")
        is_valid = self.blockchain.validate_chain()
        print(f"   ✓ Chain valid: {is_valid}")

        # Step 5: Query execution history
        print("\n[STEP 5] Querying execution history...")
        execution_records = []
        for block in self.blockchain.chain:
            for entry in block.entries:
                if entry.metadata and entry.metadata.get("is_execution_record"):
                    execution_records.append(entry)

        print(f"   ✓ Found {len(execution_records)} execution record(s)")

        # Assertions
        self.assertTrue(is_valid)
        self.assertEqual(len(execution_records), 1)
        self.assertTrue(execution_records[0].metadata["all_actions_complete"])

        print("\n" + "="*60)
        print("WORKFLOW TEST COMPLETE ✓")
        print("="*60 + "\n")


def run_fie_asset_tests():
    """Run all FIE asset directive tests with verbose output."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFIEAssetDirectives))
    suite.addTests(loader.loadTestsFromTestCase(TestExecutorAssetAccess))
    suite.addTests(loader.loadTestsFromTestCase(TestExecutorRecordsExecution))
    suite.addTests(loader.loadTestsFromTestCase(TestMultiAssetDirective))
    suite.addTests(loader.loadTestsFromTestCase(TestConditionalAssetDirectives))
    suite.addTests(loader.loadTestsFromTestCase(TestFullFIEWorkflow))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result


if __name__ == "__main__":
    run_fie_asset_tests()
