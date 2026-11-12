"""Tool abstractions: a typed allowlist registry and structured results."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from app.providers.protocols import ToolSpec


class ToolResult(BaseModel):
    """A completed tool execution: either a typed result or a structured error."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tool_result_id: str
    tool: str
    arguments: dict[str, Any]
    status: Literal["ok", "error"]
    output: dict[str, Any] | None = None
    error: str | None = None


class Tool(ABC):
    """A local, deterministic, side-effect-free tool with typed args/result."""

    name: ClassVar[str]
    description: ClassVar[str]
    args_model: ClassVar[type[BaseModel]]

    @abstractmethod
    async def run(self, args: BaseModel) -> BaseModel: ...

    def to_spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            parameters=self.args_model.model_json_schema(),
        )


class ToolRegistry:
    """Allowlist of tools; executes calls with a timeout and error capture."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def specs(self) -> list[ToolSpec]:
        return [tool.to_spec() for tool in self._tools.values()]

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        tool_result_id: str,
        timeout: float,
    ) -> ToolResult:
        tool = self._tools.get(name)
        if tool is None:
            return ToolResult(
                tool_result_id=tool_result_id,
                tool=name,
                arguments=arguments,
                status="error",
                error=f"unknown tool: {name}",
            )
        try:
            args = tool.args_model.model_validate(arguments)
        except ValidationError as exc:
            return ToolResult(
                tool_result_id=tool_result_id,
                tool=name,
                arguments=arguments,
                status="error",
                error=f"invalid arguments: {exc}",
            )
        try:
            result = await asyncio.wait_for(tool.run(args), timeout)
        except TimeoutError:
            return ToolResult(
                tool_result_id=tool_result_id,
                tool=name,
                arguments=arguments,
                status="error",
                error="tool timed out",
            )
        except Exception as exc:  # noqa: BLE001 - tools report errors as results
            return ToolResult(
                tool_result_id=tool_result_id,
                tool=name,
                arguments=arguments,
                status="error",
                error=f"tool error: {exc}",
            )
        return ToolResult(
            tool_result_id=tool_result_id,
            tool=name,
            arguments=arguments,
            status="ok",
            output=result.model_dump(),
        )
