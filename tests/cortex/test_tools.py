"""Tests for tools module."""

import pytest
from traylinx.cortex.tools import TOOL_DEFINITIONS, get_tool_schema, ToolExecutor
from traylinx.cortex.tools.definitions import tool_name_to_command, get_tool_by_name
from traylinx.cortex.tools.executor import ToolCall, ToolChain, parse_chained_command


class TestToolDefinitions:
    """Tests for OpenAI-style tool definitions."""

    def test_tool_count(self):
        """Should have 12 tool definitions."""
        assert len(TOOL_DEFINITIONS) == 12

    def test_tool_format(self):
        """Tools should have correct structure."""
        for tool in TOOL_DEFINITIONS:
            assert tool["type"] == "function"
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]

    def test_get_tool_schema(self):
        """get_tool_schema should return all tools."""
        schema = get_tool_schema()
        assert len(schema) == 12

    def test_get_tool_by_name(self):
        """Should find specific tool by name."""
        tool = get_tool_by_name("traylinx_run")
        assert tool is not None
        assert tool["function"]["name"] == "traylinx_run"

        tool = get_tool_by_name("nonexistent")
        assert tool is None

    def test_tool_name_mapping(self):
        """Tool names should map to CLI commands."""
        assert tool_name_to_command("traylinx_run") == "run"
        assert tool_name_to_command("traylinx_stop") == "stop"
        assert tool_name_to_command("traylinx_logs") == "logs"
        assert tool_name_to_command("traylinx_discover") == "discover"
        assert tool_name_to_command("unknown") is None


class TestToolCall:
    """Tests for ToolCall parsing and validation."""

    def test_create_tool_call(self):
        """Can create a ToolCall."""
        call = ToolCall(
            id="call_123",
            name="traylinx_run",
            arguments={"agent_name": "test"},
        )
        assert call.id == "call_123"
        assert call.name == "traylinx_run"
        assert call.arguments["agent_name"] == "test"


class TestToolChain:
    """Tests for tool chaining."""

    def test_add_tool(self):
        """Can add tools to chain."""
        chain = ToolChain()
        call = ToolCall(id="1", name="traylinx_run", arguments={})
        chain.add(call)
        assert len(chain.calls) == 1

    def test_chain_iteration(self):
        """Can iterate through chain."""
        chain = ToolChain()
        chain.add(ToolCall(id="1", name="traylinx_run", arguments={}))
        chain.add(ToolCall(id="2", name="traylinx_logs", arguments={}))

        first = chain.next()
        assert first.name == "traylinx_run"
        assert not chain.is_complete()

        second = chain.next()
        assert second.name == "traylinx_logs"
        assert chain.is_complete()

    def test_parse_chained_command(self):
        """Parse natural language chain."""
        commands = parse_chained_command("start my agent and show logs")
        assert commands == ["run", "logs"]

        commands = parse_chained_command("stop it then start again")
        assert commands == ["stop", "run"]

        commands = parse_chained_command("build and run")
        assert commands == ["build", "run"]


class TestToolExecutor:
    """Tests for tool execution."""

    def test_validate_tool_call(self):
        """Validation should catch missing params."""
        executor = ToolExecutor(command_executor=None)

        # Valid call - stop requires agent_name
        call = ToolCall(id="1", name="traylinx_stop", arguments={"agent_name": "test"})
        valid, error = executor.validate_tool_call(call)
        assert valid

        # Invalid - missing required param
        call = ToolCall(id="2", name="traylinx_stop", arguments={})
        valid, error = executor.validate_tool_call(call)
        assert not valid
        assert "agent_name" in error

    def test_unknown_tool(self):
        """Unknown tool should fail validation."""
        executor = ToolExecutor(command_executor=None)
        call = ToolCall(id="1", name="unknown_tool", arguments={})
        valid, error = executor.validate_tool_call(call)
        assert not valid
        assert "Unknown" in error

    def test_to_intent(self):
        """Tool call should convert to Intent."""
        executor = ToolExecutor(command_executor=None)
        call = ToolCall(
            id="1",
            name="traylinx_run",
            arguments={"agent_name": "test"},
        )
        intent = executor.to_intent(call)
        assert intent.command == "run"
        assert intent.parameters["agent_name"] == "test"
        assert intent.confidence == 1.0
