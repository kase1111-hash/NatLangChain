"""
NatLangChain - Module Manifest System

Declares and enforces per-module capability requirements. Each module declares
what resources it needs (network endpoints, filesystem paths, shell commands,
external packages) in a YAML manifest file. At startup, manifests are validated
and any module attempting to use undeclared capabilities is flagged.

SECURITY (Audit 2.4): Addresses the "Skill/Module Signing and Sandboxing" gap
identified in the Agentic Security Audit. Provides:
- Per-module capability declarations (network, filesystem, shell, packages)
- Manifest validation at application startup
- Import allowlist enforcement
- Audit logging of all declared capabilities

Configuration:
    NATLANGCHAIN_MANIFEST_DIR=src/manifests   Directory containing manifest files
    NATLANGCHAIN_MANIFEST_ENFORCE=true        Enforce manifests (block unlisted modules)

Manifest Format (YAML):
    module: module_name
    version: "1.0"
    description: "What this module does"
    capabilities:
      network:
        - endpoint: "api.anthropic.com"
          protocol: "https"
          purpose: "LLM API calls"
      filesystem:
        - path: "$NATLANGCHAIN_IDENTITY_KEYSTORE"
          access: "read"
          purpose: "Load agent identity"
      shell:
        - command: "/usr/bin/llama-cli"
          purpose: "Local LLM inference"
      packages:
        - name: "anthropic"
          purpose: "Anthropic Claude API client"
"""

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Environment configuration
MANIFEST_DIR_ENV = "NATLANGCHAIN_MANIFEST_DIR"
MANIFEST_ENFORCE_ENV = "NATLANGCHAIN_MANIFEST_ENFORCE"

# Default manifest directory (relative to project root)
DEFAULT_MANIFEST_DIR = "src/manifests"


@dataclass
class NetworkCapability:
    """A declared network endpoint that a module may access."""
    endpoint: str
    protocol: str = "https"
    purpose: str = ""


@dataclass
class FilesystemCapability:
    """A declared filesystem path that a module may access."""
    path: str
    access: str = "read"  # "read", "write", or "readwrite"
    purpose: str = ""


@dataclass
class ShellCapability:
    """A declared shell command that a module may execute."""
    command: str
    purpose: str = ""


@dataclass
class PackageCapability:
    """A declared external package dependency."""
    name: str
    purpose: str = ""


@dataclass
class ModuleManifest:
    """Parsed capability manifest for a module."""
    module: str
    version: str = "1.0"
    description: str = ""
    network: list[NetworkCapability] = field(default_factory=list)
    filesystem: list[FilesystemCapability] = field(default_factory=list)
    shell: list[ShellCapability] = field(default_factory=list)
    packages: list[PackageCapability] = field(default_factory=list)

    @property
    def has_network(self) -> bool:
        return len(self.network) > 0

    @property
    def has_filesystem(self) -> bool:
        return len(self.filesystem) > 0

    @property
    def has_shell(self) -> bool:
        return len(self.shell) > 0

    @property
    def capability_summary(self) -> dict[str, int]:
        """Return a count of each capability type."""
        return {
            "network": len(self.network),
            "filesystem": len(self.filesystem),
            "shell": len(self.shell),
            "packages": len(self.packages),
        }


def _parse_manifest(data: dict[str, Any]) -> ModuleManifest:
    """
    Parse a manifest dictionary into a ModuleManifest.

    Args:
        data: Parsed YAML/dict data

    Returns:
        ModuleManifest with parsed capabilities

    Raises:
        ValueError: If manifest is missing required fields
    """
    module_name = data.get("module")
    if not module_name:
        raise ValueError("Manifest missing required 'module' field")

    manifest = ModuleManifest(
        module=module_name,
        version=str(data.get("version", "1.0")),
        description=data.get("description", ""),
    )

    capabilities = data.get("capabilities", {})

    # Parse network capabilities
    for net in capabilities.get("network", []):
        if isinstance(net, dict):
            manifest.network.append(NetworkCapability(
                endpoint=net.get("endpoint", ""),
                protocol=net.get("protocol", "https"),
                purpose=net.get("purpose", ""),
            ))

    # Parse filesystem capabilities
    for fs in capabilities.get("filesystem", []):
        if isinstance(fs, dict):
            manifest.filesystem.append(FilesystemCapability(
                path=fs.get("path", ""),
                access=fs.get("access", "read"),
                purpose=fs.get("purpose", ""),
            ))

    # Parse shell capabilities
    for sh in capabilities.get("shell", []):
        if isinstance(sh, dict):
            manifest.shell.append(ShellCapability(
                command=sh.get("command", ""),
                purpose=sh.get("purpose", ""),
            ))

    # Parse package capabilities
    for pkg in capabilities.get("packages", []):
        if isinstance(pkg, dict):
            manifest.packages.append(PackageCapability(
                name=pkg.get("name", ""),
                purpose=pkg.get("purpose", ""),
            ))

    return manifest


def _get_manifest_dir() -> str:
    """Get the manifest directory path."""
    return os.getenv(MANIFEST_DIR_ENV, DEFAULT_MANIFEST_DIR)


def _is_enforcement_enabled() -> bool:
    """Check if manifest enforcement is enabled."""
    return os.getenv(MANIFEST_ENFORCE_ENV, "false").lower() == "true"


class ManifestRegistry:
    """
    Registry of all loaded module manifests.

    Loads manifest files from the manifest directory and provides
    lookup, validation, and audit reporting capabilities.
    """

    def __init__(self):
        self._manifests: dict[str, ModuleManifest] = {}
        self._violations: list[dict[str, str]] = []

    @property
    def manifests(self) -> dict[str, ModuleManifest]:
        """All loaded manifests keyed by module name."""
        return dict(self._manifests)

    @property
    def violations(self) -> list[dict[str, str]]:
        """All recorded violations."""
        return list(self._violations)

    def load_manifests(self, manifest_dir: str | None = None) -> int:
        """
        Load all manifest YAML files from the manifest directory.

        Args:
            manifest_dir: Directory containing manifest files (default: from env)

        Returns:
            Number of manifests loaded
        """
        import yaml

        directory = manifest_dir or _get_manifest_dir()

        if not os.path.isdir(directory):
            logger.warning("Manifest directory not found: %s", directory)
            return 0

        count = 0
        manifest_path = Path(directory)

        for yaml_file in sorted(manifest_path.glob("*.yaml")):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)

                if not isinstance(data, dict):
                    logger.warning("Invalid manifest format in %s", yaml_file)
                    continue

                manifest = _parse_manifest(data)
                self._manifests[manifest.module] = manifest
                count += 1

                logger.info(
                    "Loaded manifest: module=%s capabilities=%s",
                    manifest.module,
                    manifest.capability_summary,
                )

            except Exception as e:
                logger.error("Failed to load manifest %s: %s", yaml_file, e)

        return count

    def get_manifest(self, module_name: str) -> ModuleManifest | None:
        """Get the manifest for a specific module."""
        return self._manifests.get(module_name)

    def has_manifest(self, module_name: str) -> bool:
        """Check if a module has a registered manifest."""
        return module_name in self._manifests

    def validate_import(self, module_name: str) -> bool:
        """
        Validate that a module has a manifest before importing.

        In enforcement mode, modules without manifests are blocked.
        In audit mode (default), missing manifests are logged as warnings.

        Args:
            module_name: Name of the module being imported

        Returns:
            True if import is allowed, False if blocked
        """
        # Skip stdlib and well-known framework modules
        if module_name.startswith(("_", "os", "sys", "json", "re", "logging",
                                   "hashlib", "base64", "math", "time",
                                   "threading", "collections", "dataclasses",
                                   "typing", "abc", "enum", "functools",
                                   "pathlib", "datetime", "uuid", "socket",
                                   "ipaddress", "urllib", "contextlib",
                                   "unicodedata", "secrets", "gzip",
                                   "shutil", "subprocess")):
            return True

        # Skip flask (framework, not a module we control)
        if module_name.startswith("flask"):
            return True

        if not self.has_manifest(module_name):
            violation = {
                "type": "missing_manifest",
                "module": module_name,
                "action": "blocked" if _is_enforcement_enabled() else "warned",
            }
            self._violations.append(violation)

            if _is_enforcement_enabled():
                logger.warning(
                    "BLOCKED import of module '%s': no manifest found", module_name
                )
                return False
            else:
                logger.info(
                    "Module '%s' has no manifest (enforcement disabled)", module_name
                )

        return True

    def check_network_capability(
        self, module_name: str, endpoint: str
    ) -> bool:
        """
        Check if a module has declared a network capability for an endpoint.

        Args:
            module_name: Module requesting network access
            endpoint: The endpoint being accessed

        Returns:
            True if the capability is declared or enforcement is disabled
        """
        manifest = self.get_manifest(module_name)
        if not manifest:
            return not _is_enforcement_enabled()

        for cap in manifest.network:
            if cap.endpoint == endpoint or endpoint.endswith(cap.endpoint):
                return True

        violation = {
            "type": "undeclared_network",
            "module": module_name,
            "endpoint": endpoint,
            "action": "blocked" if _is_enforcement_enabled() else "warned",
        }
        self._violations.append(violation)

        logger.warning(
            "Module '%s' accessing undeclared network endpoint: %s",
            module_name, endpoint,
        )
        return not _is_enforcement_enabled()

    def check_shell_capability(
        self, module_name: str, command: str
    ) -> bool:
        """
        Check if a module has declared a shell capability for a command.

        Args:
            module_name: Module requesting shell access
            command: The command being executed

        Returns:
            True if the capability is declared or enforcement is disabled
        """
        manifest = self.get_manifest(module_name)
        if not manifest:
            return not _is_enforcement_enabled()

        for cap in manifest.shell:
            if cap.command == command or command.startswith(cap.command):
                return True

        violation = {
            "type": "undeclared_shell",
            "module": module_name,
            "command": command,
            "action": "blocked" if _is_enforcement_enabled() else "warned",
        }
        self._violations.append(violation)

        logger.warning(
            "Module '%s' executing undeclared shell command: %s",
            module_name, command,
        )
        return not _is_enforcement_enabled()

    def audit_report(self) -> dict[str, Any]:
        """
        Generate an audit report of all manifests and violations.

        Returns:
            Dict with manifest summary, capability totals, and violations
        """
        total_network = 0
        total_filesystem = 0
        total_shell = 0
        total_packages = 0

        modules_summary = []
        for name, manifest in sorted(self._manifests.items()):
            caps = manifest.capability_summary
            total_network += caps["network"]
            total_filesystem += caps["filesystem"]
            total_shell += caps["shell"]
            total_packages += caps["packages"]

            modules_summary.append({
                "module": name,
                "description": manifest.description,
                "capabilities": caps,
            })

        return {
            "total_modules": len(self._manifests),
            "enforcement_enabled": _is_enforcement_enabled(),
            "totals": {
                "network_endpoints": total_network,
                "filesystem_paths": total_filesystem,
                "shell_commands": total_shell,
                "external_packages": total_packages,
            },
            "modules": modules_summary,
            "violations": self._violations,
        }


# Singleton registry
registry = ManifestRegistry()


def load_all_manifests(manifest_dir: str | None = None) -> int:
    """
    Load all module manifests from the manifest directory.

    Args:
        manifest_dir: Directory path (default: from environment or src/manifests)

    Returns:
        Number of manifests loaded
    """
    return registry.load_manifests(manifest_dir)


def get_manifest(module_name: str) -> ModuleManifest | None:
    """Get the manifest for a specific module."""
    return registry.get_manifest(module_name)


def get_audit_report() -> dict[str, Any]:
    """Get an audit report of all manifests and violations."""
    return registry.audit_report()
