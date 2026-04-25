"""Cache persistant des noms français d'espèces via Wikidata (SPARQL)."""
from __future__ import annotations

import json
import logging
from pathlib import Path

import aiohttp

_LOGGER = logging.getLogger(__name__)
_SPARQL_URL = "https://query.wikidata.org/sparql"
_USER_AGENT = "BirdNET-HA-Integration/1.0"


class SpeciesFrCache:
    """JSON file cache + Wikidata fallback for French bird common names.

    On first lookup for an unknown species: queries Wikidata SPARQL by
    scientific name (P225 = taxon name), stores the result, and persists
    the full cache to disk so future HA restarts skip the network call.
    """

    def __init__(self, cache_path: str) -> None:
        self._path = Path(cache_path)
        self._data: dict[str, str] = {}
        self._load()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._path.is_file():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
                _LOGGER.debug("French name cache loaded: %d entries", len(self._data))
            except Exception as exc:
                _LOGGER.warning("French name cache unreadable, starting fresh: %s", exc)
                self._data = {}

    def _save(self) -> None:
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except Exception as exc:
            _LOGGER.warning("Cannot save French name cache: %s", exc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self, scientific_name: str) -> str | None:
        """Return cached French name, or None if not yet known."""
        return self._data.get(scientific_name)

    async def fetch(self, scientific_name: str) -> str | None:
        """Look up French name on Wikidata, cache and persist if found."""
        if not scientific_name:
            return None
        if scientific_name in self._data:
            return self._data[scientific_name]

        sparql = (
            "SELECT ?frLabel WHERE { "
            f'?taxon wdt:P225 "{scientific_name}" . '
            "?taxon rdfs:label ?frLabel . "
            'FILTER(LANG(?frLabel) = "fr") '
            "} LIMIT 1"
        )
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            async with aiohttp.ClientSession(connector=connector) as session:
                async with session.get(
                    _SPARQL_URL,
                    params={"query": sparql, "format": "json"},
                    headers={"Accept": "application/json", "User-Agent": _USER_AGENT},
                    timeout=aiohttp.ClientTimeout(total=8),
                ) as resp:
                    if resp.status != 200:
                        _LOGGER.debug("Wikidata returned HTTP %s for %s", resp.status, scientific_name)
                        return None
                    payload = await resp.json()

            bindings = payload.get("results", {}).get("bindings", [])
            if bindings:
                fr_name = bindings[0].get("frLabel", {}).get("value", "").strip()
                if fr_name:
                    self._data[scientific_name] = fr_name
                    self._save()
                    _LOGGER.debug("French name cached: %s → %s", scientific_name, fr_name)
                    return fr_name

        except Exception as exc:
            _LOGGER.debug("Wikidata lookup failed for %s: %s", scientific_name, exc)

        return None
