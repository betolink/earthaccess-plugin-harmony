"""Harmony backend seams.

Every place where this plugin depends on the ``harmony-py`` API lives here so
that there is a single fix point when the backend changes. The functions are
patched in tests.

Verified against ``harmony-py`` 1.8.
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any

__all__ = [
    "CapabilitiesUnavailable",
    "CollectionNotFound",
    "build_request",
    "capabilities",
    "make_client",
]

_CAPABILITIES_VERSION = "3"

_SHAPEFILE_MIMES = {
    "zip": "application/shapefile+zip",
    "shz": "application/shapefile+zip",
    "json": "application/geo+json",
    "geojson": "application/geo+json",
    "kml": "application/vnd.google-earth.kml+xml",
}


class CapabilitiesUnavailable(Exception):
    """Raised when the Harmony capabilities check cannot be performed.

    Maps to ``Support(None)``: never hard-block a request on a failed check.
    """


class CollectionNotFound(Exception):
    """Raised when Harmony definitively has no service for a collection."""


def make_client(ctx: Any) -> Any:
    """Build a Harmony client from the caller's Earthdata Login credentials.

    ``harmony.Client`` takes either ``auth=(username, password)`` or
    ``token=...``. A netrc login has no token, so prefer the basic-auth pair.
    """

    import harmony

    basic = getattr(ctx.auth, "basic_auth", None)
    creds = basic() if callable(basic) else None
    if creds:
        return harmony.Client(auth=creds)
    return harmony.Client(token=ctx.auth.token())


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
    """Build a ``harmony.Request``, omitting options Harmony should default."""

    import harmony

    kwargs: dict[str, Any] = {
        "collection": harmony.Collection(id=collection_id),
        "granule_id": list(granule_ids),
    }
    if bbox is not None:
        kwargs["spatial"] = harmony.BBox(*bbox)
    if variables:
        kwargs["variables"] = list(variables)
    if shapefile:
        kwargs["shape"] = _open_shapefile(shapefile)
    if output_format:
        kwargs["format"] = output_format
    if skip_preview:
        kwargs["skip_preview"] = True
    return harmony.Request(**kwargs)


def _open_shapefile(path: str) -> tuple[Any, str]:
    extension = os.path.splitext(path)[1].lstrip(".").lower()
    mime = _SHAPEFILE_MIMES.get(extension, "application/geo+json")
    return (open(path, "rb"), mime)


def capabilities(
    client: Any, *, collection_id: str | None = None, short_name: str | None = None
) -> dict[str, Any]:
    """Return Harmony's capabilities response for a collection.

    Raises :class:`CollectionNotFound` for a definitive no and
    :class:`CapabilitiesUnavailable` when the check cannot be made.
    """

    import harmony

    if not collection_id and not short_name:
        raise CapabilitiesUnavailable("a collection id or short name is required")
    # CapabilitiesRequest rejects sending both, so prefer the concept id.
    if collection_id:
        request = harmony.CapabilitiesRequest(
            collection_id=collection_id,
            capabilities_version=_CAPABILITIES_VERSION,
        )
    else:
        request = harmony.CapabilitiesRequest(
            short_name=short_name,
            capabilities_version=_CAPABILITIES_VERSION,
        )
    try:
        response = client.submit(request)
    except Exception as exc:  # noqa: BLE001 - translate backend errors below
        if _is_not_found(exc):
            raise CollectionNotFound(short_name or collection_id) from exc
        raise CapabilitiesUnavailable(str(exc)) from exc
    if not isinstance(response, dict):
        raise CapabilitiesUnavailable("unexpected capabilities response")
    return response


def _is_not_found(exc: Exception) -> bool:
    text = " ".join(str(arg) for arg in exc.args).lower()
    return "not found" in text or "could not find" in text
