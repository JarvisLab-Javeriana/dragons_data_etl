
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BasePipeline(ABC):
    """Contract every source-specific pipeline should follow."""

    @abstractmethod
    def run(self) -> dict[str, Any]:
        """Execute the full pipeline and return the resulting metrics dict."""
        raise NotImplementedError
