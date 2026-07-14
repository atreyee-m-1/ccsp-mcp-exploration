"""MCP tools for the CCSP dose-response screening domain."""

import pandas as pd
from mcp.server.fastmcp import Image

from . import data as _data
from .plotting import render_boxplot

INSTRUCTIONS = (
    "You have access to cancer cell line screening data (similar to DepMap/PRISM). "
    "The data contains dose-response metrics (AUC, IC50, ZC50) for compounds "
    "tested across cancer cell lines, sometimes grouped by lineage. "
    "Call list_available_data first to see whether lineage annotations exist for the "
    "loaded dataset, then use the lineage-based or cell-line-based comparison tools "
    "accordingly. Use generate_boxplot to render an actual plot image."
)

# Compound-level registration/metadata columns present on the real CCSP export
# (absent from the synthetic sample_data/ schema).
_REGISTRATION_COLUMNS = [
    "compound_code",
    "ChEMBL ID",
    "LSN (numbers only)",
    "TARGET / PROJECT / PROGRAM",
    "Compound molecular weight (Da)",
    "Compound description",
]


def register(mcp) -> None:
    """Register all screening-domain tools on the given FastMCP instance."""

    @mcp.tool()
    def list_available_data() -> str:
        """List all available datasets, compounds, lineages, and metrics in the CCSP data directory."""
        df = _data.load_data()
        compounds = sorted(df["compound"].unique().tolist())
        metrics = [
            col
            for col in df.columns
            if col not in ("compound", "compound_code", "lineage", "cell_line")
        ]
        n_cell_lines = df["cell_line"].nunique()

        lines = [
            "## Available CCSP Data\n",
            f"**Data source:** {_data.DATA_FILE or _data.DATA_DIR}",
            f"**Total records:** {len(df):,}",
            f"**Cell lines:** {n_cell_lines}",
            f"**Compounds ({len(compounds)}):** {', '.join(compounds)}\n",
        ]

        if _data.has_lineage():
            lineages = sorted(df["lineage"].unique().tolist())
            lines.append(f"**Lineages ({len(lineages)}):** {', '.join(lineages)}\n")
        else:
            lines.append(
                "**Lineages:** not available in this dataset — use "
                "`compare_compound_across_cell_lines` / `compare_compounds_for_cell_line` "
                "instead of the lineage-based comparison tools.\n"
            )

        lines.append(f"**Metrics:** {', '.join(metrics)}\n")
        lines.append(
            "### Metric Definitions\n"
            "- **auc**: Area Under the dose-response Curve (lower = more sensitive)\n"
            "- **ic50_um / ic50_abs**: IC50 concentration (lower = more potent)\n"
            "- **zc50**: Z-score normalized IC50 (more negative = more sensitive)"
        )
        return "\n".join(lines)

    @mcp.tool()
    def query_data(
        compound: str | None = None,
        lineage: str | None = None,
        cell_line: str | None = None,
        metric: str = "auc",
        limit: int = 50,
    ) -> str:
        """
        Query the dose-response data with optional filters.

        Args:
            compound: Filter by compound name (case-insensitive, partial match)
            lineage: Filter by cancer lineage (case-insensitive, partial match). Ignored if the loaded dataset has no lineage column.
            cell_line: Filter by cell line name (case-insensitive, partial match)
            metric: Which metric to focus on (auc, ic50_um, zc50)
            limit: Maximum rows to return (default 50)
        """
        df = _data.load_data()

        if compound:
            df = df[df["compound"].str.contains(compound, case=False, na=False)]
        if lineage and _data.has_lineage():
            df = df[df["lineage"].str.contains(lineage, case=False, na=False)]
        if cell_line:
            df = df[df["cell_line"].str.contains(cell_line, case=False, na=False)]

        if df.empty:
            return "No data found matching the specified filters."

        if metric in df.columns:
            df = df.sort_values(metric, ascending=True)

        result = df.head(limit).to_string(index=False)
        return f"**Results** ({len(df)} total rows, showing top {min(limit, len(df))} by {metric}):\n\n```\n{result}\n```"

    @mcp.tool()
    def compare_compound_across_lineages(compound: str, metric: str = "auc") -> str:
        """
        Compare a single compound's sensitivity across all cancer lineages.
        Use this to answer: "Which lineage is compound X most effective against?"

        Args:
            compound: The compound name to compare
            metric: Metric to compare (auc, ic50_um, zc50). Lower AUC/IC50 = more sensitive.
        """
        if not _data.has_lineage():
            return (
                "This dataset has no cancer-lineage annotations. "
                "Use `compare_compound_across_cell_lines` instead to compare a compound across cell lines."
            )

        df = _data.load_data()
        mask = df["compound"].str.contains(compound, case=False, na=False)
        df_filtered = df[mask]

        if df_filtered.empty:
            return f"No data found for compound '{compound}'."

        actual_compound = df_filtered["compound"].iloc[0]

        summary = (
            df_filtered.groupby("lineage")[metric]
            .agg(["median", "mean", "std", "count"])
            .round(4)
            .sort_values("median", ascending=True)
        )

        result = summary.to_string()
        return (
            f"## {actual_compound} — {metric.upper()} by Lineage\n\n"
            f"Sorted by median (ascending = most sensitive):\n\n"
            f"```\n{result}\n```\n\n"
            f"**Most sensitive lineage:** {summary.index[0]} (median {metric} = {summary['median'].iloc[0]:.4f})\n"
            f"**Least sensitive lineage:** {summary.index[-1]} (median {metric} = {summary['median'].iloc[-1]:.4f})\n\n"
            f"💡 Use this data to generate a box plot with lineages on the x-axis and {metric} on the y-axis."
        )

    @mcp.tool()
    def compare_compounds_in_lineage(lineage: str, metric: str = "auc") -> str:
        """
        Compare multiple compounds within a single cancer lineage.
        Use this to answer: "Which compound works best for this cancer type?"

        Args:
            lineage: The cancer lineage to analyze
            metric: Metric to compare (auc, ic50_um, zc50). Lower AUC/IC50 = more sensitive.
        """
        if not _data.has_lineage():
            return (
                "This dataset has no cancer-lineage annotations. "
                "Use `compare_compounds_for_cell_line` instead to compare compounds for a specific cell line."
            )

        df = _data.load_data()
        mask = df["lineage"].str.contains(lineage, case=False, na=False)
        df_filtered = df[mask]

        if df_filtered.empty:
            return f"No data found for lineage '{lineage}'."

        actual_lineage = df_filtered["lineage"].iloc[0]

        summary = (
            df_filtered.groupby("compound")[metric]
            .agg(["median", "mean", "std", "count"])
            .round(4)
            .sort_values("median", ascending=True)
        )

        result = summary.to_string()
        return (
            f"## {actual_lineage} — {metric.upper()} by Compound\n\n"
            f"Sorted by median (ascending = most effective):\n\n"
            f"```\n{result}\n```\n\n"
            f"**Most effective compound:** {summary.index[0]} (median {metric} = {summary['median'].iloc[0]:.4f})\n"
            f"**Least effective compound:** {summary.index[-1]} (median {metric} = {summary['median'].iloc[-1]:.4f})\n\n"
            f"💡 Use this data to generate a box plot with compounds on the x-axis and {metric} on the y-axis."
        )

    @mcp.tool()
    def get_summary_statistics(
        compound: str | None = None,
        lineage: str | None = None,
        metric: str = "auc",
    ) -> str:
        """
        Get summary statistics for the specified data slice.

        Args:
            compound: Optional compound filter
            lineage: Optional lineage filter. Ignored if the loaded dataset has no lineage column.
            metric: Metric to summarize (auc, ic50_um, zc50)
        """
        df = _data.load_data()

        if compound:
            df = df[df["compound"].str.contains(compound, case=False, na=False)]
        if lineage and _data.has_lineage():
            df = df[df["lineage"].str.contains(lineage, case=False, na=False)]

        if df.empty:
            return "No data found matching filters."

        stats = df[metric].describe().round(4)
        context = []
        if compound:
            context.append(f"compound={compound}")
        if lineage and _data.has_lineage():
            context.append(f"lineage={lineage}")
        filter_str = ", ".join(context) if context else "all data"

        lines = [
            f"## Summary Statistics — {metric.upper()} ({filter_str})\n",
            f"```\n{stats.to_string()}\n```\n",
            f"**N cell lines:** {df['cell_line'].nunique()}",
            f"**N compounds:** {df['compound'].nunique()}",
        ]
        if _data.has_lineage():
            lines.append(f"**N lineages:** {df['lineage'].nunique()}")
        return "\n".join(lines)

    @mcp.tool()
    def get_raw_data_for_plot(
        compound: str | None = None,
        lineage: str | None = None,
        metric: str = "auc",
        group_by: str | None = None,
    ) -> str:
        """
        Get raw data formatted for direct use in plotting code (matplotlib/seaborn).
        Returns data as CSV text that can be loaded with pd.read_csv(StringIO(...)).

        Args:
            compound: Optional compound filter
            lineage: Optional lineage filter. Ignored if the loaded dataset has no lineage column.
            metric: Metric column to include (auc, ic50_um, zc50)
            group_by: Column to group by in the plot (lineage or compound or cell_line). Defaults to "lineage" if available, else "cell_line".
        """
        df = _data.load_data()

        if group_by is None:
            group_by = "lineage" if _data.has_lineage() else "cell_line"

        if compound:
            df = df[df["compound"].str.contains(compound, case=False, na=False)]
        if lineage and _data.has_lineage():
            df = df[df["lineage"].str.contains(lineage, case=False, na=False)]

        if df.empty:
            return "No data found matching filters."

        cols = [group_by, "cell_line", metric]
        if "compound" not in cols and compound is None:
            cols.insert(0, "compound")
        if "lineage" not in cols and lineage is None:
            cols.insert(0, "lineage")

        subset = df[[c for c in cols if c in df.columns]]
        csv_text = subset.to_csv(index=False)

        return (
            f"## Plot Data (CSV format)\n\n"
            f"Filters: compound={compound or 'all'}, lineage={lineage or 'all'}\n"
            f"Rows: {len(subset)}\n\n"
            f"```csv\n{csv_text}```\n\n"
            f"💡 Example plotting code:\n"
            f"```python\n"
            f"import pandas as pd\n"
            f"import seaborn as sns\n"
            f"import matplotlib.pyplot as plt\n"
            f"from io import StringIO\n\n"
            f"# data = pd.read_csv(StringIO(csv_text_above))\n"
            f"sns.boxplot(data=data, x='{group_by}', y='{metric}')\n"
            f"plt.xticks(rotation=45, ha='right')\n"
            f"plt.tight_layout()\n"
            f"plt.savefig('plot.png', dpi=150)\n"
            f"```"
        )

    @mcp.tool()
    def compare_compound_across_cell_lines(compound: str, metric: str = "auc", top_n: int = 20) -> str:
        """
        Compare a single compound's sensitivity across cell lines.
        Use this to answer: "Which cell lines respond best to compound X?"
        Use this instead of compare_compound_across_lineages when the dataset has no lineage annotations.

        Args:
            compound: The compound name to compare
            metric: Metric to compare (auc, ic50_abs, ...). Lower AUC/IC50 = more sensitive.
            top_n: How many of the most sensitive cell lines to show (default 20)
        """
        df = _data.load_data()
        mask = df["compound"].str.contains(compound, case=False, na=False)
        df_filtered = df[mask].dropna(subset=[metric])

        if df_filtered.empty:
            return f"No data found for compound '{compound}' with metric '{metric}'."

        actual_compound = df_filtered["compound"].iloc[0]

        summary = (
            df_filtered.groupby("cell_line")[metric]
            .agg(["median", "mean", "std", "count"])
            .round(4)
            .sort_values("median", ascending=True)
        )

        n_total = len(summary)
        shown = summary.head(top_n)
        result = shown.to_string()
        return (
            f"## {actual_compound} — {metric.upper()} by Cell Line\n\n"
            f"Showing top {min(top_n, n_total)} of {n_total} cell lines, sorted by median (ascending = most sensitive):\n\n"
            f"```\n{result}\n```\n\n"
            f"**Most sensitive cell line:** {shown.index[0]} (median {metric} = {shown['median'].iloc[0]:.4f})\n\n"
            f"💡 Use `generate_boxplot(compound=\"{actual_compound}\", metric=\"{metric}\")` to render this as a box plot."
        )

    @mcp.tool()
    def compare_compounds_for_cell_line(cell_line: str, metric: str = "auc") -> str:
        """
        Compare multiple compounds tested on a single cell line.
        Use this to answer: "Which compound works best for this cell line?"
        Use this instead of compare_compounds_in_lineage when the dataset has no lineage annotations.

        Args:
            cell_line: The cell line to analyze
            metric: Metric to compare (auc, ic50_abs, ...). Lower AUC/IC50 = more sensitive.
        """
        df = _data.load_data()
        mask = df["cell_line"].str.contains(cell_line, case=False, na=False)
        df_filtered = df[mask].dropna(subset=[metric])

        if df_filtered.empty:
            return f"No data found for cell line '{cell_line}' with metric '{metric}'."

        actual_cell_line = df_filtered["cell_line"].iloc[0]

        summary = (
            df_filtered.groupby("compound")[metric]
            .agg(["median", "mean", "std", "count"])
            .round(4)
            .sort_values("median", ascending=True)
        )

        result = summary.to_string()
        return (
            f"## {actual_cell_line} — {metric.upper()} by Compound\n\n"
            f"Sorted by median (ascending = most effective):\n\n"
            f"```\n{result}\n```\n\n"
            f"**Most effective compound:** {summary.index[0]} (median {metric} = {summary['median'].iloc[0]:.4f})\n"
            f"**Least effective compound:** {summary.index[-1]} (median {metric} = {summary['median'].iloc[-1]:.4f})\n\n"
            f"💡 Use `generate_boxplot(cell_line=\"{actual_cell_line}\", metric=\"{metric}\", group_by=\"compound\")` to render this as a box plot."
        )

    @mcp.tool()
    def generate_boxplot(
        compound: str | None = None,
        lineage: str | None = None,
        cell_line: str | None = None,
        metric: str = "auc",
        group_by: str | None = None,
        top_n: int = 20,
    ) -> Image:
        """
        Render an actual box plot image for the specified data slice and return it as a PNG.
        Use this whenever the user wants to *see* a plot (Claude Desktop cannot execute
        matplotlib code itself, so this tool renders the image server-side).

        Args:
            compound: Optional compound filter (case-insensitive, partial match)
            lineage: Optional lineage filter. Ignored if the dataset has no lineage column.
            cell_line: Optional cell line filter (case-insensitive, partial match)
            metric: Metric to plot on the y-axis (auc, ic50_abs, ic50_um, zc50, ...)
            group_by: Column for the x-axis groups (lineage, compound, or cell_line). Defaults to "lineage" if available, else "cell_line".
            top_n: Maximum number of x-axis groups to show, chosen by lowest median metric (default 20)
        """
        df = _data.load_data()

        if group_by is None:
            group_by = "lineage" if _data.has_lineage() else "cell_line"

        if compound:
            df = df[df["compound"].str.contains(compound, case=False, na=False)]
        if lineage and _data.has_lineage():
            df = df[df["lineage"].str.contains(lineage, case=False, na=False)]
        if cell_line:
            df = df[df["cell_line"].str.contains(cell_line, case=False, na=False)]

        df = df.dropna(subset=[metric])

        if df.empty or group_by not in df.columns:
            raise ValueError(f"No data available to plot for group_by='{group_by}', metric='{metric}'.")

        png_path = render_boxplot(
            df,
            group_by=group_by,
            metric=metric,
            top_n=top_n,
            title_bits=[("compound", compound), ("lineage", lineage), ("cell_line", cell_line)],
        )

        return Image(path=png_path)

    @mcp.tool()
    def get_compound_registration_info(compound: str) -> str:
        """
        Look up compound registration/ordering metadata (ChEMBL ID, LSN, target/project,
        molecular weight, description) for a compound in the loaded dataset.
        Use this before calling a ChEMBL lookup tool, to resolve a compound name to its ChEMBL ID.

        Args:
            compound: The compound name to look up (case-insensitive, partial match)
        """
        df = _data.load_data()
        mask = df["compound"].str.contains(compound, case=False, na=False)
        df_filtered = df[mask]

        if df_filtered.empty:
            return f"No data found for compound '{compound}'."

        available_cols = [c for c in _REGISTRATION_COLUMNS if c in df_filtered.columns]
        if not available_cols:
            return (
                f"'{compound}' matched data, but this dataset has no compound "
                "registration metadata (ChEMBL ID, LSN, target, etc.) — that's only "
                "available on the real CCSP export, not the synthetic sample data."
            )

        actual_compound = df_filtered["compound"].iloc[0]
        info = df_filtered[["compound"] + available_cols].drop_duplicates()

        lines = [f"## Registration Info — {actual_compound}\n"]
        for _, row in info.iterrows():
            for col in available_cols:
                val = row[col]
                if pd.notna(val):
                    lines.append(f"- **{col}:** {val}")
            lines.append("")
        return "\n".join(lines).strip()
