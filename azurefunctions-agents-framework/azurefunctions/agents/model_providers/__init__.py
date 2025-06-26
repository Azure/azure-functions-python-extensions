# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""Model providers for different LLM services."""

from .client import LLMClient

# Start with base exports
__all__ = ["LLMClient"]

# Optional providers - only import if dependencies are available
try:
    from .openai_provider import OpenAIProvider

    __all__.append("OpenAIProvider")
except ImportError:
    pass

try:
    from .azure_openai_provider import AzureOpenAIProvider

    __all__.append("AzureOpenAIProvider")
except ImportError:
    pass

try:
    from .anthropic_provider import AnthropicProvider

    __all__.append("AnthropicProvider")
except ImportError:
    pass

try:
    from .google_provider import GoogleProvider

    __all__.append("GoogleProvider")
except ImportError:
    pass
