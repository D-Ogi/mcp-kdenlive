"""Entry point for MCP server — adds sibling repos to sys.path."""

import sys
from pathlib import Path

workspace = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace / "mcp-kdenlive"))
sys.path.insert(0, str(workspace / "kdenlive-api"))

from mcp_kdenlive.server import main

main()
