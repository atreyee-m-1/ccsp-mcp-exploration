"""Thin client for the public ChEMBL REST API (no authentication required)."""

import httpx

_BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"
_TIMEOUT = 10.0

_cache: dict[str, dict] = {}


def _get_json(url: str, params: dict) -> dict:
    cache_key = url + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    if cache_key in _cache:
        return _cache[cache_key]

    response = httpx.get(url, params=params, timeout=_TIMEOUT)
    response.raise_for_status()
    data = response.json()
    _cache[cache_key] = data
    return data


def get_mechanisms(chembl_id: str) -> list[dict]:
    """Fetch curated mechanism-of-action records for a compound ChEMBL ID."""
    data = _get_json(f"{_BASE_URL}/mechanism.json", {"molecule_chembl_id": chembl_id})
    return data.get("mechanisms", [])


def get_target(target_chembl_id: str) -> dict | None:
    """Fetch target details (preferred name, gene symbols) for a target ChEMBL ID."""
    data = _get_json(f"{_BASE_URL}/target/{target_chembl_id}.json", {})
    return data or None


def get_molecule(chembl_id: str) -> dict | None:
    """Fetch basic molecule details (type, phase, structure) for a compound ChEMBL ID."""
    data = _get_json(f"{_BASE_URL}/molecule/{chembl_id}.json", {})
    return data or None
