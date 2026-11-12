"""Agent tools: a typed, local, deterministic tool registry."""

from __future__ import annotations

from app.agent.tools.base import Tool, ToolRegistry, ToolResult
from app.agent.tools.glossary import GlossaryLookupTool
from app.agent.tools.label import LabelSectionLookupTool
from app.agent.tools.threshold import ThresholdCheckTool
from app.schemas.domain import Chunk, GlossaryEntry


def build_tool_registry(chunks: list[Chunk], glossary: list[GlossaryEntry]) -> ToolRegistry:
    """Build the default allowlist of local tools."""
    registry = ToolRegistry()
    registry.register(GlossaryLookupTool(glossary))
    registry.register(LabelSectionLookupTool(chunks))
    registry.register(ThresholdCheckTool(chunks))
    return registry


__all__ = [
    "GlossaryLookupTool",
    "LabelSectionLookupTool",
    "ThresholdCheckTool",
    "Tool",
    "ToolRegistry",
    "ToolResult",
    "build_tool_registry",
]
