# CCSP MCP Server — Exploration

An MCP (Model Context Protocol) server that exposes CCSP-like cell line screening data to Claude. Computational biologists can ask Claude natural-language questions about compound sensitivity and get plots/analysis directly.

> **Note:** This repo contains only code — `sample_data/` (real or synthetic) is gitignored and never committed. Generate synthetic sample data locally with `generate_sample_data.py`, or point `CCSP_DATA_FILE`/`CCSP_DATA_DIR` at real data on your own machine.

## Quick Start

```bash
git clone https://github.com/atreyee-m-1/ccsp-mcp-exploration.git ccsp-mcp
cd ccsp-mcp

# Install dependencies
uv sync

# Generate sample data (synthetic DepMap-like data — sample_data/ is
# gitignored, so this step is required after a fresh clone)
uv run python generate_sample_data.py

# Test the server starts
uv run python server.py
```

## Connect to Claude Code

Add this to your Claude Code MCP config (`~/.claude/settings.json` or project `.claude/settings.json`):

```json
{
  "mcpServers": {
    "ccsp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/ccsp-mcp", "python", "server.py"],
      "env": {
        "CCSP_DATA_DIR": "/path/to/your/actual/data"
      }
    }
  }
}
```

> **Note:** Replace `/path/to/ccsp-mcp` with the actual path, and set `CCSP_DATA_DIR` to your shared drive path containing the real CSV matrices. If omitted, it defaults to the `sample_data/` directory in this project — run `generate_sample_data.py` first if that directory doesn't exist yet (it's gitignored).

### Loading a single real data file (CSV/TSV)

For a single real-data export (e.g. a CCSP pipeline TSV) rather than the multi-file synthetic format, set `CCSP_DATA_FILE` instead of `CCSP_DATA_DIR`:

```json
{
  "mcpServers": {
    "ccsp": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/ccsp-mcp", "python", "server.py"],
      "env": {
        "CCSP_DATA_FILE": "/path/to/pipeline_summary_GR_allpts.tsv"
      }
    }
  }
}
```

The loader auto-detects `.tsv` vs `.csv` and normalizes `cmpd`/`Compound name` columns to `compound_code`/`compound`. If the file has no `lineage` column (typical for real exports), `list_available_data` reports this and the server falls back to cell-line-level comparison tools instead of lineage-level ones.

### External calls (ChEMBL lookups)

The `chembl_lookup_compound_mechanism` tool calls the public, unauthenticated
[ChEMBL REST API](https://www.ebi.ac.uk/chembl/api/data/docs) at
`ebi.ac.uk`. The only thing sent externally is a public ChEMBL compound ID
(e.g. `CHEMBL3545376`) — no proprietary screening data, compound structures,
or internal identifiers leave the machine. Flag this to your InfoSec
reviewer as a new category vs. the rest of this POC: an outbound call to a
third-party service, not just to Anthropic.

## Available Tools

### Screening domain (`ccsp_mcp/screening/`)

| Tool | What it does |
|------|--------------|
| `list_available_data` | Show all compounds, lineages (if present), metrics available |
| `query_data` | Filter data by compound/lineage/cell_line |
| `compare_compound_across_lineages` | "Which lineage responds best to compound X?" (requires lineage data) |
| `compare_compounds_in_lineage` | "Which compound works best for lineage Y?" (requires lineage data) |
| `compare_compound_across_cell_lines` | "Which cell lines respond best to compound X?" (works without lineage data) |
| `compare_compounds_for_cell_line` | "Which compound works best for this cell line?" (works without lineage data) |
| `get_summary_statistics` | Descriptive stats for a data slice |
| `get_raw_data_for_plot` | Get CSV data formatted for direct use in matplotlib/seaborn |
| `generate_boxplot` | Renders an actual box plot PNG server-side and returns it as an image — use this to see a plot in Claude Desktop, since Desktop can't execute matplotlib code itself |
| `get_compound_registration_info` | Look up a compound's ChEMBL ID, LSN, target/project, molecular weight, description (real CCSP export only) |

### ChEMBL domain (`ccsp_mcp/chembl/`)

| Tool | What it does |
|------|--------------|
| `chembl_lookup_compound_mechanism` | Look up a compound's mechanism of action and target from the public ChEMBL database. Resolves the ChEMBL ID automatically from a compound name in the loaded screening data, or accepts one directly. Only a public ChEMBL ID is sent externally — no proprietary data leaves the machine. No API key or extra config needed. |

## Example Prompts

Once connected, comp bios can ask Claude things like:

- "Show me a box plot of AUC for Erlotinib across all lineages"
- "Which compound is most effective against Melanoma?"
- "Compare Venetoclax sensitivity — is it more effective in Leukemia or Lymphoma?"
- "Give me summary stats for all Lilly compounds (LY-*) in Breast cancer lines"
- "Make a heatmap of median AUC for all compounds across all lineages"
- "What's the mechanism of action for Erdafitinib, and what's its target?"

Claude will call the appropriate tool, get the data, and generate Python plotting code (or answer directly for simple questions).

## Data Format

The server expects CSV files with these columns:

### dose_response_parameters.csv (required)
```
compound,lineage,cell_line,auc,ic50_um,zc50
Erlotinib,Lung,A549,0.5234,1.2345,-1.2
...
```

### cell_line_metadata.csv (optional)
```
cell_line,lineage,primary_disease,subtype,source
```

### compound_metadata.csv (optional)
```
compound,mechanism_of_action,target,phase,source
```

## Using with Real CCSP Data

1. Export your CCSP matrices as CSV with the column format above
2. Place them in a directory accessible from your machine
3. Set `CCSP_DATA_DIR` environment variable to that path
4. Restart Claude Code — it will auto-discover the files

## Architecture

The server hosts multiple data domains in one MCP process. Each domain is a
self-contained Python package under `ccsp_mcp/` with its own data access and
tools, registered onto a shared `FastMCP` instance from the `server.py`
composition root:

```
server.py                    # composition root: creates FastMCP, calls register(mcp) per domain
ccsp_mcp/
├── screening/                # dose-response screening data (compound × cell_line × metric)
│   ├── data.py               #   loading/caching (CCSP_DATA_FILE / CCSP_DATA_DIR)
│   ├── plotting.py           #   matplotlib box-plot rendering
│   └── tools.py               #   @mcp.tool functions, unprefixed (list_available_data, query_data, ...)
└── chembl/                   # public ChEMBL compound/target lookups
    ├── client.py              #   thin httpx wrapper around the ChEMBL REST API
    └── tools.py               #   @mcp.tool functions, prefixed chembl_*
```

```
Shared Drive (CSV/TSV) ──────────┐
                                  ▼
                        ┌──────────────────────┐
                        │  MCP Server (Python)  │
                        │  screening domain      │  ← reads CSVs, exposes query/plot tools
                        │  chembl domain          │  ← public REST lookups (no proprietary data sent)
                        └──────────────────────┘
                                  │  (stdio transport)
                                  ▼
                        ┌──────────────────────┐
                        │  Claude Desktop/Code  │  ← natural language interface
                        └──────────────────────┘
                                  │
                                  ▼
                          Plots / Analysis
```

### Adding a new data domain

There's only one MCP server process — new data types don't need a new
Desktop config entry, just a new package:

1. Create `ccsp_mcp/<domain>/` with a `data.py` (or `client.py` for an
   external source) and a `tools.py` exposing a `register(mcp)` function.
2. Prefix new tool names with `<domain>_` (e.g. `genomics_query_mutations`)
   to avoid colliding with the unprefixed screening tools or other domains.
3. Optionally expose an `INSTRUCTIONS` string constant in `tools.py`
   describing when Claude should reach for this domain's tools.
4. In `server.py`, import the domain's `tools` module, add its
   `INSTRUCTIONS` to the joined instructions string, and call
   `<domain>_tools.register(mcp)`.

No changes to `claude_desktop_config.json` are needed unless the new domain
requires its own environment variables (API keys, data paths, etc.).
