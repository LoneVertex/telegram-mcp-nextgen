"""Tests verifying Glama compatibility and TDQS schema enrichment."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from telegram_mcp import runner
from telegram_mcp.core.schema_enricher import enrich_all_tools
from telegram_mcp.runtime import mcp


def test_glama_json_file_is_valid():
    repo_root = Path(__file__).parent.parent
    glama_path = repo_root / "glama.json"
    assert glama_path.is_file(), "glama.json must exist in repository root"

    data = json.loads(glama_path.read_text(encoding="utf-8"))
    assert "$schema" in data
    assert data["$schema"] == "https://glama.ai/mcp/schemas/server.json"
    assert "maintainers" in data
    assert "LoneVertex" in data["maintainers"]


def test_readme_contains_glama_badges():
    repo_root = Path(__file__).parent.parent
    readme_path = repo_root / "README.md"
    content = readme_path.read_text(encoding="utf-8")
    assert "https://glama.ai/mcp/servers/LoneVertex/telegram-mcp-nextgen" in content


@pytest.mark.asyncio
async def test_schema_enricher_achieves_100_percent_coverage():
    count = enrich_all_tools(mcp)
    assert count == 128

    tools = await mcp.list_tools()
    assert len(tools) == 128

    missing_desc = []
    short_titles = []

    for tool in tools:
        # Title must be meaningful (longer than name)
        title = tool.title or (tool.annotations.title if tool.annotations else None)
        assert title, f"Tool {tool.name} must have title"
        if len(title) <= len(tool.name):
            short_titles.append((tool.name, title))

        # Every parameter must have a description
        props = tool.inputSchema.get("properties", {})
        for param_name, param_schema in props.items():
            desc = param_schema.get("description")
            if not desc or not desc.strip():
                missing_desc.append((tool.name, param_name))

    assert not short_titles, f"Tools with titles not longer than name: {short_titles}"
    assert not missing_desc, f"Parameters missing descriptions: {missing_desc}"


@pytest.mark.asyncio
async def test_offline_inspection_mode_serves_without_clients(monkeypatch):
    class _FakeMcp:
        def __init__(self):
            self.ran = None

        async def run_stdio_async(self):
            self.ran = "stdio"

        async def run_streamable_http_async(self):
            self.ran = "http"

    fake_mcp = _FakeMcp()
    monkeypatch.setattr(runner, "clients", {})
    monkeypatch.setattr(runner, "mcp", fake_mcp)
    monkeypatch.setenv("MCP_TRANSPORT", "stdio")

    # Should not raise RuntimeError when clients is empty
    await runner._main()
    assert fake_mcp.ran == "stdio"


def test_schema_enricher_fallbacks():
    class _FakeTool:
        def __init__(self, name, props):
            self.name = name
            self.title = None
            self.description = "Old"
            self.annotations = None
            self.parameters = {"properties": props}

    class _FakeToolManager:
        def __init__(self, tools):
            self._tools = tools

        def list_tools(self):
            return self._tools

    class _FakeServer:
        def __init__(self, tools):
            self._tool_manager = _FakeToolManager(tools)

    tool = _FakeTool("custom_test_tool", {"unknown_param": {}, "limit": {}})
    server = _FakeServer([tool])

    enrich_all_tools(server)
    assert tool.title == "Custom Test Tool Details"
    assert (
        tool.parameters["properties"]["unknown_param"]["description"]
        == "Parameter 'unknown_param' for Custom Test Tool Details."
    )
    assert "Maximum number" in tool.parameters["properties"]["limit"]["description"]

    # Short name fallback
    short_tool = _FakeTool("a", {})
    server2 = _FakeServer([short_tool])
    enrich_all_tools(server2)
    assert short_tool.title == "A Details"
