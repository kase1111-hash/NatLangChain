"""
NatLangChain - Multi-Provider LLM Abstraction Layer

Implements support for all mainstream LLM providers to eliminate centralization risk:
- Anthropic Claude (cloud)
- OpenAI GPT-4/GPT-4o (cloud)
- Google Gemini (cloud)
- xAI Grok (cloud)
- Ollama (local)
- llama.cpp (local)

This addresses the centralization risk identified in blockchain research:
"LLM Dependency Creates Centralization Risk... If the LLM service is unavailable,
validation stops... Provider centralization unlike PoW/PoS where anyone can participate"
"""

import json
import logging
import os
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import shutil
from urllib.parse import urlparse

import requests

# Configure module-level logger
logger = logging.getLogger(__name__)

# SECURITY: Provider URL SSRF validation (Finding 6.2, 7.1)
ALLOW_LOCAL_PROVIDERS = os.getenv("NATLANGCHAIN_ALLOW_LOCAL_PROVIDERS", "true").lower() == "true"
_ALLOWED_PROVIDER_HOSTS_STR = os.getenv("NATLANGCHAIN_ALLOWED_PROVIDER_HOSTS", "")
ALLOWED_PROVIDER_HOSTS = [
    h.strip() for h in _ALLOWED_PROVIDER_HOSTS_STR.split(",") if h.strip()
]


def _validate_provider_url(url: str) -> tuple[bool, str | None]:
    """
    Validate provider URL against SSRF protections with local exception.

    SECURITY: Prevents SSRF attacks via provider base URLs (Finding 6.2).
    Allows localhost by default for local providers (configurable via
    NATLANGCHAIN_ALLOW_LOCAL_PROVIDERS).

    Also enforces optional host allowlist via NATLANGCHAIN_ALLOWED_PROVIDER_HOSTS
    (Finding 7.1).
    """
    if not url:
        return False, "Provider URL is required"

    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    # Check optional host allowlist (Finding 7.1)
    if ALLOWED_PROVIDER_HOSTS:
        if hostname not in ALLOWED_PROVIDER_HOSTS:
            return False, (
                f"Provider host '{hostname}' not in allowed list. "
                f"Allowed: {ALLOWED_PROVIDER_HOSTS}"
            )
        return True, None

    # Allow localhost for local provider usage
    if ALLOW_LOCAL_PROVIDERS and hostname in ("localhost", "127.0.0.1", "::1"):
        return True, None

    # Full SSRF validation for non-local URLs
    try:
        from api.ssrf_protection import validate_url_for_ssrf
        return validate_url_for_ssrf(url)
    except ImportError:
        # If ssrf_protection not importable, at least block obvious dangerous hosts
        if hostname in ("169.254.169.254", "metadata.google.internal"):
            return False, f"Access to host '{hostname}' is blocked for security reasons"
        return True, None

# SECURITY: Allowlist of permitted llama.cpp binary paths (Finding 6.1)
ALLOWED_CLI_PATHS = {
    "llama-cli",
    "/usr/local/bin/llama-cli",
    "/usr/bin/llama-cli",
    "/opt/llama.cpp/llama-cli",
}

# SECURITY: Maximum prompt size for CLI subprocess invocation (Finding 6.1)
MAX_CLI_PROMPT_LENGTH = 100_000  # 100KB


def _validate_cli_path(cli_path: str) -> str:
    """Validate cli_path against allowlist. Returns resolved path or raises ValueError."""
    resolved = shutil.which(cli_path) or cli_path
    if cli_path not in ALLOWED_CLI_PATHS and resolved not in ALLOWED_CLI_PATHS:
        raise ValueError(
            f"CLI path '{cli_path}' is not in the allowed list. "
            f"Allowed paths: {sorted(ALLOWED_CLI_PATHS)}"
        )
    return resolved


class ProviderType(Enum):
    """Classification of LLM provider types."""

    CLOUD = "cloud"  # Requires API key, external service
    LOCAL = "local"  # Runs on local machine, no API key needed


class ProviderStrength(Enum):
    """
    Provider strengths for weighted consensus.

    Based on Future.md's Tiered Validation Stack:
    - Nuance: Best at semantic subtlety and context
    - Logic: Best at logical reasoning and consistency
    - Breadth: Best at broad knowledge and coverage
    - Speed: Fastest response time for real-time validation
    """

    NUANCE = "nuance"
    LOGIC = "logic"
    BREADTH = "breadth"
    SPEED = "speed"
    BALANCED = "balanced"


@dataclass
class ProviderConfig:
    """Configuration for an LLM provider."""

    name: str
    provider_type: ProviderType
    strength: ProviderStrength
    weight: float = 1.0
    model_id: str = ""
    api_key: str | None = field(default=None, repr=False)
    base_url: str | None = None
    timeout: int = 30
    max_retries: int = 3
    enabled: bool = True
    extra_params: dict = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    success: bool
    content: str | None = None
    error: str | None = None
    model: str = ""
    provider: str = ""
    latency_ms: float = 0
    tokens_used: int = 0
    raw_response: Any = None


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.

    All providers must implement the `complete` method which takes a prompt
    and returns a standardized LLMResponse.
    """

    def __init__(self, config: ProviderConfig):
        """
        Initialize the provider.

        Args:
            config: Provider configuration
        """
        self.config = config
        self.name = config.name
        self._client = None

    @abstractmethod
    def complete(self, prompt: str, max_tokens: int = 512) -> LLMResponse:
        """
        Send a completion request to the LLM.

        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens in response

        Returns:
            Standardized LLMResponse
        """

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is available and configured.

        Returns:
            True if provider can accept requests
        """

    def _extract_json_from_response(self, response_text: str) -> str:
        """
        Extract JSON from a response that may contain markdown code blocks.

        Args:
            response_text: Raw response text

        Returns:
            Extracted JSON string
        """
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            if json_end != -1:
                return response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            if json_end != -1:
                return response_text[json_start:json_end].strip()
        return response_text.strip()

    def parse_json_response(self, response_text: str) -> dict[str, Any] | None:
        """
        Parse JSON from response text.

        Args:
            response_text: Raw response text

        Returns:
            Parsed JSON dict or None if parsing fails
        """
        try:
            json_str = self._extract_json_from_response(response_text)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse JSON from %s response: %s", self.name, str(e))
            return None


# =============================================================================
# Cloud Providers
# =============================================================================


class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude provider.

    Strength: Nuance - Best at semantic subtlety and context understanding.
    Models: claude-3-5-sonnet, claude-3-opus, claude-3-haiku
    """

    def __init__(self, config: ProviderConfig | None = None):
        if config is None:
            config = ProviderConfig(
                name="anthropic",
                provider_type=ProviderType.CLOUD,
                strength=ProviderStrength.NUANCE,
                weight=1.0,
                model_id="claude-sonnet-4-20250514",
                api_key=os.getenv("ANTHROPIC_API_KEY"),
            )
        super().__init__(config)

    def is_available(self) -> bool:
        """Check if Anthropic API is available."""
        if not self.config.api_key:
            return False
        try:
            import httpx
            from anthropic import Anthropic

            # Create client with timeout configuration
            timeout = httpx.Timeout(
                connect=10.0,  # Connection timeout
                read=self.config.timeout,  # Read timeout (default 30s)
                write=10.0,  # Write timeout
                pool=10.0,  # Pool timeout
            )
            self._client = Anthropic(
                api_key=self.config.api_key,
                timeout=timeout,
            )
            return True
        except ImportError:
            logger.warning("anthropic package not installed")
            return False
        except Exception as e:
            logger.warning("Anthropic client initialization failed: %s", str(e))
            return False

    def complete(self, prompt: str, max_tokens: int = 512) -> LLMResponse:
        """Send completion request to Claude with timeout protection."""
        if not self.is_available():
            return LLMResponse(
                success=False,
                error="Anthropic provider not available",
                provider=self.name,
            )

        start_time = time.time()
        try:
            import httpx
            from anthropic import Anthropic

            if self._client is None:
                # Create client with timeout configuration
                timeout = httpx.Timeout(
                    connect=10.0,
                    read=self.config.timeout,
                    write=10.0,
                    pool=10.0,
                )
                self._client = Anthropic(
                    api_key=self.config.api_key,
                    timeout=timeout,
                )

            message = self._client.messages.create(
                model=self.config.model_id,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            latency = (time.time() - start_time) * 1000

            if not message.content:
                return LLMResponse(
                    success=False,
                    error="Empty response from Claude",
                    provider=self.name,
                    model=self.config.model_id,
                    latency_ms=latency,
                )

            content = message.content[0].text if hasattr(message.content[0], "text") else ""

            return LLMResponse(
                success=True,
                content=content,
                provider=self.name,
                model=self.config.model_id,
                latency_ms=latency,
                tokens_used=message.usage.output_tokens if hasattr(message, "usage") else 0,
                raw_response=message,
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            error_type = type(e).__name__

            # Check for timeout errors
            if "timeout" in str(e).lower() or "Timeout" in error_type:
                logger.error(
                    "Anthropic API timeout after %.1fs (limit: %ds): %s",
                    latency / 1000,
                    self.config.timeout,
                    str(e),
                )
                return LLMResponse(
                    success=False,
                    error=f"API timeout after {self.config.timeout}s",
                    provider=self.name,
                    model=self.config.model_id,
                    latency_ms=latency,
                )

            logger.error("Anthropic completion failed: %s", str(e))
            return LLMResponse(
                success=False,
                error=str(e),
                provider=self.name,
                model=self.config.model_id,
                latency_ms=latency,
            )


class OpenAIProvider(LLMProvider):
    """
    OpenAI GPT provider.

    Strength: Breadth - Best at broad knowledge and diverse capabilities.
    Models: gpt-4o, gpt-4-turbo, gpt-4, gpt-3.5-turbo
    """

    def __init__(self, config: ProviderConfig | None = None):
        if config is None:
            config = ProviderConfig(
                name="openai",
                provider_type=ProviderType.CLOUD,
                strength=ProviderStrength.BREADTH,
                weight=1.0,
                model_id="gpt-4o",
                api_key=os.getenv("OPENAI_API_KEY"),
            )
        super().__init__(config)

    def is_available(self) -> bool:
        """Check if OpenAI API is available."""
        if not self.config.api_key:
            return False
        try:
            import httpx
            from openai import OpenAI

            # Create client with timeout configuration
            timeout = httpx.Timeout(
                connect=10.0,
                read=self.config.timeout,
                write=10.0,
                pool=10.0,
            )
            self._client = OpenAI(
                api_key=self.config.api_key,
                timeout=timeout,
            )
            return True
        except ImportError:
            logger.warning("openai package not installed. Install with: pip install openai")
            return False
        except Exception as e:
            logger.warning("OpenAI client initialization failed: %s", str(e))
            return False

    def complete(self, prompt: str, max_tokens: int = 512) -> LLMResponse:
        """Send completion request to GPT with timeout protection."""
        if not self.is_available():
            return LLMResponse(
                success=False,
                error="OpenAI provider not available",
                provider=self.name,
            )

        start_time = time.time()
        try:
            import httpx
            from openai import OpenAI

            if self._client is None:
                timeout = httpx.Timeout(
                    connect=10.0,
                    read=self.config.timeout,
                    write=10.0,
                    pool=10.0,
                )
                self._client = OpenAI(
                    api_key=self.config.api_key,
                    timeout=timeout,
                )

            response = self._client.chat.completions.create(
                model=self.config.model_id,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            latency = (time.time() - start_time) * 1000

            if not response.choices:
                return LLMResponse(
                    success=False,
                    error="Empty response from OpenAI",
                    provider=self.name,
                    model=self.config.model_id,
                    latency_ms=latency,
                )

            content = response.choices[0].message.content or ""

            return LLMResponse(
                success=True,
                content=content,
                provider=self.name,
                model=self.config.model_id,
                latency_ms=latency,
                tokens_used=response.usage.completion_tokens if response.usage else 0,
                raw_response=response,
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            error_type = type(e).__name__

            # Check for timeout errors
            if "timeout" in str(e).lower() or "Timeout" in error_type:
                logger.error(
                    "OpenAI API timeout after %.1fs (limit: %ds): %s",
                    latency / 1000,
                    self.config.timeout,
                    str(e),
                )
                return LLMResponse(
                    success=False,
                    error=f"API timeout after {self.config.timeout}s",
                    provider=self.name,
                    model=self.config.model_id,
                    latency_ms=latency,
                )

            logger.error("OpenAI completion failed: %s", str(e))
            return LLMResponse(
                success=False,
                error=str(e),
                provider=self.name,
                model=self.config.model_id,
                latency_ms=latency,
            )


class GeminiProvider(LLMProvider):
    """
    Google Gemini provider.

    Strength: Balanced - Good all-around performance with multimodal capabilities.
    Models: gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash
    """

    def __init__(self, config: ProviderConfig | None = None):
        if config is None:
            config = ProviderConfig(
                name="gemini",
                provider_type=ProviderType.CLOUD,
                strength=ProviderStrength.BALANCED,
                weight=1.0,
                model_id="gemini-2.0-flash",
                api_key=os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"),
            )
        super().__init__(config)

    def is_available(self) -> bool:
        """Check if Gemini API is available."""
        if not self.config.api_key:
            return False
        try:
            import google.generativeai as genai

            genai.configure(api_key=self.config.api_key)
            self._client = genai.GenerativeModel(self.config.model_id)
            return True
        except ImportError:
            logger.warning(
                "google-generativeai package not installed. "
                "Install with: pip install google-generativeai"
            )
            return False
        except Exception as e:
            logger.warning("Gemini client initialization failed: %s", str(e))
            return False

    def complete(self, prompt: str, max_tokens: int = 512) -> LLMResponse:
        """Send completion request to Gemini."""
        if not self.is_available():
            return LLMResponse(
                success=False,
                error="Gemini provider not available",
                provider=self.name,
            )

        start_time = time.time()
        try:
            import google.generativeai as genai

            if self._client is None:
                genai.configure(api_key=self.config.api_key)
                self._client = genai.GenerativeModel(self.config.model_id)

            response = self._client.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    max_output_tokens=max_tokens,
                ),
            )

            latency = (time.time() - start_time) * 1000

            if not response.text:
                return LLMResponse(
                    success=False,
                    error="Empty response from Gemini",
                    provider=self.name,
                    model=self.config.model_id,
                    latency_ms=latency,
                )

            return LLMResponse(
                success=True,
                content=response.text,
                provider=self.name,
                model=self.config.model_id,
                latency_ms=latency,
                raw_response=response,
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error("Gemini completion failed: %s", str(e))
            return LLMResponse(
                success=False,
                error=str(e),
                provider=self.name,
                model=self.config.model_id,
                latency_ms=latency,
            )


class GrokProvider(LLMProvider):
    """
    xAI Grok provider.

    Strength: Logic - Strong reasoning capabilities with real-time knowledge.
    Models: grok-2, grok-2-mini, grok-beta
    """

    def __init__(self, config: ProviderConfig | None = None):
        if config is None:
            config = ProviderConfig(
                name="grok",
                provider_type=ProviderType.CLOUD,
                strength=ProviderStrength.LOGIC,
                weight=1.0,
                model_id="grok-2",
                api_key=os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY"),
                base_url="https://api.x.ai/v1",
            )
        super().__init__(config)

    def is_available(self) -> bool:
        """Check if Grok API is available."""
        if not self.config.api_key:
            return False
        try:
            # Grok uses OpenAI-compatible API
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url,
            )
            return True
        except ImportError:
            logger.warning(
                "openai package not installed (required for Grok). Install with: pip install openai"
            )
            return False
        except Exception as e:
            logger.warning("Grok client initialization failed: %s", str(e))
            return False

    def complete(self, prompt: str, max_tokens: int = 512) -> LLMResponse:
        """Send completion request to Grok."""
        if not self.is_available():
            return LLMResponse(
                success=False,
                error="Grok provider not available",
                provider=self.name,
            )

        start_time = time.time()
        try:
            from openai import OpenAI

            if self._client is None:
                self._client = OpenAI(
                    api_key=self.config.api_key,
                    base_url=self.config.base_url,
                )

            response = self._client.chat.completions.create(
                model=self.config.model_id,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

            latency = (time.time() - start_time) * 1000

            if not response.choices:
                return LLMResponse(
                    success=False,
                    error="Empty response from Grok",
                    provider=self.name,
                    model=self.config.model_id,
                    latency_ms=latency,
                )

            content = response.choices[0].message.content or ""

            return LLMResponse(
                success=True,
                content=content,
                provider=self.name,
                model=self.config.model_id,
                latency_ms=latency,
                tokens_used=response.usage.completion_tokens if response.usage else 0,
                raw_response=response,
            )

        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error("Grok completion failed: %s", str(e))
            return LLMResponse(
                success=False,
                error=str(e),
                provider=self.name,
                model=self.config.model_id,
                latency_ms=latency,
            )


# =============================================================================
# Local Providers
# =============================================================================


class OllamaProvider(LLMProvider):
    """
    Ollama local LLM provider.

    Strength: Speed - Fast local inference with no API latency.
    Models: llama3.2, mistral, qwen2.5, deepseek-r1, phi3, etc.

    Ollama must be running locally: https://ollama.ai
    Default endpoint: http://localhost:11434
    """

    def __init__(self, config: ProviderConfig | None = None):
        if config is None:
            config = ProviderConfig(
                name="ollama",
                provider_type=ProviderType.LOCAL,
                strength=ProviderStrength.SPEED,
                weight=0.8,  # Slightly lower weight for local models
                model_id=os.getenv("OLLAMA_MODEL", "llama3.2"),
                base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            )
        super().__init__(config)

        # SECURITY: Validate base URL against SSRF protections (Finding 6.2)
        if self.config.base_url:
            is_safe, error_msg = _validate_provider_url(self.config.base_url)
            if not is_safe:
                logger.error("Ollama base URL failed SSRF validation: %s", error_msg)
                self.config.enabled = False

    def is_available(self) -> bool:
        """Check if Ollama server is running and model is available."""
        if not self.config.enabled:
            return False
        try:
            response = requests.get(
                f"{self.config.base_url}/api/tags",
                timeout=5,
            )
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "").split(":")[0] for m in models]
                if self.config.model_id.split(":")[0] in model_names:
                    return True
                elif models:
                    # Use first available model if specified model not found
                    logger.info(
                        "Ollama model '%s' not found, available: %s",
                        self.config.model_id,
                        model_names,
                    )
                    return True
            return False
        except requests.RequestException:
            logger.warning(
                "Ollama not available at %s. Start with: ollama serve",
                self.config.base_url,
            )
            return False

    def complete(self, prompt: str, max_tokens: int = 512) -> LLMResponse:
        """Send completion request to Ollama."""
        if not self.is_available():
            return LLMResponse(
                success=False,
                error="Ollama provider not available",
                provider=self.name,
            )

        start_time = time.time()
        try:
            response = requests.post(
                f"{self.config.base_url}/api/generate",
                json={
                    "model": self.config.model_id,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                    },
                },
                timeout=self.config.timeout,
            )

            latency = (time.time() - start_time) * 1000

            if response.status_code != 200:
                return LLMResponse(
                    success=False,
                    error=f"Ollama returned status {response.status_code}",
                    provider=self.name,
                    model=self.config.model_id,
                    latency_ms=latency,
                )

            result = response.json()
            content = result.get("response", "")

            return LLMResponse(
                success=True,
                content=content,
                provider=self.name,
                model=self.config.model_id,
                latency_ms=latency,
                tokens_used=result.get("eval_count", 0),
                raw_response=result,
            )

        except requests.RequestException as e:
            latency = (time.time() - start_time) * 1000
            logger.error("Ollama completion failed: %s", str(e))
            return LLMResponse(
                success=False,
                error=str(e),
                provider=self.name,
                model=self.config.model_id,
                latency_ms=latency,
            )


class LlamaCppProvider(LLMProvider):
    """
    llama.cpp local LLM provider.

    Strength: Speed - Ultra-fast CPU/GPU inference for GGUF models.

    Supports two modes:
    1. llama-server HTTP API (recommended): Run llama-server separately
    2. Direct CLI invocation (fallback): Uses llama-cli directly

    Setup:
    - Install: https://github.com/ggerganov/llama.cpp
    - Download GGUF model (e.g., from HuggingFace)
    - Server mode: llama-server -m model.gguf --port 8080
    """

    def __init__(self, config: ProviderConfig | None = None):
        if config is None:
            config = ProviderConfig(
                name="llama_cpp",
                provider_type=ProviderType.LOCAL,
                strength=ProviderStrength.SPEED,
                weight=0.8,
                model_id=os.getenv("LLAMA_CPP_MODEL", ""),
                base_url=os.getenv("LLAMA_CPP_HOST", "http://localhost:8080"),
                extra_params={
                    "cli_path": os.getenv("LLAMA_CPP_CLI", "llama-cli"),
                    "use_server": True,  # Prefer server mode
                },
            )
        super().__init__(config)
        self._use_server = self.config.extra_params.get("use_server", True)

        # SECURITY: Validate base URL against SSRF protections (Finding 6.2)
        if self.config.base_url:
            is_safe, error_msg = _validate_provider_url(self.config.base_url)
            if not is_safe:
                logger.error("llama.cpp base URL failed SSRF validation: %s", error_msg)
                self.config.enabled = False

    def is_available(self) -> bool:
        """Check if llama.cpp is available (server or CLI)."""
        if not self.config.enabled:
            return False
        # Try server mode first
        if self._use_server:
            try:
                response = requests.get(
                    f"{self.config.base_url}/health",
                    timeout=5,
                )
                if response.status_code == 200:
                    return True
            except requests.RequestException:
                logger.info(
                    "llama.cpp server not available at %s, trying CLI mode",
                    self.config.base_url,
                )
                self._use_server = False

        # Try CLI mode
        cli_path = self.config.extra_params.get("cli_path", "llama-cli")
        # SECURITY: Validate cli_path against allowlist (Finding 6.1)
        try:
            cli_path = _validate_cli_path(cli_path)
        except ValueError:
            logger.warning("llama.cpp CLI path '%s' not in allowlist", cli_path)
            return False
        try:
            result = subprocess.run(
                [cli_path, "--version"],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0:
                if self.config.model_id and os.path.exists(self.config.model_id):
                    return True
                logger.warning(
                    "llama.cpp CLI available but no model specified. "
                    "Set LLAMA_CPP_MODEL to path of GGUF file."
                )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        logger.warning(
            "llama.cpp not available. "
            "Either run llama-server or set LLAMA_CPP_CLI and LLAMA_CPP_MODEL"
        )
        return False

    def complete(self, prompt: str, max_tokens: int = 512) -> LLMResponse:
        """Send completion request to llama.cpp."""
        if self._use_server:
            return self._complete_server(prompt, max_tokens)
        else:
            return self._complete_cli(prompt, max_tokens)

    def _complete_server(self, prompt: str, max_tokens: int) -> LLMResponse:
        """Complete using llama.cpp server API."""
        start_time = time.time()
        try:
            response = requests.post(
                f"{self.config.base_url}/completion",
                json={
                    "prompt": prompt,
                    "n_predict": max_tokens,
                    "stream": False,
                },
                timeout=self.config.timeout,
            )

            latency = (time.time() - start_time) * 1000

            if response.status_code != 200:
                return LLMResponse(
                    success=False,
                    error=f"llama.cpp server returned status {response.status_code}",
                    provider=self.name,
                    model=self.config.model_id,
                    latency_ms=latency,
                )

            result = response.json()
            content = result.get("content", "")

            return LLMResponse(
                success=True,
                content=content,
                provider=self.name,
                model=self.config.model_id or "llama.cpp-server",
                latency_ms=latency,
                tokens_used=result.get("tokens_predicted", 0),
                raw_response=result,
            )

        except requests.RequestException as e:
            latency = (time.time() - start_time) * 1000
            logger.error("llama.cpp server completion failed: %s", str(e))
            return LLMResponse(
                success=False,
                error=str(e),
                provider=self.name,
                model=self.config.model_id,
                latency_ms=latency,
            )

    def _complete_cli(self, prompt: str, max_tokens: int) -> LLMResponse:
        """Complete using llama.cpp CLI directly."""
        start_time = time.time()
        cli_path = self.config.extra_params.get("cli_path", "llama-cli")

        # SECURITY: Validate cli_path against allowlist (Finding 6.1)
        try:
            cli_path = _validate_cli_path(cli_path)
        except ValueError as e:
            return LLMResponse(
                success=False,
                error=str(e),
                provider=self.name,
                model=self.config.model_id,
            )

        # SECURITY: Enforce prompt size limit for subprocess (Finding 6.1)
        if len(prompt) > MAX_CLI_PROMPT_LENGTH:
            return LLMResponse(
                success=False,
                error=f"Prompt exceeds maximum CLI length ({MAX_CLI_PROMPT_LENGTH} chars)",
                provider=self.name,
                model=self.config.model_id,
            )

        try:
            result = subprocess.run(
                [
                    cli_path,
                    "-m",
                    self.config.model_id,
                    "-p",
                    prompt,
                    "-n",
                    str(max_tokens),
                    "--no-display-prompt",
                ],
                capture_output=True,
                text=True,
                timeout=self.config.timeout,
                check=False,
            )

            latency = (time.time() - start_time) * 1000

            if result.returncode != 0:
                return LLMResponse(
                    success=False,
                    error=f"llama.cpp CLI failed: {result.stderr}",
                    provider=self.name,
                    model=self.config.model_id,
                    latency_ms=latency,
                )

            return LLMResponse(
                success=True,
                content=result.stdout.strip(),
                provider=self.name,
                model=os.path.basename(self.config.model_id),
                latency_ms=latency,
            )

        except subprocess.TimeoutExpired:
            latency = (time.time() - start_time) * 1000
            return LLMResponse(
                success=False,
                error="llama.cpp CLI timed out",
                provider=self.name,
                model=self.config.model_id,
                latency_ms=latency,
            )
        except Exception as e:
            latency = (time.time() - start_time) * 1000
            logger.error("llama.cpp CLI completion failed: %s", str(e))
            return LLMResponse(
                success=False,
                error=str(e),
                provider=self.name,
                model=self.config.model_id,
                latency_ms=latency,
            )


# =============================================================================
# Provider Manager
# =============================================================================


class ProviderManager:
    """
    Manages multiple LLM providers for multi-model consensus.

    Automatically discovers and initializes available providers based on
    environment configuration. Supports both cloud and local providers.
    """

    # Registry of available provider classes
    PROVIDER_REGISTRY: dict[str, type[LLMProvider]] = {
        "anthropic": AnthropicProvider,
        "openai": OpenAIProvider,
        "gemini": GeminiProvider,
        "grok": GrokProvider,
        "ollama": OllamaProvider,
        "llama_cpp": LlamaCppProvider,
    }

    def __init__(
        self,
        auto_discover: bool = True,
        required_providers: list[str] | None = None,
    ):
        """
        Initialize the provider manager.

        Args:
            auto_discover: Automatically discover available providers
            required_providers: List of provider names that must be available
        """
        self.providers: dict[str, LLMProvider] = {}
        self._required = required_providers or []

        if auto_discover:
            self.discover_providers()

    def discover_providers(self) -> dict[str, bool]:
        """
        Discover and initialize all available providers.

        Returns:
            Dict mapping provider name to availability status
        """
        discovery_results = {}

        for name, provider_class in self.PROVIDER_REGISTRY.items():
            try:
                provider = provider_class()
                if provider.is_available():
                    self.providers[name] = provider
                    discovery_results[name] = True
                    logger.info(
                        "Provider '%s' available (model: %s, strength: %s)",
                        name,
                        provider.config.model_id,
                        provider.config.strength.value,
                    )
                else:
                    discovery_results[name] = False
            except Exception as e:
                discovery_results[name] = False
                logger.debug("Provider '%s' initialization failed: %s", name, str(e))

        # Check required providers
        for required in self._required:
            if required not in self.providers:
                raise ValueError(
                    f"Required provider '{required}' not available. "
                    f"Available: {list(self.providers.keys())}"
                )

        if not self.providers:
            logger.warning(
                "No LLM providers available. Configure at least one:\n"
                "  Cloud: ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, XAI_API_KEY\n"
                "  Local: ollama serve, or llama-server"
            )

        return discovery_results

    def add_provider(self, provider: LLMProvider) -> None:
        """
        Add a custom provider instance.

        Args:
            provider: Provider instance to add
        """
        if provider.is_available():
            self.providers[provider.name] = provider
        else:
            raise ValueError(f"Provider '{provider.name}' is not available")

    def remove_provider(self, name: str) -> bool:
        """
        Remove a provider.

        Args:
            name: Provider name

        Returns:
            True if provider was removed
        """
        if name in self.providers:
            del self.providers[name]
            return True
        return False

    def get_provider(self, name: str) -> LLMProvider | None:
        """
        Get a specific provider.

        Args:
            name: Provider name

        Returns:
            Provider instance or None
        """
        return self.providers.get(name)

    def list_providers(self) -> list[dict[str, Any]]:
        """
        List all available providers with their configurations.

        Returns:
            List of provider info dicts
        """
        return [
            {
                "name": name,
                "type": provider.config.provider_type.value,
                "strength": provider.config.strength.value,
                "weight": provider.config.weight,
                "model": provider.config.model_id,
            }
            for name, provider in self.providers.items()
        ]

    def get_providers_by_type(self, provider_type: ProviderType) -> list[LLMProvider]:
        """
        Get providers of a specific type.

        Args:
            provider_type: CLOUD or LOCAL

        Returns:
            List of matching providers
        """
        return [p for p in self.providers.values() if p.config.provider_type == provider_type]

    def get_providers_by_strength(self, strength: ProviderStrength) -> list[LLMProvider]:
        """
        Get providers with a specific strength.

        Args:
            strength: Provider strength category

        Returns:
            List of matching providers
        """
        return [p for p in self.providers.values() if p.config.strength == strength]

    @property
    def provider_count(self) -> int:
        """Number of available providers."""
        return len(self.providers)

    @property
    def has_cloud_providers(self) -> bool:
        """Whether any cloud providers are available."""
        return any(p.config.provider_type == ProviderType.CLOUD for p in self.providers.values())

    @property
    def has_local_providers(self) -> bool:
        """Whether any local providers are available."""
        return any(p.config.provider_type == ProviderType.LOCAL for p in self.providers.values())


# =============================================================================
# Utility Functions
# =============================================================================


def get_default_provider_manager() -> ProviderManager:
    """
    Get a provider manager with auto-discovered providers.

    Returns:
        Configured ProviderManager instance
    """
    return ProviderManager(auto_discover=True)


def list_available_providers() -> list[str]:
    """
    List names of all available providers.

    Returns:
        List of provider names
    """
    manager = ProviderManager(auto_discover=True)
    return list(manager.providers.keys())


def quick_complete(prompt: str, provider_name: str | None = None) -> str | None:
    """
    Quick completion using first available provider.

    Args:
        prompt: Prompt to send
        provider_name: Optional specific provider to use

    Returns:
        Response text or None if failed
    """
    manager = ProviderManager(auto_discover=True)

    if provider_name and provider_name in manager.providers:
        provider = manager.providers[provider_name]
    elif manager.providers:
        provider = next(iter(manager.providers.values()))
    else:
        logger.error("No LLM providers available")
        return None

    response = provider.complete(prompt)
    return response.content if response.success else None
