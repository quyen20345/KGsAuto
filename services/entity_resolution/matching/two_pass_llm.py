"""
Two-Pass LLM Entity Resolution

Pass 1: Sub-clustering - Phân nhóm entities thành sub-groups
Pass 2: Canonical Synthesis - Merge từng sub-group thành canonical entity

Approach này đơn giản hơn và hiệu quả hơn so với NRS + MDG + CMR.
"""

from __future__ import annotations

import json
import re
import numpy as np
from typing import Any
import logging


class TwoPassLLMResolver:
    """
    Two-Pass LLM Entity Resolution.

    Pass 1: LLM phân tích cluster và chia thành sub-groups
    Pass 2: LLM merge mỗi sub-group thành canonical entity
    """

    def __init__(
        self,
        llm_provider: str,
        llm_model: str,
        llm_api_key: str | None = None,
        conservative_threshold: float = 0.88,
    ):
        """
        Initialize TwoPassLLMResolver.

        Args:
            llm_provider: LLM provider (proxypal, 9router, gemini, etc.)
            llm_model: Model name
            llm_api_key: API key (optional)
            conservative_threshold: Threshold for conservative fallback
        """
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.llm_api_key = llm_api_key
        self.conservative_threshold = conservative_threshold
        self._llm_client = None
        self.logger = logging.getLogger(__name__)

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

    def resolve_cluster(
        self,
        cluster_entities: list[dict],
        embeddings: dict[str, list[float]],
        entity_type: str = "UNKNOWN",
    ) -> list[dict]:
        """
        Main entry point: Resolve cluster using 2-pass approach.

        Args:
            cluster_entities: List of entities in cluster
            embeddings: Dict mapping node_id to embedding vector
            entity_type: Entity type (PERSON, ORGANIZATIONAL_UNIT, etc.)

        Returns:
            List of canonical entities (or original entities if fallback)
        """
        self.logger.info(f"  Resolving cluster with {len(cluster_entities)} entities (type: {entity_type})")

        # Pass 1: Sub-clustering
        self.logger.info("    Pass 1: Sub-clustering")
        pass1_result = self._pass1_subclustering(cluster_entities, entity_type)

        # Validate Pass 1
        if self._is_all_singletons(pass1_result):
            self.logger.warning("    Pass 1 returned all singletons, using conservative fallback")
            return self._conservative_fallback(cluster_entities, embeddings)

        # Validate sub-groups bằng embedding similarity
        if not self._validate_subgroups(pass1_result, embeddings):
            self.logger.warning("    Pass 1 sub-groups validation failed, using conservative fallback")
            return self._conservative_fallback(cluster_entities, embeddings)

        self.logger.info(f"    Pass 1 success: {len(pass1_result['sub_groups'])} sub-groups, {len(pass1_result.get('singletons', []))} singletons")

        # Pass 2: Merge mỗi sub-group
        self.logger.info("    Pass 2: Canonical synthesis")
        canonical_entities = []

        for sub_group in pass1_result['sub_groups']:
            entity_ids = sub_group.get('entity_ids', [])

            if len(entity_ids) == 1:
                # Singleton, giữ nguyên
                canonical_entities.append(self._keep_singleton_by_id(entity_ids[0], cluster_entities))
            else:
                # Merge thành canonical entity
                canonical = self._pass2_merge(sub_group, cluster_entities, entity_type)
                if canonical:
                    canonical_entities.append(canonical)
                else:
                    # Pass 2 failed, giữ nguyên entities
                    for eid in entity_ids:
                        canonical_entities.append(self._keep_singleton_by_id(eid, cluster_entities))

        # Xử lý singletons từ Pass 1
        for singleton_id in pass1_result.get('singletons', []):
            canonical_entities.append(self._keep_singleton_by_id(singleton_id, cluster_entities))

        self.logger.info(f"    Pass 2 complete: {len(canonical_entities)} canonical entities")

        return canonical_entities

    def _pass1_subclustering(self, cluster_entities: list[dict], entity_type: str) -> dict:
        """
        Pass 1: LLM phân nhóm entities.

        Args:
            cluster_entities: List of entities
            entity_type: Entity type

        Returns:
            Dict with sub_groups and singletons
        """
        prompt = self._build_pass1_prompt(cluster_entities, entity_type)

        try:
            llm = self._get_llm_client()
            response = llm.generate(
                prompt=prompt,
                system_prompt="You are an entity resolution expert. Return only valid JSON.",
            )

            content = response.content if hasattr(response, "content") else str(response)

            # Parse response
            result = self._parse_pass1_response(content, cluster_entities)

            return result

        except Exception as e:
            self.logger.error(f"Pass 1 LLM call failed: {e}")
            # Return all singletons
            return {
                "sub_groups": [],
                "singletons": [e["node_id"] for e in cluster_entities],
                "confidence": 0.0,
            }

    def _pass2_merge(
        self,
        sub_group: dict,
        cluster_entities: list[dict],
        entity_type: str,
    ) -> dict | None:
        """
        Pass 2: LLM merge entities trong sub-group.

        Args:
            sub_group: Sub-group from Pass 1
            cluster_entities: All entities in cluster
            entity_type: Entity type

        Returns:
            Canonical entity dict or None if failed
        """
        entity_ids = sub_group.get('entity_ids', [])

        # Lấy entities trong sub-group
        entities = [e for e in cluster_entities if e['node_id'] in entity_ids]

        if not entities:
            return None

        prompt = self._build_pass2_prompt(entities, entity_type)

        try:
            llm = self._get_llm_client()
            response = llm.generate(
                prompt=prompt,
                system_prompt="You are an entity resolution expert. Return only valid JSON.",
            )

            content = response.content if hasattr(response, "content") else str(response)

            # Parse response
            canonical = self._parse_pass2_response(content, entities)

            return canonical

        except Exception as e:
            self.logger.error(f"Pass 2 LLM call failed: {e}")
            return None

    def _build_pass1_prompt(self, entities: list[dict], entity_type: str) -> str:
        """Build prompt cho Pass 1."""
        entities_formatted = self._format_entities_for_prompt(entities)

        prompt = f"""Task: Phân tích {len(entities)} entities và chia thành các sub-groups.

Mỗi sub-group chứa các entities đại diện cho CÙNG MỘT thực thể trong thế giới thực.

Entity Type: {entity_type}

Entities:
{entities_formatted}

Guidelines:
1. Tìm các entities có name/alias giống nhau hoặc tương tự
2. Kiểm tra context: cùng role, cùng organization, cùng time period
3. Entities từ cùng source_document CÓ THỂ là cùng entity (nếu có vai trò khác nhau)
4. Nếu không chắc chắn → Tách riêng (đừng merge sai)
5. Ít nhất phải có 1 sub-group với 2+ entities (trừ khi thực sự tất cả khác nhau)

Output JSON format:
{{
  "sub_groups": [
    {{
      "group_id": "g0",
      "entity_ids": ["node_id_1", "node_id_2", "node_id_3"],
      "reasoning": "Cùng tên 'Nguyễn Văn A', cùng là Giảng viên"
    }},
    {{
      "group_id": "g1",
      "entity_ids": ["node_id_4", "node_id_5"],
      "reasoning": "Cùng tên 'Trần Thị B'"
    }}
  ],
  "singletons": ["node_id_6", "node_id_7", "node_id_8"],
  "confidence": 0.85
}}

Return ONLY valid JSON, no markdown, no extra text."""

        return prompt

    def _build_pass2_prompt(self, entities: list[dict], entity_type: str) -> str:
        """Build prompt cho Pass 2."""
        entities_formatted = self._format_entities_for_prompt(entities)

        prompt = f"""Task: Merge {len(entities)} entities thành 1 canonical entity.

Entity Type: {entity_type}

Entities (đã được xác nhận là cùng 1 thực thể):
{entities_formatted}

Guidelines:
1. Chọn canonical_id: Ưu tiên entity có thông tin đầy đủ nhất
2. Merge labels: Union tất cả labels
3. Merge properties:
   - name: Chọn tên đầy đủ nhất (ưu tiên có học hàm/chức danh cho PERSON)
   - aliases: Union tất cả names và aliases
   - email: Chọn email hợp lệ
   - Các fields khác: Ưu tiên giá trị chi tiết nhất, không conflict

Output JSON format:
{{
  "canonical_id": "node_id_1",
  "labels": ["PERSON", "LECTURER"],
  "properties": {{
    "name": "TS. Nguyễn Văn A",
    "aliases": ["Nguyễn Văn A", "NVA", "TS. A"],
    "role": "Giảng viên",
    "email": "nva@vnu.edu.vn"
  }},
  "merged_from": ["node_id_1", "node_id_2", "node_id_3"]
}}

Return ONLY valid JSON, no markdown, no extra text."""

        return prompt

    def _format_entities_for_prompt(self, entities: list[dict]) -> str:
        """Format entities for LLM prompt."""
        lines = []

        for i, entity in enumerate(entities, 1):
            node_id = entity.get("node_id", "unknown")
            payload = entity.get("payload", {})
            props = payload.get("properties", {})

            name = props.get("name", "N/A")
            aliases = props.get("aliases") or []
            source_doc = props.get("source_document_id", "N/A")
            evidence = props.get("evidence_text", "")

            lines.append(f"{i}. ID: {node_id}")
            lines.append(f"   Name: {name}")
            if aliases:
                lines.append(f"   Aliases: {aliases}")
            lines.append(f"   Source: {source_doc}")
            if evidence:
                lines.append(f"   Evidence: {evidence[:200]}")
            lines.append("")

        return "\n".join(lines)

    def _parse_pass1_response(self, content: str, cluster_entities: list[dict]) -> dict:
        """Parse Pass 1 LLM response."""
        # Extract JSON
        parsed = self._extract_json(content)

        if not parsed:
            # Parse failed, return all singletons
            return {
                "sub_groups": [],
                "singletons": [e["node_id"] for e in cluster_entities],
                "confidence": 0.0,
            }

        # Validate and clean
        sub_groups = parsed.get("sub_groups", [])
        singletons = parsed.get("singletons", [])
        confidence = parsed.get("confidence", 0.7)

        # Get valid node IDs
        valid_node_ids = {e["node_id"] for e in cluster_entities}

        # Clean sub_groups
        cleaned_groups = []
        seen_nodes = set()

        for group in sub_groups:
            if not isinstance(group, dict):
                continue

            entity_ids = group.get("entity_ids", [])

            # Filter valid and unseen IDs
            valid_ids = [
                eid for eid in entity_ids
                if eid in valid_node_ids and eid not in seen_nodes
            ]

            if len(valid_ids) > 0:
                cleaned_groups.append({
                    "group_id": group.get("group_id", f"g{len(cleaned_groups)}"),
                    "entity_ids": valid_ids,
                    "reasoning": group.get("reasoning", ""),
                })
                seen_nodes.update(valid_ids)

        # Clean singletons
        cleaned_singletons = [
            sid for sid in singletons
            if sid in valid_node_ids and sid not in seen_nodes
        ]
        seen_nodes.update(cleaned_singletons)

        # Add missing nodes as singletons
        missing = valid_node_ids - seen_nodes
        cleaned_singletons.extend(missing)

        return {
            "sub_groups": cleaned_groups,
            "singletons": cleaned_singletons,
            "confidence": confidence,
        }

    def _parse_pass2_response(self, content: str, entities: list[dict]) -> dict | None:
        """Parse Pass 2 LLM response."""
        # Extract JSON
        parsed = self._extract_json(content)

        if not parsed:
            return None

        # Extract fields
        canonical_id = parsed.get("canonical_id")
        labels = parsed.get("labels", [])
        properties = parsed.get("properties", {})
        merged_from = parsed.get("merged_from", [])

        if not canonical_id:
            # Use first entity as canonical
            canonical_id = entities[0]["node_id"]

        if not merged_from:
            merged_from = [e["node_id"] for e in entities]

        return {
            "canonical_id": canonical_id,
            "labels": labels if isinstance(labels, list) else [],
            "properties": properties if isinstance(properties, dict) else {},
            "merged_from": merged_from if isinstance(merged_from, list) else [],
        }

    def _extract_json(self, raw: str) -> dict | None:
        """Extract JSON from LLM response."""
        # Remove markdown code blocks
        cleaned = raw.replace("```json", "").replace("```", "").strip()

        # Remove thinking tags
        if "<think>" in cleaned and "</think>" in cleaned:
            cleaned = cleaned.split("</think>", 1)[1].strip()

        # Try to find JSON object
        match = re.search(r'\{.*\}', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        # Try direct parse
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return None

    def _is_all_singletons(self, pass1_result: dict) -> bool:
        """Check if Pass 1 returned all singletons."""
        sub_groups = pass1_result.get("sub_groups", [])

        # Check if any sub-group has 2+ entities
        has_multi_entity_group = any(
            len(g.get("entity_ids", [])) > 1 for g in sub_groups
        )

        return not has_multi_entity_group

    def _validate_subgroups(
        self,
        pass1_result: dict,
        embeddings: dict[str, list[float]],
        min_intra_similarity: float = 0.70,
    ) -> bool:
        """Validate sub-groups bằng embedding similarity."""
        sub_groups = pass1_result.get("sub_groups", [])

        for group in sub_groups:
            entity_ids = group.get("entity_ids", [])

            if len(entity_ids) < 2:
                continue

            # Get vectors
            vectors = [embeddings[eid] for eid in entity_ids if eid in embeddings]

            if len(vectors) < 2:
                continue

            # Compute intra-group similarity
            intra_sim = self._compute_intra_similarity(vectors)

            # If too low, sub-group is suspicious
            if intra_sim < min_intra_similarity:
                self.logger.warning(f"      Sub-group validation failed: intra_sim={intra_sim:.3f} < {min_intra_similarity}")
                return False

        return True

    def _compute_intra_similarity(self, vectors: list[list[float]]) -> float:
        """Compute average pairwise similarity within group."""
        if len(vectors) < 2:
            return 1.0

        vectors_array = np.array(vectors)

        # Normalize
        norms = np.linalg.norm(vectors_array, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        normalized = vectors_array / norms

        # Compute similarity matrix
        sim_matrix = np.dot(normalized, normalized.T)

        # Extract upper triangle (avoid diagonal)
        n = len(vectors)
        similarities = []
        for i in range(n):
            for j in range(i + 1, n):
                similarities.append(sim_matrix[i, j])

        return float(np.mean(similarities)) if similarities else 1.0

    def _keep_singleton_by_id(self, node_id: str, cluster_entities: list[dict]) -> dict:
        """Keep entity as singleton (no merge)."""
        entity = next((e for e in cluster_entities if e["node_id"] == node_id), None)

        if not entity:
            return {
                "canonical_id": node_id,
                "labels": [],
                "properties": {},
                "merged_from": [node_id],
            }

        payload = entity.get("payload", {})

        return {
            "canonical_id": node_id,
            "labels": payload.get("labels", []),
            "properties": payload.get("properties", {}),
            "merged_from": [node_id],
        }

    def _conservative_fallback(
        self,
        cluster_entities: list[dict],
        embeddings: dict[str, list[float]],
    ) -> list[dict]:
        """
        Conservative fallback: rule-based merging.

        Rules:
        1. Only merge if cosine similarity >= threshold (default 0.88)
        2. Only merge if name/alias overlap exists
        3. If no pairs meet criteria, return singletons
        """
        self.logger.info("      Using conservative fallback")

        # Extract node info
        nodes = []
        for item in cluster_entities:
            node_id = item["node_id"]
            props = item.get("payload", {}).get("properties", {})
            aliases = props.get("aliases") or []
            nodes.append({
                "node_id": node_id,
                "name": props.get("name", "").lower().strip(),
                "aliases": [a.lower().strip() for a in aliases],
                "vector": embeddings.get(node_id, []),
                "payload": item.get("payload", {}),
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

                # Rule 1: High similarity
                if nodes[i]["vector"] and nodes[j]["vector"]:
                    vec_i = np.array(nodes[i]["vector"])
                    vec_j = np.array(nodes[j]["vector"])
                    norm_i = np.linalg.norm(vec_i)
                    norm_j = np.linalg.norm(vec_j)

                    if norm_i == 0 or norm_j == 0:
                        continue

                    sim = np.dot(vec_i, vec_j) / (norm_i * norm_j)

                    if sim < self.conservative_threshold:
                        continue
                else:
                    continue

                # Rule 2: Name/alias overlap
                names_i = {nodes[i]["name"]} | set(nodes[i]["aliases"])
                names_j = {nodes[j]["name"]} | set(nodes[j]["aliases"])

                # Remove empty
                names_i = {n for n in names_i if n}
                names_j = {n for n in names_j if n}

                # Check overlap
                has_overlap = False

                if names_i & names_j:
                    has_overlap = True
                else:
                    # Check substring match
                    for name_i in names_i:
                        for name_j in names_j:
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

        # Build canonical entities
        canonical_entities = []

        for group in merged_groups:
            if len(group) == 1:
                # Singleton
                canonical_entities.append(self._keep_singleton_by_id(group[0], cluster_entities))
            else:
                # Merge group
                entities_in_group = [e for e in cluster_entities if e["node_id"] in group]
                canonical = self._merge_entities_rule_based(entities_in_group)
                canonical_entities.append(canonical)

        return canonical_entities

    def _merge_entities_rule_based(self, entities: list[dict]) -> dict:
        """Merge entities using rule-based approach."""
        if not entities:
            return {
                "canonical_id": "unknown",
                "labels": [],
                "properties": {},
                "merged_from": [],
            }

        # Pick first as canonical
        canonical_id = entities[0]["node_id"]

        # Merge labels
        all_labels = []
        for e in entities:
            for label in e.get("payload", {}).get("labels", []):
                if label not in all_labels:
                    all_labels.append(label)

        # Merge properties
        merged_props = {}
        for e in entities:
            props = e.get("payload", {}).get("properties", {})
            for key, val in props.items():
                if val is None:
                    continue

                existing = merged_props.get(key)
                if existing is None:
                    merged_props[key] = val
                    continue

                if isinstance(existing, list):
                    merged = list(existing)
                    if isinstance(val, list):
                        for item in val:
                            if item not in merged:
                                merged.append(item)
                    elif val not in merged:
                        merged.append(val)
                    merged_props[key] = merged
                else:
                    # Prefer longer/more detailed value
                    if val and (not existing or len(str(val)) > len(str(existing))):
                        merged_props[key] = val

        return {
            "canonical_id": canonical_id,
            "labels": all_labels,
            "properties": merged_props,
            "merged_from": [e["node_id"] for e in entities],
        }
