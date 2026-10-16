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
        self.preview_skipped = False

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

    def capabilities(self, collection_id: str) -> bool:
        self.calls.append(("capabilities", collection_id))
        if self.capabilities_error is not None:
            raise self.capabilities_error
        if collection_id in self.unsupported_collections:
            from earthaccess_harmony.client import CollectionNotFound

            raise CollectionNotFound(collection_id)
        return True

    def cancel(self, job_id: str) -> None:
        self.calls.append(("cancel", job_id))
        self.canceled = True

    def pause(self, job_id: str) -> bool:
        self.calls.append(("pause", job_id))
        self.paused = True
        return True

    def resume(self, job_id: str) -> bool:
        self.calls.append(("resume", job_id))
        self.resumed = True
        return True

    def skip_preview(self, job_id: str) -> bool:
        self.calls.append(("skip_preview", job_id))
        self.preview_skipped = True
        return True


class HarmonyFixtures(Fixtures):
    def __init__(self, client: FakeHarmonyClient | None = None, **kwargs: Any) -> None:
        self.client = client or FakeHarmonyClient(
            unsupported_collections={"C-NO-HARMONY"}
        )
        kwargs.setdefault(
            "result_set", GranuleResultSet([make_granule(collection_id="C-HARMONY")])
        )
        kwargs.setdefault(
            "unsupported_result_set",
            GranuleResultSet([make_granule(collection_id="C-NO-HARMONY")]),
        )
        super().__init__(**kwargs)

    def backend(self) -> AbstractContextManager[Any]:
        from earthaccess_harmony import client as client_mod

        return mock.patch.multiple(
            client_mod,
            make_client=lambda ctx: self.client,
            build_request=lambda **kwargs: {"request": kwargs},
        )
