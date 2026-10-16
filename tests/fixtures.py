"""A fake Harmony client and conformance fixtures (no network, no harmony-py)."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any
from unittest import mock

from earthaccess_plugin_spec.testing import Fixtures

__all__ = ["FakeHarmonyClient", "HarmonyFixtures"]


class FakeHarmonyClient:
    """A minimal stand-in for ``harmony.Client``.

    ``statuses`` is consumed in order; the last value repeats.
    """

    def __init__(
        self,
        statuses: list[str] | None = None,
        urls: list[str] | None = None,
        job_id: str = "job-123",
    ) -> None:
        self._statuses = list(statuses) if statuses else ["successful"]
        self.urls = list(urls) if urls is not None else ["https://example.org/out.nc4"]
        self.job_id = job_id
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
        super().__init__(**kwargs)
        self.client = client or FakeHarmonyClient()

    def backend(self) -> AbstractContextManager[Any]:
        from earthaccess_harmony import client as client_mod

        return mock.patch.multiple(
            client_mod,
            make_client=lambda ctx: self.client,
            build_request=lambda **kwargs: {"request": kwargs},
        )
