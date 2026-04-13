"""
LLM Clusterer - In-context Clustering Implementation

Implements LLM-based in-context clustering for entity resolution.
Uses LLM to group entities within a record set.
"""

from __future__ import annotations

import json
import re
import numpy as np
from typing import Any


CLUSTERING_PROMPT_TEMPLATE = """You are an expert in entity resolution for Vietnamese knowledge graphs.

Task: Group these {n} {entity_type} records into clusters where each cluster represents the SAME real-world entity.

Records:
{records_formatted}

Guidelines for merging:
1. **MERGE if**: Different source documents + name/alias overlap + refer to same real-world entity
   - Name variations (abbreviations, full names, with/without prefixes/suffixes) are NORMAL for same entity
   - Example patterns: "Công ty A" vs "Công ty TNHH A", "TS. Nguyễn Văn B" vs "Nguyễn Văn B"
   - Cross-document duplicates with similar names → LIKELY same entity

2. **DO NOT MERGE if**: Same source_document_id (one document rarely mentions same entity multiple times)

3. **DO NOT MERGE if**: Clearly different entities despite similar names
   - Check context clues: different roles, different time periods, different locations

Decision strategy:
- Primary question: Does this refer to the SAME real-world entity?
- Name variations are EXPECTED and should NOT prevent merging
- Be confident in merging when names overlap significantly
- Only separate if there's clear evidence they are different entities

Output JSON format:
{{
  "groups": [
    {{
      "group_id": "g0",
      "node_ids": ["node_1", "node_2", "node_3"],
      "reasoning": "Brief explanation why these belong together"
    }}
  ],
  "confidence": 0.95
}}

Return ONLY valid JSON, no markdown, no extra text."""


class LLMClusterer:
    """
    LLM-based in-context clustering for entity resolution.

    Uses LLM to analyze a record set and group entities that
    represent the same real-world entity.
    """

    def __init__(self, llm_provider: str, llm_model: str, llm_api_key: str | None = None):
        """
        Initialize LLMClusterer.

        Args:
            llm_provider: LLM provider (openai, anthropic)
            llm_model: Model name
            llm_api_key: API key (optional, can use environment variable)
        """
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        self._llm_client = None

    def _get_llm_client(self) -> Any:
        """Get or create LLM client."""
        if self._llm_client is None:
            from services.llms import get_llm

            self._llm_client = get_llm(
                self.llm_provider,
                model_name=self.llm_model,
                api_key=self.llm_api_key,
            )
        return self._llm_client

    def cluster_record_set(
        self,
        record_set: list[dict],
        entity_type: str,
        embeddings: dict[str, list[float]] | None = None,
    ) -> dict:
        """
        Cluster record set using LLM.

        Args:
            record_set: List of entity items to cluster
            entity_type: Entity type (PERSON, ORGANIZATIONAL_UNIT, etc.)
            embeddings: Optional embeddings for conservative fallback

        Returns:
            Dictionary with:
            - groups: List of groups, each with group_id, node_ids, reasoning
            - confidence: Overall confidence score (0.0-1.0)
        """
        # Build prompt
        prompt = self._build_prompt(record_set, entity_type)

        # Call LLM
        try:
            llm = self._get_llm_client()
            response = llm.generate(
                prompt=prompt,
                system_prompt="You are an entity resolution expert. Return only valid JSON.",
            )

            # Extract content
            content = response.content if hasattr(response, "content") else str(response)

            # Debug: log raw response
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"LLM raw response: {content[:500]}")

            # Parse response
            result = self._parse_response(content, record_set)

            return result

        except Exception as e:
            # Use conservative fallback instead of all-singleton
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"LLM call failed: {e}")
            return self._build_conservative_fallback(
                record_set=record_set,
                embeddings=embeddings or {},
                similarity_threshold=0.88,
            )

    def _build_prompt(self, record_set: list[dict], entity_type: str) -> str:
        """
        Build in-context clustering prompt.

        Args:
            record_set: List of entity items
            entity_type: Entity type

        Returns:
            Formatted prompt string
        """
        # Format records
        records_formatted = []
        for i, item in enumerate(record_set, 1):
            node_id = item.get("node_id", "")
            props = item.get("payload", {}).get("properties", {})

            name = props.get("name", "")
            aliases = props.get("aliases", [])
            source = props.get("source_document_id", "")
            evidence = props.get("evidence_text", "")

            record_str = f"""Record {i}:
  ID: {node_id}
  Name: {name}
  Aliases: {', '.join(aliases) if aliases else 'None'}
  Source: {source}
  Evidence: {evidence[:200] if evidence else 'None'}"""

            records_formatted.append(record_str)

        records_text = "\n\n".join(records_formatted)

        # Fill template
        prompt = CLUSTERING_PROMPT_TEMPLATE.format(
            n=len(record_set),
            entity_type=entity_type,
            records_formatted=records_text,
        )

        return prompt

    def _parse_response(self, response: str, record_set: list[dict]) -> dict:
        """
        Parse and validate LLM response.

        Args:
            response: Raw LLM response
            record_set: Original record set (for validation)

        Returns:
            Validated clustering result
        """
        # Extract JSON from response
        parsed = self._extract_json(response)

        if not parsed:
            # Fallback: each entity in separate group (parse failed)
            return {
                "groups": [
                    {
                        "group_id": f"g{i}",
                        "node_ids": [item["node_id"]],
                        "reasoning": "JSON parse failed",
                    }
                    for i, item in enumerate(record_set)
                ],
                "confidence": 0.0,
                "error": "Failed to parse JSON",
            }

        # Validate and clean groups
        groups = parsed.get("groups", [])
        if not isinstance(groups, list):
            groups = []

        # Get valid node IDs
        valid_node_ids = {item["node_id"] for item in record_set}

        # Clean and validate groups
        cleaned_groups = []
        seen_nodes = set()

        for i, group in enumerate(groups):
            if not isinstance(group, dict):
                continue

            group_id = group.get("group_id", f"g{i}")
            node_ids = group.get("node_ids", [])
            reasoning = group.get("reasoning", "")

            # Filter valid and unseen node IDs
            valid_ids = [
                nid
                for nid in node_ids
                if nid in valid_node_ids and nid not in seen_nodes
            ]

            if valid_ids:
                cleaned_groups.append({
                    "group_id": str(group_id),
                    "node_ids": valid_ids,
                    "reasoning": str(reasoning),
                })
                seen_nodes.update(valid_ids)

        # Add any missing nodes as singletons
        missing_nodes = valid_node_ids - seen_nodes
        for i, node_id in enumerate(missing_nodes):
            cleaned_groups.append({
                "group_id": f"g_missing_{i}",
                "node_ids": [node_id],
                "reasoning": "Not assigned by LLM",
            })

        # Get confidence
        confidence = parsed.get("confidence", 0.7)
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (TypeError, ValueError):
            confidence = 0.7

        return {
            "groups": cleaned_groups,
            "confidence": confidence,
        }

    def _extract_json(self, raw: str) -> dict | None:
        """
        Extract JSON from LLM response.

        Handles markdown code blocks and other formatting.

        Args:
            raw: Raw response string

        Returns:
            Parsed JSON dict or None if parsing fails
        """
        if not raw:
            return None

        content = raw.strip()

        # Try to extract from markdown code block
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", content, re.DOTALL)
        if match:
            content = match.group(1)

        # Try direct JSON parse
        try:
            parsed = json.loads(content)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            pass

        # Try to find JSON object in text
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return None

        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            return None

    def _build_conservative_fallback(
        self,
        record_set: list[dict],
        embeddings: dict[str, list[float]],
        similarity_threshold: float = 0.88,
    ) -> dict:
        """
        Conservative fallback: merge only high-confidence pairs.

        Rules:
        1. Only merge if cosine similarity >= threshold (default 0.88)
        2. Only merge if name/alias overlap exists
        3. Never merge same source_document_id
        4. If no pairs meet criteria, return singletons

        Args:
            record_set: List of entity items to cluster
            embeddings: Dictionary mapping node_id to embedding vector
            similarity_threshold: Minimum cosine similarity for merge (default 0.88)

        Returns:
            Clustering result with conservative merges
        """
        # Extract node info
        nodes = []
        for item in record_set:
            node_id = item["node_id"]
            props = item.get("payload", {}).get("properties", {})
            aliases = props.get("aliases") or []
            nodes.append({
                "node_id": node_id,
                "name": props.get("name", "").lower().strip(),
                "aliases": [a.lower().strip() for a in aliases],
                "source_doc": props.get("source_document_id", ""),
                "vector": embeddings.get(node_id, []),
            })

        # Find high-confidence pairs
        merged_groups = []
        used_nodes = set()

        for i in range(len(nodes)):
            if nodes[i]["node_id"] in used_nodes:
                continue

            group = [nodes[i]["node_id"]]

            for j in range(i + 1, len(nodes)):
                if nodes[j]["node_id"] in used_nodes:
                    continue

                # Rule 1: Different source documents
                if nodes[i]["source_doc"] == nodes[j]["source_doc"]:
                    continue

                # Rule 2: High similarity
                if nodes[i]["vector"] and nodes[j]["vector"]:
                    vec_i = np.array(nodes[i]["vector"])
                    vec_j = np.array(nodes[j]["vector"])
                    norm_i = np.linalg.norm(vec_i)
                    norm_j = np.linalg.norm(vec_j)

                    if norm_i == 0 or norm_j == 0:
                        continue

                    sim = np.dot(vec_i, vec_j) / (norm_i * norm_j)

                    if sim < similarity_threshold:
                        continue
                else:
                    continue

                # Rule 3: Name/alias overlap (improved with substring matching)
                names_i = {nodes[i]["name"]} | set(nodes[i]["aliases"])
                names_j = {nodes[j]["name"]} | set(nodes[j]["aliases"])

                # Remove empty strings
                names_i = {n for n in names_i if n}
                names_j = {n for n in names_j if n}

                # Check for overlap: exact match OR substring match
                has_overlap = False

                # Check exact match first
                if names_i & names_j:
                    has_overlap = True
                else:
                    # Check substring match (one name contains another)
                    for name_i in names_i:
                        for name_j in names_j:
                            # Check if one is substring of another (case-insensitive)
                            if name_i in name_j or name_j in name_i:
                                has_overlap = True
                                break
                        if has_overlap:
                            break

                if not has_overlap:
                    continue

                # All rules passed: merge
                group.append(nodes[j]["node_id"])
                used_nodes.add(nodes[j]["node_id"])

            used_nodes.add(nodes[i]["node_id"])
            merged_groups.append(group)

        # Build result
        groups = []
        for idx, node_ids in enumerate(merged_groups):
            reasoning = "Conservative fallback merge" if len(node_ids) > 1 else "Conservative fallback singleton"
            groups.append({
                "group_id": f"g{idx}",
                "node_ids": node_ids,
                "reasoning": reasoning,
            })

        return {
            "groups": groups,
            "confidence": 0.6,  # Lower confidence for fallback
            "fallback": "conservative",
        }
