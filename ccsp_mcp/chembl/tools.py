"""MCP tools for looking up compound/target information from ChEMBL."""

import httpx

from ..screening import data as _screening_data
from . import client

INSTRUCTIONS = (
    "You also have access to chembl_lookup_compound_mechanism, which looks up a compound's "
    "mechanism of action and target from the public ChEMBL database. Use it when the user asks "
    "what a compound does, what it targets, or its mechanism of action — it can resolve the "
    "ChEMBL ID automatically from a compound name already present in the loaded screening data."
)

_EXPLORE_URL = "https://www.ebi.ac.uk/chembl/explore/compound/{id}"


def _resolve_chembl_id(compound: str) -> str | None:
    df = _screening_data.load_data()
    if "ChEMBL ID" not in df.columns:
        return None
    mask = df["compound"].str.contains(compound, case=False, na=False)
    matches = df.loc[mask, "ChEMBL ID"].dropna()
    if matches.empty:
        return None
    return matches.iloc[0]


def register(mcp) -> None:
    """Register all ChEMBL-domain tools on the given FastMCP instance."""

    @mcp.tool()
    def chembl_lookup_compound_mechanism(
        compound: str | None = None, chembl_id: str | None = None
    ) -> str:
        """
        Look up a compound's mechanism of action and target from the public ChEMBL database.
        Use this to answer "what does compound X do?" / "what's its target?" / "what's its
        mechanism of action?" Only a public ChEMBL ID is sent externally — no proprietary data.

        Args:
            compound: Compound name to resolve via the loaded screening data (case-insensitive, partial match)
            chembl_id: A ChEMBL compound ID directly (e.g. "CHEMBL3545376"), if known. Takes priority over compound.
        """
        if not chembl_id:
            if not compound:
                return "Provide either a compound name or a chembl_id."
            chembl_id = _resolve_chembl_id(compound)
            if not chembl_id:
                return (
                    f"Could not resolve a ChEMBL ID for '{compound}' from the loaded dataset "
                    "(it may have no ChEMBL ID column, or no match). Pass chembl_id directly instead."
                )

        try:
            mechanisms = client.get_mechanisms(chembl_id)
        except httpx.HTTPError as e:
            return f"Error contacting ChEMBL for {chembl_id}: {e}"

        explore_link = _EXPLORE_URL.format(id=chembl_id)

        if not mechanisms:
            try:
                molecule = client.get_molecule(chembl_id)
            except httpx.HTTPError as e:
                return f"Error contacting ChEMBL for {chembl_id}: {e}"

            if not molecule:
                return f"No ChEMBL record found for '{chembl_id}'.\n\n{explore_link}"

            lines = [
                f"## {chembl_id} — No curated mechanism of action in ChEMBL\n",
                f"- **Molecule type:** {molecule.get('molecule_type', 'unknown')}",
                f"- **Max phase:** {molecule.get('max_phase', 'unknown')}",
                f"\n{explore_link}",
            ]
            return "\n".join(lines)

        lines = [f"## {chembl_id} — Mechanism of Action\n"]
        for mech in mechanisms:
            lines.append(f"- **Mechanism:** {mech.get('mechanism_of_action', 'unknown')}")
            lines.append(f"- **Action type:** {mech.get('action_type', 'unknown')}")
            lines.append(f"- **Max phase:** {mech.get('max_phase', 'unknown')}")

            target_id = mech.get("target_chembl_id")
            if target_id:
                try:
                    target = client.get_target(target_id)
                except httpx.HTTPError:
                    target = None
                target_name = target.get("pref_name", target_id) if target else target_id
                lines.append(f"- **Target:** {target_name} ({target_id})")
            lines.append("")

        lines.append(explore_link)
        return "\n".join(lines)
