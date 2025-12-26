"""Tests for the MCP module."""

import json
from pathlib import Path
import pytest

from traylinx.mcp.models import RemoteTool, ToolResult, ServerConfig, MCPCallResult
from traylinx.mcp.registry import (
    MCP_CONFIG_FILE,
    list_servers,
    add_server,
    remove_server,
    get_server,
)


class TestRemoteTool:
    """Tests for RemoteTool model."""

    def test_basic_tool(self):
        """Test creating a basic tool."""
        tool = RemoteTool(name="test_tool", description="A test tool")
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"

    def test_tool_with_schema(self):
        """Test tool with input schema."""
        schema = {
            "type": "object",
            "properties": {"city": {"type": "string"}},
        }
        # Use inputSchema alias like MCP SDK does
        tool = RemoteTool.model_validate({
            "name": "weather",
            "inputSchema": schema,
        })
        assert tool.input_schema["properties"]["city"]["type"] == "string"

    def test_empty_name_rejected(self):
        """Test that empty name is rejected."""
        with pytest.raises(ValueError):
            RemoteTool(name="", description="test")

    def test_input_schema_alias(self):
        """Test inputSchema alias works."""
        tool = RemoteTool.model_validate({
            "name": "test",
            "inputSchema": {"type": "object"},
        })
        assert tool.input_schema["type"] == "object"


class TestToolResult:
    """Tests for ToolResult model."""

    def test_successful_result(self):
        """Test a successful result."""
        result = ToolResult(
            ok=True,
            server="test-server",
            tool="test-tool",
            text="Hello, world!",
        )
        assert result.ok
        assert result.content == "Hello, world!"

    def test_error_result(self):
        """Test an error result."""
        result = ToolResult(
            ok=False,
            server="test-server",
            tool="test-tool",
            error="Connection failed",
        )
        assert not result.ok
        assert "Connection failed" in result.content

    def test_data_result(self):
        """Test result with structured data."""
        result = ToolResult(
            ok=True,
            server="test",
            tool="test",
            data={"key": "value"},
        )
        assert "key" in result.content


class TestServerConfig:
    """Tests for ServerConfig model."""

    def test_stdio_config(self):
        """Test stdio server config."""
        config = ServerConfig(
            name="test-stdio",
            transport="stdio",
            command=["python", "-m", "myserver"],
        )
        assert config.name == "test-stdio"
        assert config.transport == "stdio"
        assert len(config.command) == 3

    def test_http_config(self):
        """Test HTTP server config."""
        config = ServerConfig(
            name="test-http",
            transport="http",
            url="http://localhost:8000/mcp",
        )
        assert config.transport == "http"
        assert config.url == "http://localhost:8000/mcp"

    def test_invalid_name_rejected(self):
        """Test that invalid names are rejected."""
        with pytest.raises(ValueError):
            ServerConfig(name="has spaces", transport="stdio")

    def test_invalid_transport_rejected(self):
        """Test that invalid transport is rejected."""
        with pytest.raises(ValueError):
            ServerConfig(name="test", transport="invalid")

    def test_validate_config_stdio(self):
        """Test validation for stdio config."""
        config = ServerConfig(name="test", transport="stdio")
        errors = config.validate_config()
        assert "command" in errors[0]

    def test_validate_config_http(self):
        """Test validation for http config."""
        config = ServerConfig(name="test", transport="http")
        errors = config.validate_config()
        assert "url" in errors[0]


class TestMCPCallResult:
    """Tests for MCPCallResult model."""

    def test_successful_result(self):
        """Test parsing successful result."""
        raw = {
            "isError": False,
            "content": [{"type": "text", "text": "Hello"}],
        }
        parsed = MCPCallResult.model_validate(raw)
        result = parsed.to_tool_result("srv", "tool")
        assert result.ok
        assert result.text == "Hello"

    def test_error_result(self):
        """Test parsing error result."""
        raw = {
            "isError": True,
            "content": [{"text": "Something went wrong"}],
        }
        parsed = MCPCallResult.model_validate(raw)
        result = parsed.to_tool_result("srv", "tool")
        assert not result.ok
        assert "Something went wrong" in result.error


class TestRegistry:
    """Tests for MCP registry."""

    @pytest.fixture(autouse=True)
    def setup_temp_config(self, tmp_path, monkeypatch):
        """Use temporary config file for tests."""
        temp_config = tmp_path / "mcp-servers.json"
        import traylinx.mcp.registry as reg
        monkeypatch.setattr(reg, "MCP_CONFIG_FILE", temp_config)

    def test_list_empty(self):
        """Test listing when no servers configured."""
        servers = list_servers()
        assert servers == []

    def test_add_and_get_server(self):
        """Test adding and retrieving a server."""
        config = ServerConfig(
            name="test-server",
            transport="http",
            url="http://localhost:8000",
        )
        add_server(config)

        retrieved = get_server("test-server")
        assert retrieved is not None
        assert retrieved.name == "test-server"
        assert retrieved.url == "http://localhost:8000"

    def test_remove_server(self):
        """Test removing a server."""
        config = ServerConfig(
            name="to-remove",
            transport="stdio",
            command=["python", "-m", "server"],
        )
        add_server(config)
        assert get_server("to-remove") is not None

        result = remove_server("to-remove")
        assert result is True
        assert get_server("to-remove") is None

    def test_remove_nonexistent(self):
        """Test removing non-existent server."""
        result = remove_server("does-not-exist")
        assert result is False

    def test_update_existing_server(self):
        """Test updating an existing server."""
        config1 = ServerConfig(
            name="update-test",
            transport="http",
            url="http://old.url",
        )
        add_server(config1)

        config2 = ServerConfig(
            name="update-test",
            transport="http",
            url="http://new.url",
        )
        add_server(config2)

        retrieved = get_server("update-test")
        assert retrieved.url == "http://new.url"


class TestModuleImports:
    """Tests for module imports."""

    def test_mcp_module_imports(self):
        """Test that MCP module can be imported."""
        from traylinx.mcp import (
            MCPClient,
            RemoteTool,
            ToolResult,
            ServerConfig,
            list_servers,
            add_server,
        )

        assert MCPClient is not None
        assert RemoteTool is not None
        assert ToolResult is not None
        assert ServerConfig is not None
        assert list_servers is not None
        assert add_server is not None
