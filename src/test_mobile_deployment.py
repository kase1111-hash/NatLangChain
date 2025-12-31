"""
End-to-end tests for Mobile Deployment module (Plan 17)
Runs 10 comprehensive simulations covering all features
"""

import sys
import traceback
from datetime import datetime

from mobile_deployment import (
    ConnectionState,
    DeviceType,
    MobileDeploymentManager,
    WalletType,
)


class SimulationResult:
    def __init__(self, name: str):
        self.name = name
        self.passed = False
        self.error = None
        self.details = []

    def log(self, msg: str):
        self.details.append(msg)
        print(f"    {msg}")

    def success(self):
        self.passed = True
        print(f"  ✓ {self.name} PASSED")

    def fail(self, error: str):
        self.passed = False
        self.error = error
        print(f"  ✗ {self.name} FAILED: {error}")


def simulation_1_device_registration():
    """Simulation 1: Complete device registration flow for all device types"""
    result = SimulationResult("Device Registration Flow")

    try:
        manager = MobileDeploymentManager()
        result.log("Created MobileDeploymentManager")

        # Register each device type
        devices = {}
        for device_type in DeviceType:
            device_id = manager.register_device(
                device_type=device_type,
                device_name=f"Test {device_type.name} Device",
                capabilities={"camera": True, "biometric": device_type != DeviceType.WEB}
            )
            devices[device_type] = device_id
            result.log(f"Registered {device_type.name}: {device_id[:8]}...")

        # Verify all devices exist (5 device types: IOS, ANDROID, WEB, DESKTOP, EMBEDDED)
        assert len(manager.portable.devices) == 5, "Should have 5 devices"

        # Get features for each device
        for device_type, device_id in devices.items():
            features = manager.get_device_features(device_id)
            assert features is not None, f"Features should exist for {device_type.name}"
            result.log(f"Features for {device_type.name}: edge_ai={features.get('edge_ai_enabled')}")

        # Check statistics
        stats = manager.get_statistics()
        assert stats["devices"]["total"] == 5, f"Expected 5 devices, got {stats['devices']['total']}"
        result.log(f"Total devices registered: {stats['devices']['total']}")

        result.success()
    except Exception as e:
        result.fail(str(e))
        traceback.print_exc()

    return result


def simulation_2_edge_ai_inference():
    """Simulation 2: Edge AI model loading and inference"""
    result = SimulationResult("Edge AI Inference Pipeline")

    try:
        manager = MobileDeploymentManager()

        # Register a device
        device_id = manager.register_device(
            device_type=DeviceType.IOS,
            device_name="iPhone 15 Pro",
            capabilities={"neural_engine": True, "memory_gb": 8}
        )
        result.log(f"Registered iOS device: {device_id[:8]}...")

        # Load multiple models
        models = [
            ("contract_parser_v1", "contract_parser"),
            ("intent_classifier_v1", "intent_classifier"),
            ("sentiment_analyzer_v1", "sentiment")
        ]

        for model_id, model_type in models:
            success = manager.load_edge_model(
                model_id=model_id,
                model_type=model_type,
                model_path=f"/models/{model_id}.onnx",
                device_id=device_id
            )
            assert success, f"Failed to load model {model_id}"
            result.log(f"Loaded model: {model_id}")

        # Run inferences
        test_inputs = [
            ("contract_parser_v1", "I offer $5000 for web development services"),
            ("intent_classifier_v1", "Looking to hire a contractor"),
            ("sentiment_analyzer_v1", "This is an excellent proposal")
        ]

        for model_id, input_text in test_inputs:
            inference_result = manager.run_inference(
                model_id=model_id,
                input_data={"text": input_text},
                device_id=device_id
            )
            assert inference_result["success"], f"Inference failed for {model_id}"
            result.log(f"Inference {model_id}: confidence={inference_result['result']['confidence']:.2f}")

        # Check model statistics
        edge_stats = manager.edge_ai.get_statistics()
        assert edge_stats["models_loaded"] == 3
        assert edge_stats["total_inferences"] == 3
        result.log(f"Total inferences: {edge_stats['total_inferences']}")

        result.success()
    except Exception as e:
        result.fail(str(e))
        traceback.print_exc()

    return result


def simulation_3_wallet_connection():
    """Simulation 3: Mobile wallet connection and signing"""
    result = SimulationResult("Wallet Connection & Signing")

    try:
        manager = MobileDeploymentManager()

        # Register device
        device_id = manager.register_device(
            device_type=DeviceType.ANDROID,
            device_name="Pixel 8",
            capabilities={"secure_enclave": True}
        )
        result.log(f"Registered Android device: {device_id[:8]}...")

        # Connect different wallet types
        wallet_connections = {}
        wallet_configs = [
            (WalletType.WALLETCONNECT, "0x1234567890abcdef1234567890abcdef12345678"),
            (WalletType.METAMASK, "0xabcdef1234567890abcdef1234567890abcdef12"),
            (WalletType.NATIVE, "0x9876543210fedcba9876543210fedcba98765432")
        ]

        for wallet_type, address in wallet_configs:
            conn_id = manager.connect_wallet(
                wallet_type=wallet_type,
                device_id=device_id,
                wallet_address=address
            )
            assert conn_id, f"Failed to connect {wallet_type.name}"
            wallet_connections[wallet_type] = conn_id
            result.log(f"Connected {wallet_type.name}: {conn_id[:8]}...")

        # Sign messages with each wallet
        for wallet_type, conn_id in wallet_connections.items():
            sign_result = manager.sign_message(
                connection_id=conn_id,
                message="I agree to the contract terms",
                sign_type="personal"
            )
            assert sign_result["success"], f"Signing failed for {wallet_type.name}"
            result.log(f"Signed with {wallet_type.name}: {sign_result['signature'][:16]}...")

        # Disconnect one wallet
        disconnected = manager.disconnect_wallet(wallet_connections[WalletType.METAMASK])
        assert disconnected, "Failed to disconnect wallet"
        result.log("Disconnected MetaMask wallet")

        # Verify connection state
        conn = manager.wallet_manager.connections[wallet_connections[WalletType.METAMASK]]
        assert conn.state == ConnectionState.DISCONNECTED
        result.log("Verified disconnection state")

        result.success()
    except Exception as e:
        result.fail(str(e))
        traceback.print_exc()

    return result


def simulation_4_offline_state_management():
    """Simulation 4: Offline state saving and retrieval"""
    result = SimulationResult("Offline State Management")

    try:
        manager = MobileDeploymentManager()

        # Register device
        device_id = manager.register_device(
            device_type=DeviceType.IOS,
            device_name="iPad Pro",
            capabilities={"storage_gb": 256}
        )
        result.log(f"Registered device: {device_id[:8]}...")

        # Save different state types
        state_types = [
            ("contracts", {"active_contracts": ["c1", "c2"], "draft_contracts": ["d1"]}),
            ("entries", {"pending_entries": 5, "synced_entries": 100}),
            ("settings", {"theme": "dark", "notifications": True, "language": "en"}),
            ("cache", {"last_block": 12345, "cached_at": datetime.now().isoformat()})
        ]

        state_ids = {}
        for state_type, state_data in state_types:
            state_id = manager.save_offline_state(
                device_id=device_id,
                state_type=state_type,
                state_data=state_data
            )
            state_ids[state_type] = state_id
            result.log(f"Saved {state_type} state: {state_id[:8]}...")

        # Retrieve states
        for state_type, original_data in state_types:
            retrieved = manager.get_offline_state(device_id, state_type)
            assert retrieved is not None, f"Failed to retrieve {state_type}"
            assert retrieved["data"] == original_data, f"Data mismatch for {state_type}"
            result.log(f"Retrieved {state_type} state successfully")

        # Get all states
        all_states = manager.get_offline_state(device_id, None)
        assert len(all_states) == 4, "Should have 4 state types"
        result.log(f"Total state types: {len(all_states)}")

        result.success()
    except Exception as e:
        result.fail(str(e))
        traceback.print_exc()

    return result


def simulation_5_offline_sync_queue():
    """Simulation 5: Offline operation queue and sync"""
    result = SimulationResult("Offline Sync Queue")

    try:
        manager = MobileDeploymentManager()

        # Register device
        device_id = manager.register_device(
            device_type=DeviceType.ANDROID,
            device_name="Samsung S24",
            capabilities={}
        )
        result.log(f"Registered device: {device_id[:8]}...")

        # Queue offline operations
        operations = [
            ("create", "contract", {"title": "New Contract", "amount": 5000}),
            ("update", "entry", {"entry_id": "e1", "content": "Updated content"}),
            ("create", "proposal", {"match_id": "m1", "terms": {"price": 1000}}),
            ("delete", "draft", {"draft_id": "d1"}),
            ("update", "settings", {"key": "notification", "value": True})
        ]

        op_ids = []
        for op_type, resource_type, data in operations:
            op_id = manager.queue_offline_operation(
                device_id=device_id,
                operation_type=op_type,
                resource_type=resource_type,
                resource_data=data
            )
            op_ids.append(op_id)
            result.log(f"Queued {op_type} {resource_type}: {op_id[:8]}...")

        # Check queue
        queue = manager.get_sync_queue(device_id)
        assert len(queue) == 5, f"Queue should have 5 items, has {len(queue)}"
        result.log(f"Queue size: {len(queue)}")

        # Sync device
        sync_result = manager.sync_device(device_id, force=False)
        assert sync_result["success"], "Sync should succeed"
        result.log(f"Synced {sync_result['synced_count']} operations")

        # Verify queue is empty after sync
        queue_after = manager.get_sync_queue(device_id)
        assert len(queue_after) == 0, "Queue should be empty after sync"
        result.log("Queue cleared after sync")

        result.success()
    except Exception as e:
        result.fail(str(e))
        traceback.print_exc()

    return result


def simulation_6_conflict_resolution():
    """Simulation 6: Sync conflict detection and resolution"""
    result = SimulationResult("Conflict Detection & Resolution")

    try:
        manager = MobileDeploymentManager()

        # Register device
        device_id = manager.register_device(
            device_type=DeviceType.WEB,
            device_name="Chrome Browser",
            capabilities={}
        )
        result.log(f"Registered device: {device_id[:8]}...")

        # Create some conflicts manually
        import uuid

        from mobile_deployment import SyncConflict

        conflicts = []
        for i in range(3):
            conflict = SyncConflict(
                conflict_id=str(uuid.uuid4()),
                resource_type=f"resource_{i}",
                resource_id=f"res_{i}",
                local_data={"value": f"local_{i}", "version": 1},
                remote_data={"value": f"remote_{i}", "version": 2},
                conflict_type="version_mismatch",
                detected_at=datetime.now()
            )
            manager.offline_manager.conflicts[device_id] = manager.offline_manager.conflicts.get(device_id, [])
            manager.offline_manager.conflicts[device_id].append(conflict)
            conflicts.append(conflict)
            result.log(f"Created conflict: {conflict.conflict_id[:8]}...")

        # Get conflicts
        retrieved_conflicts = manager.get_conflicts(device_id)
        assert len(retrieved_conflicts) == 3, "Should have 3 conflicts"
        result.log(f"Retrieved {len(retrieved_conflicts)} conflicts")

        # Resolve conflicts with different strategies
        resolutions = ["local", "remote", "merge"]
        for i, conflict in enumerate(conflicts):
            merged_data = {"value": f"merged_{i}", "version": 3} if resolutions[i] == "merge" else None
            success = manager.resolve_conflict(
                conflict_id=conflict.conflict_id,
                resolution=resolutions[i],
                merged_data=merged_data
            )
            assert success, f"Failed to resolve conflict with {resolutions[i]}"
            result.log(f"Resolved conflict with {resolutions[i]} strategy")

        # Verify conflicts resolved
        remaining = manager.get_conflicts(device_id)
        assert len(remaining) == 0, "All conflicts should be resolved"
        result.log("All conflicts resolved")

        result.success()
    except Exception as e:
        result.fail(str(e))
        traceback.print_exc()

    return result


def simulation_7_multi_device_sync():
    """Simulation 7: Multi-device synchronization scenario"""
    result = SimulationResult("Multi-Device Synchronization")

    try:
        manager = MobileDeploymentManager()

        # Register multiple devices for same "user"
        devices = {}
        device_configs = [
            (DeviceType.IOS, "iPhone"),
            (DeviceType.ANDROID, "Android Tablet"),
            (DeviceType.WEB, "Desktop Browser"),
            (DeviceType.DESKTOP, "MacBook")
        ]

        for device_type, name in device_configs:
            device_id = manager.register_device(
                device_type=device_type,
                device_name=name,
                capabilities={}
            )
            devices[name] = device_id
            result.log(f"Registered {name}: {device_id[:8]}...")

        # Queue operations on different devices
        for name, device_id in devices.items():
            manager.queue_offline_operation(
                device_id=device_id,
                operation_type="create",
                resource_type="note",
                resource_data={"content": f"Note from {name}", "timestamp": datetime.now().isoformat()}
            )
            result.log(f"Queued operation on {name}")

        # Sync all devices
        sync_results = {}
        for name, device_id in devices.items():
            sync_result = manager.sync_device(device_id)
            sync_results[name] = sync_result
            result.log(f"Synced {name}: success={sync_result['success']}")

        # All should succeed
        assert all(r["success"] for r in sync_results.values()), "All syncs should succeed"

        # Check audit trail
        audit = manager.get_audit_trail(limit=20)
        assert len(audit) >= 8, "Should have at least 8 audit entries (4 registers + 4 syncs)"
        result.log(f"Audit trail entries: {len(audit)}")

        result.success()
    except Exception as e:
        result.fail(str(e))
        traceback.print_exc()

    return result


def simulation_8_hardware_wallet():
    """Simulation 8: Hardware wallet integration"""
    result = SimulationResult("Hardware Wallet Integration")

    try:
        manager = MobileDeploymentManager()

        # Register device
        device_id = manager.register_device(
            device_type=DeviceType.DESKTOP,
            device_name="Linux Desktop",
            capabilities={"usb": True, "bluetooth": True}
        )
        result.log(f"Registered device: {device_id[:8]}...")

        # Connect hardware wallet
        hw_conn_id = manager.connect_wallet(
            wallet_type=WalletType.HARDWARE,
            device_id=device_id,
            wallet_address="0xhardware1234567890abcdef1234567890abcdef"
        )
        assert hw_conn_id, "Failed to connect hardware wallet"
        result.log(f"Connected hardware wallet: {hw_conn_id[:8]}...")

        # Check connection state
        conn = manager.wallet_manager.connections[hw_conn_id]
        assert conn.state == ConnectionState.CONNECTED
        assert conn.wallet_type == WalletType.HARDWARE
        result.log("Verified hardware wallet connection")

        # Sign different message types
        sign_types = ["personal", "typed_data", "transaction"]
        for sign_type in sign_types:
            sign_result = manager.sign_message(
                connection_id=hw_conn_id,
                message=f"Test {sign_type} message",
                sign_type=sign_type
            )
            assert sign_result["success"], f"Failed to sign {sign_type}"
            result.log(f"Signed {sign_type}: {sign_result['signature'][:16]}...")

        # Verify signature count
        assert conn.signature_count == 3, "Should have 3 signatures"
        result.log(f"Total signatures: {conn.signature_count}")

        result.success()
    except Exception as e:
        result.fail(str(e))
        traceback.print_exc()

    return result


def simulation_9_resource_management():
    """Simulation 9: Edge AI resource management and limits"""
    result = SimulationResult("Edge AI Resource Management")

    try:
        manager = MobileDeploymentManager()

        # Register resource-constrained device
        device_id = manager.register_device(
            device_type=DeviceType.ANDROID,
            device_name="Budget Phone",
            capabilities={"memory_gb": 2, "cpu_cores": 4}
        )
        result.log(f"Registered device: {device_id[:8]}...")

        # Check default resource limits
        limits = manager.edge_ai.resource_limits
        result.log(f"Memory limit: {limits.max_memory_mb}MB")
        result.log(f"CPU limit: {limits.max_cpu_percent}%")
        result.log(f"Battery drain limit: {limits.max_battery_drain_percent}%")

        # Load model and run multiple inferences to test resource tracking
        manager.load_edge_model(
            model_id="test_model",
            model_type="classifier",
            model_path="/models/test.onnx",
            device_id=device_id
        )
        result.log("Loaded test model")

        # Run 10 inferences
        for i in range(10):
            manager.run_inference(
                model_id="test_model",
                input_data={"iteration": i},
                device_id=device_id
            )
        result.log("Completed 10 inferences")

        # Check statistics
        stats = manager.edge_ai.get_statistics()
        assert stats["total_inferences"] == 10
        assert stats["models_loaded"] == 1
        result.log(f"Stats: {stats['total_inferences']} inferences, {stats['models_loaded']} models")

        # Check model inference count
        model = manager.edge_ai.loaded_models["test_model"]
        assert model.inference_count == 10
        result.log(f"Model inference count: {model.inference_count}")

        result.success()
    except Exception as e:
        result.fail(str(e))
        traceback.print_exc()

    return result


def simulation_10_full_workflow():
    """Simulation 10: Complete end-to-end workflow"""
    result = SimulationResult("Full End-to-End Workflow")

    try:
        manager = MobileDeploymentManager()
        result.log("=== Starting Complete Workflow ===")

        # Step 1: Register device
        device_id = manager.register_device(
            device_type=DeviceType.IOS,
            device_name="iPhone 15 Pro Max",
            capabilities={"neural_engine": True, "face_id": True, "memory_gb": 8}
        )
        result.log(f"1. Registered device: {device_id[:8]}...")

        # Step 2: Load AI models
        models = ["contract_parser", "intent_classifier"]
        for model in models:
            manager.load_edge_model(
                model_id=model,
                model_type=model,
                model_path=f"/models/{model}.onnx",
                device_id=device_id
            )
        result.log(f"2. Loaded {len(models)} AI models")

        # Step 3: Connect wallet
        wallet_id = manager.connect_wallet(
            wallet_type=WalletType.WALLETCONNECT,
            device_id=device_id,
            wallet_address="0xuser1234567890abcdef1234567890abcdef1234"
        )
        result.log(f"3. Connected wallet: {wallet_id[:8]}...")

        # Step 4: Save offline state
        manager.save_offline_state(
            device_id=device_id,
            state_type="session",
            state_data={"wallet_connected": True, "models_loaded": models}
        )
        result.log("4. Saved offline state")

        # Step 5: Run inference on contract text
        contract_text = "I offer $10,000 for building a mobile app within 3 months"
        inference_result = manager.run_inference(
            model_id="contract_parser",
            input_data={"text": contract_text},
            device_id=device_id
        )
        result.log(f"5. Parsed contract: confidence={inference_result['result']['confidence']:.2f}")

        # Step 6: Queue contract creation for sync
        manager.queue_offline_operation(
            device_id=device_id,
            operation_type="create",
            resource_type="contract",
            resource_data={
                "content": contract_text,
                "parsed": inference_result["result"],
                "wallet": wallet_id
            }
        )
        result.log("6. Queued contract creation")

        # Step 7: Sign the contract
        sign_result = manager.sign_message(
            connection_id=wallet_id,
            message=f"I sign this contract: {contract_text[:50]}...",
            sign_type="typed_data"
        )
        result.log(f"7. Signed contract: {sign_result['signature'][:16]}...")

        # Step 8: Queue signature for sync
        manager.queue_offline_operation(
            device_id=device_id,
            operation_type="update",
            resource_type="contract",
            resource_data={
                "signature": sign_result["signature"],
                "signed_at": datetime.now().isoformat()
            }
        )
        result.log("8. Queued signature update")

        # Step 9: Sync all pending operations
        sync_result = manager.sync_device(device_id)
        result.log(f"9. Synced {sync_result['synced_count']} operations")

        # Step 10: Verify final state
        stats = manager.get_statistics()
        result.log("10. Final Statistics:")
        result.log(f"    - Devices: {stats['devices']['total']}")
        result.log(f"    - Models: {stats['edge_ai']['models_loaded']}")
        result.log(f"    - Inferences: {stats['edge_ai']['total_inferences']}")
        result.log(f"    - Wallet connections: {stats['wallets']['total_connections']}")
        result.log(f"    - Operations synced: {stats['offline']['operations_synced']}")

        # Verify audit trail
        audit = manager.get_audit_trail(limit=10)
        result.log(f"    - Audit entries: {len(audit)}")

        result.success()
    except Exception as e:
        result.fail(str(e))
        traceback.print_exc()

    return result


def run_all_simulations():
    """Run all 10 end-to-end simulations"""
    print("\n" + "=" * 60)
    print("Mobile Deployment - End-to-End Simulations")
    print("=" * 60 + "\n")

    simulations = [
        simulation_1_device_registration,
        simulation_2_edge_ai_inference,
        simulation_3_wallet_connection,
        simulation_4_offline_state_management,
        simulation_5_offline_sync_queue,
        simulation_6_conflict_resolution,
        simulation_7_multi_device_sync,
        simulation_8_hardware_wallet,
        simulation_9_resource_management,
        simulation_10_full_workflow
    ]

    results = []
    for i, sim in enumerate(simulations, 1):
        print(f"\n[Simulation {i}/10] {sim.__doc__.strip()}")
        print("-" * 50)
        result = sim()
        results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("SIMULATION SUMMARY")
    print("=" * 60)

    passed = sum(1 for r in results if r.passed)
    failed = sum(1 for r in results if not r.passed)

    for i, result in enumerate(results, 1):
        status = "✓ PASS" if result.passed else "✗ FAIL"
        print(f"  {i:2}. {result.name}: {status}")
        if not result.passed:
            print(f"      Error: {result.error}")

    print("-" * 60)
    print(f"Total: {passed} passed, {failed} failed out of {len(results)}")
    print("=" * 60 + "\n")

    return passed == len(results)


if __name__ == "__main__":
    success = run_all_simulations()
    sys.exit(0 if success else 1)
