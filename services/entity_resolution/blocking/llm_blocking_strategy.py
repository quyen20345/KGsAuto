"""
LLM-Based Blocking Strategy

Uses LLM to automatically determine blocking strategy based on entity types.
LLM analyzes unique label combinations and groups them into blocks where
entities might refer to the same real-world entity.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger(__name__)


class LLMBlockingStrategy:
    """
    Use LLM to determine blocking strategy based on entity types.

    LLM analyzes all unique label combinations and groups them into blocks
    where entities might refer to the same real-world entity.
    """

    def __init__(self, llm_provider: str, llm_model: str, llm_api_key: str | None = None):
        """
        Initialize LLM blocking strategy.

        Args:
            llm_provider: LLM provider (OpenAICompatible, gemini, etc.)
            llm_model: Model name
            llm_api_key: API key (optional)
        """
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        self._llm_client = None
        self._cache = {}  # Cache blocking strategy by unique label set

    def _get_llm_client(self) -> Any:
        """Lazy load LLM client."""
        if self._llm_client is None:
            from services.llms import get_llm
            self._llm_client = get_llm(
                provider=self.llm_provider,
                model_name=self.llm_model,
                api_key=self.llm_api_key,
            )
        return self._llm_client

    def block(self, items: list[dict]) -> dict[str, list[dict]]:
        """
        Group items into blocks using LLM reasoning.

        Args:
            items: List of entity items with labels

        Returns:
            Dict mapping block_id → list of items in that block
        """
        # 1. Extract unique label combinations
        unique_labels = self._extract_unique_labels(items)

        # 2. Call LLM once to get blocking strategy (with caching)
        cache_key = frozenset(tuple(sorted(labels)) for labels in unique_labels)
        if cache_key not in self._cache:
            logger.info(f"Calling LLM to determine blocking strategy for {len(unique_labels)} unique label combinations")
            blocking_strategy = self._llm_determine_blocks(unique_labels)
            self._cache[cache_key] = blocking_strategy
            logger.info(f"LLM returned {len(blocking_strategy['blocks'])} blocks")
        else:
            logger.info("Using cached blocking strategy")
            blocking_strategy = self._cache[cache_key]

        # 3. Apply strategy to group items
        blocks = self._apply_strategy(items, blocking_strategy)
        return blocks

    def _extract_unique_labels(self, items: list[dict]) -> list[list[str]]:
        """
        Extract unique label combinations from items.

        Example:
            Input: 10,000 entities with labels
            - Entity 1: ["PERSON"]
            - Entity 2: ["PERSON", "LECTURER"]
            - Entity 3: ["LECTURER", "PERSON"]  # Same as Entity 2, different order
            - Entity 4: ["ORGANIZATION"]
            - ...

            Output: Only unique combinations (sorted to deduplicate)
            [
                ["PERSON"],
                ["LECTURER", "PERSON"],  # Sorted, so ["PERSON", "LECTURER"] = ["LECTURER", "PERSON"]
                ["ORGANIZATION"],
                ["ORGANIZATION", "UNIVERSITY"],
                ...
            ]

        Why extract unique combinations?
        1. Reduce LLM input size: 10,000 entities → ~20 unique combinations
        2. Avoid duplicate analysis: ["PERSON", "LECTURER"] = ["LECTURER", "PERSON"]
        3. LLM only needs to reason about types, not individual entities
        """
        unique = set()
        for item in items:
            labels = tuple(sorted(item.get("payload", {}).get("labels", [])))
            unique.add(labels)
        return [list(labels) for labels in unique]

    def _llm_determine_blocks(self, unique_labels: list[list[str]]) -> dict:
        """
        Call LLM to determine blocking strategy.

        Args:
            unique_labels: List of unique label combinations

        Returns:
            Blocking strategy dict with format:
            {
              "blocks": [
                {
                  "block_id": "person_related",
                  "types": ["PERSON", "LECTURER", "RESEARCHER"],
                  "reasoning": "..."
                }
              ]
            }
        """
        # Log input types
        logger.info("=" * 80)
        logger.info("LLM BLOCKING INPUT:")
        logger.info(f"Total unique label combinations: {len(unique_labels)}")
        for i, labels in enumerate(unique_labels, 1):
            logger.info(f"  {i}. {labels}")
        logger.info("=" * 80)

        prompt = f"""Bạn là chuyên gia về entity resolution. Nhiệm vụ của bạn là phân tích các entity types và nhóm chúng thành blocks.

Entities trong cùng block có thể là cùng một thực thể (đồng tham chiếu). Ví dụ:
- "PERSON" và "LECTURER" có thể cùng block vì một người có thể được gọi là "person" hoặc "lecturer"
- "ORGANIZATION" và "UNIVERSITY" có thể cùng block vì một trường đại học là một tổ chức
- "ORGANIZATIONAL_UNIT" và "TRADE_UNION_UNIT" NÊN KHÁC block với "ORGANIZATION" vì đơn vị con không nên merge với tổ chức cha

Entity types cần phân tích:
{json.dumps(unique_labels, indent=2, ensure_ascii=False)}

Trả về JSON format (chỉ JSON, không có text khác):
{{
  "blocks": [
    {{
      "block_id": "person_related",
      "types": ["PERSON", "LECTURER"],
      "reasoning": "Các type này đều chỉ con người, có thể đồng tham chiếu"
    }},
    {{
      "block_id": "organization_related",
      "types": ["ORGANIZATION", "UNIVERSITY"],
      "reasoning": "Các type tổ chức cấp cao, có thể có tên gọi khác nhau"
    }}
  ]
}}

Lưu ý:
- Mỗi type chỉ thuộc 1 block duy nhất (quan trọng: tránh conflict khi rewiring relationships)
- Nếu một type có thể thuộc nhiều blocks, chọn block phù hợp nhất
- block_id phải là snake_case, ngắn gọn
- reasoning giải thích tại sao nhóm các types này lại với nhau
"""

        llm = self._get_llm_client()
        response = llm.generate(prompt)

        # Parse JSON from response
        content = response.content.strip()

        # Try to extract JSON if wrapped in markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        try:
            strategy = json.loads(content)
            self._validate_strategy(strategy, unique_labels)

            # Log output blocks
            logger.info("=" * 80)
            logger.info("LLM BLOCKING OUTPUT:")
            logger.info(f"Total blocks: {len(strategy.get('blocks', []))}")
            for block in strategy.get('blocks', []):
                block_id = block.get('block_id', 'unknown')
                types = block.get('types', [])
                reasoning = block.get('reasoning', '')
                logger.info(f"  Block '{block_id}':")
                logger.info(f"    Types: {types}")
                logger.info(f"    Reasoning: {reasoning}")
            logger.info("=" * 80)

            return strategy
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.error(f"Response content: {content}")
            # Fallback: create simple strategy
            return self._create_fallback_strategy(unique_labels)

    def _validate_strategy(self, strategy: dict, unique_labels: list[list[str]]) -> None:
        """Validate LLM-generated blocking strategy."""
        if "blocks" not in strategy:
            raise ValueError("Strategy missing 'blocks' key")

        # Check all types are covered
        all_types_in_strategy = set()
        for block in strategy["blocks"]:
            all_types_in_strategy.update(block["types"])

        all_types_in_input = set()
        for labels in unique_labels:
            all_types_in_input.update(labels)

        missing = all_types_in_input - all_types_in_strategy
        if missing:
            logger.warning(f"LLM strategy missing types: {missing}")

    def _create_fallback_strategy(self, unique_labels: list[list[str]]) -> dict:
        """Create simple fallback strategy if LLM fails."""
        logger.warning("Using fallback blocking strategy (each label combination = 1 block)")
        blocks = []
        for i, labels in enumerate(unique_labels):
            blocks.append({
                "block_id": f"block_{i:04d}",
                "types": labels,
                "reasoning": "Fallback: each label combination in separate block"
            })
        return {"blocks": blocks}

    def _apply_strategy(self, items: list[dict], strategy: dict) -> dict[str, list[dict]]:
        """
        Apply blocking strategy to group items.

        Args:
            items: List of entity items
            strategy: Blocking strategy from LLM

        Returns:
            Dict mapping block_id → list of items
        """
        # Build type → block_id mapping
        type_to_block = {}
        for block in strategy["blocks"]:
            block_id = block["block_id"]
            for typ in block["types"]:
                type_to_block[typ] = block_id

        # Group items by block
        blocks = defaultdict(list)
        for item in items:
            labels = item.get("payload", {}).get("labels", [])

            # Find which block this item belongs to
            # If item has multiple labels, use first matching block
            block_id = None
            for label in labels:
                if label in type_to_block:
                    block_id = type_to_block[label]
                    break

            if block_id is None:
                # No matching block, put in "unknown" block
                block_id = "unknown"
                logger.warning(f"Item {item['node_id']} with labels {labels} not matched to any block")

            blocks[block_id].append(item)

        return dict(blocks)
