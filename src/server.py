"""Prompt Library — npm for AI agent prompts and configs."""

from mcp.server.fastmcp import FastMCP
from src.tools.prompt_tools import register_prompt_tools

mcp = FastMCP(
    "Prompt Library",
    instructions=(
        "Community-driven library of tested prompts and tool configurations. "
        "Share, discover, and rate prompts that work. Like npm, but for "
        "AI agent configs and prompt templates."
    ),
)

register_prompt_tools(mcp)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
