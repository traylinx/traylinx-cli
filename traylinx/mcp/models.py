"""Pydantic models for MCP integration.

Defines type-safe models for MCP tools, results, and server configuration.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RemoteTool(BaseModel):
    """Represents an MCP tool available from a server."""

    model_config = ConfigDict(from_attributes=True)

    name: str
    """Tool name."""

    description: str | None = None
    """Human-readable description."""

    input_schema: dict[str, Any] = Field(
        default_factory=lambda: {"type": "object", "properties": {}},
        validation_alias="inputSchema",
    )
    """JSON Schema for tool arguments."""

    server_name: str = ""
    """Name of the server providing this tool."""

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is non-empty."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Tool name must be a non-empty string")
        return v.strip()

    @field_validator("input_schema", mode="before")
    @classmethod
    def normalize_schema(cls, v: Any) -> dict[str, Any]:
        """Normalize input schema to dict."""
        if v is None:
            return {"type": "object", "properties": {}}
        if isinstance(v, dict):
            return v
        # Handle MCP SDK objects
        if hasattr(v, "model_dump"):
            try:
                return v.model_dump()
            except Exception:
                pass
        return {"type": "object", "properties": {}}


class ToolResult(BaseModel):
    """Result from calling an MCP tool."""

    ok: bool = True
    """Whether the call succeeded."""

    server: str
    """Server that handled the call."""

    tool: str
    """Tool that was called."""

    text: str | None = None
    """Text content from the result."""

    data: dict[str, Any] | None = None
    """Structured data from the result."""

    error: str | None = None
    """Error message if call failed."""

    @property
    def content(self) -> str:
        """Get text or formatted data content."""
        if self.text:
            return self.text
        if self.data:
            import json
            return json.dumps(self.data, indent=2)
        if self.error:
            return f"Error: {self.error}"
        return "(no content)"


class ServerConfig(BaseModel):
    """Configuration for an MCP server."""

    model_config = ConfigDict(extra="ignore")

    name: str
    """Unique server identifier."""

    transport: str = "stdio"
    """Transport type: 'stdio' or 'http'"""

    # For stdio transport
    command: list[str] | None = None
    """Command and arguments to start stdio server."""

    env: dict[str, str] = Field(default_factory=dict)
    """Environment variables for stdio server."""

    # For HTTP transport
    url: str | None = None
    """URL for HTTP server."""

    headers: dict[str, str] = Field(default_factory=dict)
    """HTTP headers for authentication."""

    # Metadata
    enabled: bool = True
    """Whether server is enabled."""

    description: str | None = None
    """Optional description."""

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure name is valid identifier."""
        if not isinstance(v, str) or not v.strip():
            raise ValueError("Server name must be a non-empty string")
        # Allow alphanumeric, dash, underscore
        import re
        if not re.match(r"^[a-zA-Z0-9_-]+$", v):
            raise ValueError("Server name must contain only alphanumeric, dash, or underscore")
        return v.strip()

    @field_validator("transport")
    @classmethod
    def validate_transport(cls, v: str) -> str:
        """Ensure transport is valid."""
        valid = {"stdio", "http", "streamable-http"}
        if v not in valid:
            raise ValueError(f"Transport must be one of: {', '.join(valid)}")
        return v

    def validate_config(self) -> list[str]:
        """Validate configuration is complete.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if self.transport == "stdio":
            if not self.command:
                errors.append("stdio transport requires 'command'")
        elif self.transport in ("http", "streamable-http"):
            if not self.url:
                errors.append("http transport requires 'url'")

        return errors


class MCPContentBlock(BaseModel):
    """Content block from MCP response."""

    model_config = ConfigDict(from_attributes=True)

    type: str = "text"
    text: str | None = None
    data: dict[str, Any] | None = None


class MCPCallResult(BaseModel):
    """Raw result from MCP SDK call."""

    model_config = ConfigDict(from_attributes=True)

    isError: bool = False
    content: list[MCPContentBlock] = Field(default_factory=list)
    structuredContent: dict[str, Any] | None = None

    @field_validator("content", mode="before")
    @classmethod
    def normalize_content(cls, v: Any) -> list[MCPContentBlock]:
        """Normalize content to list of blocks."""
        if v is None:
            return []
        if isinstance(v, list):
            return [
                MCPContentBlock.model_validate(item) if isinstance(item, dict)
                else MCPContentBlock(text=str(item))
                for item in v
            ]
        return []

    def to_tool_result(self, server: str, tool: str) -> ToolResult:
        """Convert to ToolResult."""
        if self.isError:
            error_text = "\n".join(
                b.text for b in self.content if b.text
            ) or "Unknown error"
            return ToolResult(
                ok=False,
                server=server,
                tool=tool,
                error=error_text,
            )

        # Extract text content
        text_parts = [b.text for b in self.content if b.text]
        text = "\n".join(text_parts) if text_parts else None

        return ToolResult(
            ok=True,
            server=server,
            tool=tool,
            text=text,
            data=self.structuredContent,
        )
