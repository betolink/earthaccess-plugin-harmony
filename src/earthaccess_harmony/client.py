"""Harmony backend seams.

Every place where this plugin depends on the ``harmony-py`` API lives here so
that there is a single fix point when the backend changes. Both functions are
patched in tests.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

__all__ = ["build_request", "make_client"]


def make_client(ctx: Any) -> Any:
    """Build a Harmony client authenticated with the caller's EDL session.

    VERIFY: how ``harmony.Client`` is constructed from an EDL session or token.
    """

    import harmony

    # ctx.auth is a lazy EDL handle; session() logs in on first use.
    return harmony.Client(session=ctx.auth.session())


def build_request(
    *,
    collection_id: str,
    granule_ids: Sequence[str],
    bbox: Sequence[float] | None = None,
    variables: Sequence[str] | None = None,
    shapefile: str | None = None,
    output_format: str | None = None,
    skip_preview: bool = False,
) -> Any:
    """Build a Harmony request.

    VERIFY: the ``Request`` keywords (``granule_id``, ``spatial``, ``shape``,
    ``format``, ``skip_preview``) and the ``Collection``/``BBox`` helpers.
    """

    import harmony

    return harmony.Request(
        collection=harmony.Collection(id=collection_id),
        granule_id=list(granule_ids),
        spatial=harmony.BBox(*bbox) if bbox is not None else None,
        variables=list(variables) if variables else None,
        shape=shapefile,
        format=output_format,
        skip_preview=skip_preview,
    )
