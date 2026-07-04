"""
SentinelAI MCP Server
======================
Exposes the Cybersecurity Agent's PII / injection-detection capability as a
standalone MCP tool, callable by any MCP-compatible client (e.g. Claude,
other agent frameworks).

This file is fully additive: it does not modify agents.py, file_processor.py,
workflow.py, or server.py. It imports the existing, already-tested functions
directly and runs as an independent process over stdio transport.

Run standalone with:
    python mcp_server.py
"""
from __future__ import annotations

import asyncio
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from file_processor import parse_csv
from agents import cybersecurity_agent

server = Server("sentinelai-mcp")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Advertise the tools this MCP server exposes."""
    return [
        Tool(
            name="analyze_cybersecurity_risks",
            description=(
                "Scans a CSV financial dataset for PII exposure (SSNs, credit "
                "cards, emails, phone numbers) and prompt-injection / SQL-injection "
                "patterns. Returns structured findings, a risk score, and a summary."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "csv_content": {
                        "type": "string",
                        "description": "Raw CSV file content as a UTF-8 string.",
                    }
                },
                "required": ["csv_content"],
            },
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Dispatch incoming tool calls to the appropriate handler."""
    if name != "analyze_cybersecurity_risks":
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    csv_content = arguments.get("csv_content", "")
    if not csv_content:
        return [TextContent(type="text", text='{"ok": false, "error": "csv_content is required"}')]

    parsed = parse_csv(csv_content.encode("utf-8"))

    if not parsed.get("ok"):
        return [TextContent(type="text", text=f'{{"ok": false, "error": "{parsed.get("error", "parse failed")}"}}')]

    ctx = {"dataframe": parsed["dataframe"]}
    result = await cybersecurity_agent(ctx)

    import json
    return [TextContent(type="text", text=json.dumps(result, default=str))]


async def main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
