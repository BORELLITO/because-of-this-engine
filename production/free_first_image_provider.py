#!/usr/bin/env python3
"""Free-first visual provider policy for the independent Shorts engine.

The policy is intentionally conservative:
1. factual/public imagery is attempted first;
2. generative fallback is opt-in and never implicit;
3. every successful result is marked for human visual review;
4. failures remain explicit instead of silently substituting unrelated art.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol

from image_provider import ImageGenerationError, ImageRequest, _write_json_atomic


class FactualProvider(Protocol):
    def generate(self, request: ImageRequest, *, query: str) -> dict[str, Any]:
        ...


class GenerativeProvider(Protocol):
    def generate(self, request: ImageRequest) -> dict[str, Any]:
        ...


class FreeFirstImageProvider:
    """Prefer factual imagery; use an explicitly enabled AI fallback only on failure."""

    def __init__(
        self,
        *,
        factual_provider: FactualProvider,
        generative_provider: GenerativeProvider | None = None,
        allow_generative_fallback: bool = False,
    ) -> None:
        self.factual_provider = factual_provider
        self.generative_provider = generative_provider
        self.allow_generative_fallback = allow_generative_fallback

    @staticmethod
    def _mark(output_path: Path, metadata: dict[str, Any], **extra: Any) -> dict[str, Any]:
        result = dict(metadata)
        result.update(
            {
                "selection_policy": "free-first-v1",
                "human_review_required": True,
                **extra,
            }
        )
        _write_json_atomic(
            output_path.with_suffix(output_path.suffix + ".json"),
            result,
        )
        return result

    def generate(self, request: ImageRequest, *, query: str) -> dict[str, Any]:
        try:
            factual = self.factual_provider.generate(request, query=query)
            return self._mark(
                request.output_path.expanduser().resolve(),
                factual,
                selected_source="factual_primary",
            )
        except ImageGenerationError as factual_error:
            if not self.allow_generative_fallback or self.generative_provider is None:
                raise ImageGenerationError(
                    "Free-first policy stopped: the factual provider failed and generative fallback "
                    "is disabled. Review the factual source or explicitly enable the AI fallback."
                ) from factual_error

            try:
                generated = self.generative_provider.generate(request)
            except ImageGenerationError as generative_error:
                raise ImageGenerationError(
                    "Free-first policy stopped: both the factual provider and the explicitly enabled "
                    "generative fallback failed."
                ) from generative_error

            return self._mark(
                request.output_path.expanduser().resolve(),
                generated,
                selected_source="generative_fallback",
                fallback_reason="factual_provider_error",
            )
