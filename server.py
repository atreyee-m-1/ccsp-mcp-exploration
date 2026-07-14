"""
CCSP MCP Server — Exposes cell line screening data (and related lookups) to Claude.

This is the composition root: each data domain lives in its own package under
ccsp_mcp/ and registers its own tools via a register(mcp) function.
"""

from mcp.server.fastmcp import FastMCP

from ccsp_mcp.chembl import tools as chembl_tools
from ccsp_mcp.screening import tools as screening_tools

mcp = FastMCP(
    "CCSP Cell Line Screening",
    instructions="\n\n".join([screening_tools.INSTRUCTIONS, chembl_tools.INSTRUCTIONS]),
)

screening_tools.register(mcp)
chembl_tools.register(mcp)

if __name__ == "__main__":
    mcp.run(transport="stdio")
