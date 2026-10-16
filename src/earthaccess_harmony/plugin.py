"""The Harmony plugin: subset and transform Earthdata granules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from earthaccess_plugin_spec import PluginBase, Support

from . import client as _client
from .job import HarmonyJob

__all__ = ["HarmonyPlugin"]


class HarmonyPlugin(PluginBase):
    name = "harmony"
    needs = frozenset({"concept_id"})
    auth = "edl"
    output = "assets"

    @dataclass
    class Options:
        bbox: tuple[float, float, float, float] | None = None
        variables: list[str] = field(default_factory=list)
        shapefile: str | None = None
        output_format: str | None = None
        skip_preview: bool = False

    def __init__(self, ctx: Any) -> None:
        super().__init__(ctx)
        self._h: Any = None

    def _harmony_client(self) -> Any:
        if self._h is None:
            self._h = _client.make_client(self._ctx)
        return self._h

    def _request(self, results: Any, options: Options) -> HarmonyJob:
        request = _client.build_request(
            collection_id=results.collection_id,
            granule_ids=list(results.ids),
            bbox=options.bbox,
            variables=options.variables,
            shapefile=options.shapefile,
            output_format=options.output_format,
            skip_preview=options.skip_preview,
        )
        client = self._harmony_client()
        return HarmonyJob(client.submit(request), client)

    def get_job(self, job_id: str) -> HarmonyJob:
        return HarmonyJob(job_id, self._harmony_client())

    def _supports(self, results: Any) -> Support:
        # Association first (cheap: already in the results), capabilities as the
        # tiebreaker (one network call per collection).
        if any(
            str(service.get("Type", "")).lower() == "harmony"
            for service in results.services()
        ):
            return Support(True)
        try:
            if _client.capabilities(self._harmony_client(), results.collection_id):
                return Support(True)
            return Support(
                False,
                f"no Harmony service is associated with {results.collection_id}",
            )
        except _client.CollectionNotFound:
            return Support(
                False,
                f"no Harmony service is associated with {results.collection_id}",
            )
        except _client.CapabilitiesUnavailable as exc:
            return Support(None, f"could not check Harmony capabilities: {exc}")
        except Exception as exc:  # noqa: BLE001 - unknown means don't hard-block
            return Support(None, f"could not check Harmony capabilities: {exc!r}")
