"""Single source of truth for visual-provider rights and host policy.

Provider policy is intentionally fail-closed.  Automated stock routes and
manual archive/government routes are distinct: a source can be discoverable
without being eligible for automatic download or render promotion.
"""

from __future__ import annotations

from typing import Any


def _policy(
    *,
    license_name: str,
    page_hosts: set[str] | frozenset[str],
    media_hosts: set[str] | frozenset[str],
    source_tier: str,
    manual_only: bool = False,
    license_names: tuple[str, ...] = (),
) -> dict[str, Any]:
    accepted = tuple(dict.fromkeys((license_name, *license_names)))
    return {
        "license_name": license_name,
        "license_names": accepted,
        "page_hosts": frozenset(page_hosts),
        "media_hosts": frozenset(media_hosts),
        "source_tier": source_tier,
        "manual_only": manual_only,
    }


PROVIDER_POLICIES: dict[str, dict[str, Any]] = {
    # Automated/free stock lanes.  These remain the default discovery order.
    "mixkit": _policy(
        license_name="Mixkit Stock Video Free License",
        page_hosts={"mixkit.co"},
        media_hosts={"mixkit.co"},
        source_tier="stock_auto",
    ),
    "pixabay": _policy(
        license_name="Pixabay Content License",
        page_hosts={"pixabay.com"},
        media_hosts={"pixabay.com"},
        source_tier="stock_auto",
    ),
    "pexels": _policy(
        license_name="Pexels License",
        page_hosts={"pexels.com"},
        media_hosts={"pexels.com", "videos.pexels.com", "images.pexels.com"},
        source_tier="stock_auto",
    ),
    "coverr": _policy(
        license_name="Coverr Video License",
        page_hosts={"coverr.co"},
        media_hosts={"coverr.co", "storage.coverr.co"},
        source_tier="stock_auto",
    ),
    # Discovery is allowed, but every item needs page-level license and
    # attribution review before intake.
    "videvo": _policy(
        license_name="Videvo Royalty-Free License",
        license_names=(
            "Videvo Attribution License",
            "Videvo Creative Commons 3.0",
            "CC BY 3.0",
        ),
        page_hosts={"videvo.net"},
        media_hosts={"videvo.net", "static.videvo.net"},
        source_tier="cc_manual",
        manual_only=True,
    ),
    "videezy": _policy(
        license_name="Videezy Free Video License",
        license_names=(
            "Videezy Attribution License",
            "Creative Commons",
            "CC BY 3.0",
        ),
        page_hosts={"videezy.com"},
        media_hosts={"videezy.com", "static.videezy.com"},
        source_tier="cc_manual",
        manual_only=True,
    ),
    # Per-file rights lanes.  The license_name is a normalized label used in
    # the manifest; the actual page/item license must also be retained.
    "wikimedia": _policy(
        license_name="Wikimedia Commons Per-File License",
        license_names=(
            "Public Domain",
            "CC0 1.0",
            "CC BY 4.0",
            "CC BY-SA 4.0",
            "CC BY 3.0",
            "CC BY-SA 3.0",
        ),
        page_hosts={"commons.wikimedia.org"},
        media_hosts={"commons.wikimedia.org", "upload.wikimedia.org"},
        source_tier="cc_manual",
        manual_only=True,
    ),
    "nasa": _policy(
        license_name="NASA Media Guidelines (per asset)",
        page_hosts={"nasa.gov", "images.nasa.gov", "svs.gsfc.nasa.gov"},
        media_hosts={"nasa.gov", "images.nasa.gov", "svs.gsfc.nasa.gov"},
        source_tier="government_manual",
        manual_only=True,
    ),
    "noaa": _policy(
        license_name="NOAA Media Rights (per asset)",
        page_hosts={"noaa.gov", "oceanexplorer.noaa.gov", "sos.noaa.gov"},
        media_hosts={"noaa.gov", "oceanexplorer.noaa.gov", "sos.noaa.gov"},
        source_tier="government_manual",
        manual_only=True,
    ),
    "loc": _policy(
        license_name="Library of Congress Rights & Access (per item)",
        page_hosts={"loc.gov"},
        media_hosts={"loc.gov", "tile.loc.gov"},
        source_tier="archive_manual",
        manual_only=True,
    ),
    "nara": _policy(
        license_name="NARA Rights Status (per item)",
        page_hosts={"archives.gov", "catalog.archives.gov"},
        media_hosts={"archives.gov", "catalog.archives.gov"},
        source_tier="archive_manual",
        manual_only=True,
    ),
    "internet_archive": _policy(
        license_name="Internet Archive Rights Statement (per item)",
        page_hosts={"archive.org"},
        media_hosts={"archive.org", "ia801", "ia800", "ia900"},
        source_tier="archive_manual",
        manual_only=True,
    ),
    "original": _policy(
        license_name="Original/Commissioned Source",
        page_hosts=set(),
        media_hosts=set(),
        source_tier="original",
        manual_only=True,
    ),
}


def policy_for(provider: str) -> dict[str, Any] | None:
    """Return the provider policy, or None for unsupported routes."""
    return PROVIDER_POLICIES.get(str(provider or "").strip().lower())


def license_allowed(policy: dict[str, Any], license_name: str | None) -> bool:
    """Match an explicit manifest license against the provider allowlist."""
    value = str(license_name or "").strip().lower()
    accepted = {
        str(item).strip().lower()
        for item in policy.get("license_names", ())
        if str(item).strip()
    }
    return bool(value and value in accepted)


def host_allowed(hostname: str | None, allowed_bases: set[str] | frozenset[str]) -> bool:
    """Allow only exact bases or their explicit subdomains."""
    normalized = str(hostname or "").lower().rstrip(".")
    for base in allowed_bases:
        base = str(base).lower().rstrip(".")
        # A wildcard-like media host such as ia801 is intentionally treated as
        # a prefix only when the policy explicitly uses it.
        if normalized == base or normalized.endswith("." + base):
            return True
        if base.startswith("ia") and normalized.startswith(base + "."):
            return True
    return False
