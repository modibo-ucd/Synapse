"""LLM and embedding provider adapters (OpenAI-compatible)."""

from app.providers.openai import (
    OpenAIEmbeddingProvider,
    OpenAILLMClient,
    build_embedding_provider,
    build_llm_client,
    create_async_openai,
)
from app.providers.protocols import (
    EmbeddingProvider,
    LLMClient,
    LLMResult,
    ProviderError,
    ToolCall,
    ToolChatResult,
    ToolSpec,
)

__all__ = [
    "EmbeddingProvider",
    "LLMClient",
    "LLMResult",
    "OpenAIEmbeddingProvider",
    "OpenAILLMClient",
    "ProviderError",
    "ToolCall",
    "ToolChatResult",
    "ToolSpec",
    "build_embedding_provider",
    "build_llm_client",
    "create_async_openai",
]

