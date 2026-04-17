"""
Hard-coded Blocking Strategies

Fallback strategies when LLM is not available or disabled.
"""

from __future__ import annotations
from collections import defaultdict


class PrimaryTypeBlockingStrategy:
    """
    Hard-coded blocking by primary_type.

    Fallback strategy when LLM is not available or fails.
    Groups entities by their primary_type field (PERSON, ORGANIZATION, etc.)
    """

    def block(self, items: list[dict]) -> dict[str, list[dict]]:
        """
        Group items by primary_type.

        Args:
            items: List of entity items with primary_type in payload

        Returns:
            Dict mapping primary_type → list of items
        """
        blocks = defaultdict(list)
        for item in items:
            ptype = str(item.get("payload", {}).get("primary_type", "UNKNOWN"))
            blocks[ptype].append(item)
        return dict(blocks)
