"""Box-plot rendering for the CCSP dose-response screening domain."""

import tempfile

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def render_boxplot(
    df: pd.DataFrame,
    group_by: str,
    metric: str,
    top_n: int,
    title_bits: list[tuple[str, str]],
) -> str:
    """Render a box plot of `metric` grouped by `group_by`, capped to the top_n
    groups with lowest median metric. Returns the path to a temp PNG file."""
    medians = df.groupby(group_by)[metric].median().sort_values()
    top_groups = medians.head(top_n).index.tolist()
    df = df[df[group_by].isin(top_groups)]

    data_by_group = [df[df[group_by] == g][metric].values for g in top_groups]

    fig, ax = plt.subplots(figsize=(max(6, len(top_groups) * 0.5), 6))
    ax.boxplot(data_by_group, tick_labels=top_groups)
    ax.set_xlabel(group_by)
    ax.set_ylabel(metric)
    title_suffix = ", ".join(f"{k}={v}" for k, v in title_bits if v)
    ax.set_title(f"{metric} by {group_by}" + (f" ({title_suffix})" if title_suffix else ""))
    plt.setp(ax.get_xticklabels(), rotation=45, ha="right")
    fig.tight_layout()

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    fig.savefig(tmp.name, dpi=150)
    plt.close(fig)

    return tmp.name
