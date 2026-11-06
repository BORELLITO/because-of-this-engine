"""Single source of truth for visual-provider rights and host policy.

The policy is intentionally narrow and fail-closed. Providers must expose a
commercial/free-use license on the source page, and media URLs must remain on
the provider's exact host or an explicitly permitted subdomain.
"""

from __future__ import annotations

from typing import Any


PROVIDER_POLICIES: dict[str, dict[str, Any]] = {
    "mixkit": {
        "license_name": "Mixkit Stock Video Free License",
        "page_hosts": frozenset({"mixkit.co"}),
        "media_hosts": frozenset({"mixkit.co"}),
    },
    "pixabay": {
        "license_name": "Pixabay Content License",
        "page_hosts": frozenset({"pixabay.com"}),
        "media_hosts": frozenset({"pixabay.com"}),
    },
}


def policy_for(provider: str) -> dict[str, Any] | None:
    """Return the immutable provider policy, or None for unsupported routes."""
    return PROVIDER_POLICIES.get(str(provider or "").strip().lower())


def host_allowed(hostname: str | None, allowed_bases: set[str] | frozenset[str]) -> bool:
    """Allow only exact bases or their explicit subdomains."""
    normalized = str(hostname or "").lower().rstrip(".")
    return any(
        normalized == base or normalized.endswith("." + base)
        for base in allowed_bases
    )
