"""A fake Harmony client and conformance fixtures (no network, no harmony-py)."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any
from unittest import mock

from earthaccess_plugin_spec.results import GranuleResultSet
from earthaccess_plugin_spec.testing import Fixtures

__all__ = ["FakeHarmonyClient", "HarmonyFixtures", "make_granule"]


def make_granule(
    *,
    collection_id: str = "C-HARMONY",
    concept_id: str = "G1",
    ur: str = "G1.EXAMPLE",
    short_name: str = "ATL06",
) -> dict[str, Any]:
    return {
        "meta": {"concept-id": concept_id, "collection-concept-id": collection_id},
        "umm": {
            "GranuleUR": ur,
            "CollectionReference": {"ShortName": short_name, "Version": "006"},
        },
    }


class FakeHarmonyClient:
    """A minimal stand-in for ``harmony.Client``.

    ``statuses`` is consumed in order; the last value repeats.
    """

    def __init__(
        self,
        statuses: list[str] | None = None,
        urls: list[str] | None = None,
        job_id: str = "job-123",
        unsupported_collections: set[str] | None = None,
        capabilities_error: Exception | None = None,
    ) -> None:
        self._statuses = list(statuses) if statuses else ["successful"]
        self.urls = list(urls) if urls is not None else ["https://example.org/out.nc4"]
        self.job_id = job_id
        self.unsupported_collections = set(unsupported_collections or ())
        self.capabilities_error = capabilities_error
        self.calls: list[tuple[str, Any]] = []
        self.canceled = False
        self.paused = False
        self.resumed = False

    def submit(self, request: Any) -> str:
        self.calls.append(("submit", request))
        return self.job_id

    def status(self, job_id: str) -> dict[str, Any]:
        self.calls.append(("status", job_id))
        raw = self._statuses[0]
        if len(self._statuses) > 1:
            raw = self._statuses.pop(0)
        return {"status": raw, "request": {"secret": True}, "message": "ok"}

    def result_urls(self, job_id: str) -> list[str]:
        self.calls.append(("result_urls", job_id))
        return list(self.urls)

    def cancel(self, job_id: str) -> None:
        self.calls.append(("cancel", job_id))
        self.canceled = True

    def pause(self, job_id: str) -> None:
        self.calls.append(("pause", job_id))
        self.paused = True

    def resume(self, job_id: str) -> None:
        self.calls.append(("resume", job_id))
        self.resumed = True


def fake_capabilities(client: FakeHarmonyClient):
    """A stand-in for the ``client.capabilities`` seam (returns a response dict)."""

    def check(
        _client: Any, *, collection_id: str | None = None, short_name: str | None = None
    ) -> dict[str, Any]:
        from earthaccess_harmony.client import CollectionNotFound

        if client.capabilities_error is not None:
            raise client.capabilities_error
        key = collection_id or short_name
        if key in client.unsupported_collections:
            raise CollectionNotFound(key)
        return {
            "services": [
                {
                    "name": "subsetter",
                    "capabilities": {
                        "subsetting": {
                            "bbox": True,
                            "temporal": True,
                            "variable": True,
                            "shape": True,
                            "dimension": False,
                        },
                        "outputFormats": [{"mimeType": "application/netcdf4"}],
                    },
                }
            ]
        }

    return check


class HarmonyFixtures(Fixtures):
    def __init__(self, client: FakeHarmonyClient | None = None, **kwargs: Any) -> None:
        self.client = client or FakeHarmonyClient(
            unsupported_collections={"C-NO-HARMONY", "LANDSAT_8_C1"}
        )
        kwargs.setdefault(
            "result_set", GranuleResultSet([make_granule(collection_id="C-HARMONY")])
        )
        kwargs.setdefault(
            "unsupported_result_set",
            GranuleResultSet(
                [
                    make_granule(
                        collection_id="C-NO-HARMONY", short_name="LANDSAT_8_C1"
                    )
                ]
            ),
        )
        super().__init__(**kwargs)

    def backend(self) -> AbstractContextManager[Any]:
        from earthaccess_harmony import client as client_mod

        return mock.patch.multiple(
            client_mod,
            make_client=lambda ctx: self.client,
            build_request=lambda **kwargs: {"request": kwargs},
            capabilities=fake_capabilities(self.client),
        )
