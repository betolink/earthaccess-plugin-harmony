"""The Harmony plugin: subset and transform Earthdata granules."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from earthaccess_plugin_spec import Capabilities, Capability, PluginBase

from . import client as _client
from .job import HarmonyJob

__all__ = ["HarmonyPlugin"]


def _operations_from_services(
    services: list[dict[str, Any]],
) -> tuple[frozenset[Capability], frozenset[str]]:
    """Map Harmony's capabilities response onto our operation/format enums."""

    operations: set[Capability] = set()
    formats: set[str] = set()
    for service in services:
        caps = service.get("capabilities", {}) or {}
        subsetting = caps.get("subsetting", {}) or {}
        if subsetting.get("bbox"):
            operations.add(Capability.SUBSET_BBOX)
        if subsetting.get("temporal"):
            operations.add(Capability.SUBSET_TEMPORAL)
        if subsetting.get("variable"):
            operations.add(Capability.SUBSET_VARIABLE)
        if subsetting.get("shape"):
            operations.add(Capability.SUBSET_SHAPE)
        if subsetting.get("dimension"):
            operations.add(Capability.SUBSET_DIMENSION)
        if (caps.get("reprojection") or {}).get("supported"):
            operations.add(Capability.REPROJECT)
        averaging = caps.get("averaging", {}) or {}
        if averaging.get("time"):
            operations.add(Capability.AVERAGE_TIME)
        if averaging.get("area"):
            operations.add(Capability.AVERAGE_AREA)
        if caps.get("concatenation"):
            operations.add(Capability.CONCATENATE)
        for output in caps.get("outputFormats", []) or []:
            mime = output.get("mimeType") or output.get("name")
            if mime:
                formats.add(mime)
    return frozenset(operations), frozenset(formats)


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

    def _supports(self, results: Any) -> Capabilities:
        collection_id = getattr(results, "collection_id", "") or ""
        short_name = getattr(results, "short_name", "") or ""
        label = short_name or collection_id
        if not label:
            return Capabilities(None, reason="need a collection id or short name")
        try:
            response = _client.capabilities(
                self._harmony_client(),
                collection_id=collection_id or None,
                short_name=short_name or None,
            )
        except _client.CollectionNotFound:
            return Capabilities(
                False, collection=label, reason=f"no Harmony service for {label}"
            )
        except _client.CapabilitiesUnavailable as exc:
            return Capabilities(
                None, collection=label, reason=f"could not check Harmony: {exc}"
            )
        except Exception as exc:  # noqa: BLE001 - unknown means don't hard-block
            return Capabilities(
                None, collection=label, reason=f"could not check Harmony: {exc!r}"
            )
        services = response.get("services") or []
        if not services:
            return Capabilities(
                False, collection=label, reason=f"no Harmony service for {label}"
            )
        operations, formats = _operations_from_services(services)
        return Capabilities(
            True, collection=label, operations=operations, formats=formats
        )
