JSON_OUTPUT = """
{
  "nodes": [
    {
      "id": "node_[sanitized_canonical_name]",
      "labels": ["<UPPER_CASE_ENTITY_LABEL>"],
      "properties": {
        "name": "<string>",
        "aliases": ["<string>"],
        "chunk_id": ["<string>"],
        "model_extracted": ["<string>"],
        "description": ["<string>"]
      }
    }
  ],
  "relationships": [
    {
      "id": "rel_[source_id]_[target_id]_[relationship_type]",
      "type": "<FREE_FORM_UPPER_CASE_RELATIONSHIP_TYPE>",
      "source": "<node_id>",
      "target": "<node_id>",
      "properties": {
        "chunk_id": ["<string>"],
        "model_extracted": ["<string>"],
        "description": ["<string>"]
      }
    }
  ]
}
"""

ENTITY_LABELS = """
Use only the following entity labels:

Core entity labels (recommended for standalone nodes):
- UNIVERSITY: A university or higher education institution as a whole.
- FACULTY: A faculty or school within a university.
- DEPARTMENT: An academic department.
- INSTITUTE: An institute or center within a university.
- LAB: A laboratory or research lab.
- ADMINISTRATIVE_UNIT: A non-academic office or administrative unit.
- PROGRAM: A degree or study program.
- COURSE: A course, module, or class.
- PERSON: Any identifiable person.
- EVENT: A conference, seminar, workshop, lecture, or university event.
- RESEARCH_PROJECT: A research project or funded project.
- RESEARCH_AREA: A research field, theme, or topic.
- PUBLICATION: A publication, paper, article, report, or thesis.
- DOCUMENT: A form, guideline, regulation, policy, handbook, or other document.
- SCHOLARSHIP: A scholarship, grant, or financial support program.
- PARTNERSHIP: A collaboration, partnership, or cooperation agreement.
- LOCATION: A city, campus, place, or geographic location.
- BUILDING: A building, campus building, or physical facility.
- ROOM: A room, office, or physical sub-location.
- WEBSITE: A website, portal, or online information resource.
- SYSTEM: A digital platform, portal, or software system.

Do NOT use as standalone entity labels unless there is a very strong reason:
- ROLE: Prefer as a property or relation of PERSON, not as an independent entity.
- ORGANIZATION_UNIT: Prefer specific labels such as FACULTY, DEPARTMENT, INSTITUTE, LAB, or ADMINISTRATIVE_UNIT instead of this generic label.

Labeling principles:
1. Prefer the most specific label available.
2. Only create an entity when it refers to a distinct real-world object.
3. The entity should usually have its own identity, attributes, or relationships.
4. If something is better represented as a property, relation, or description, do not create a separate entity.
5. Avoid generic or redundant nodes when a more specific label already captures the concept.
"""

EXTRACTION_PROMPT_TEMPLATE = """
You are an expert Knowledge Graph extraction system.

Extract entities and relationships from the provided text.

Important:
- Use only the allowed ENTITY LABELS.
- Relationship types are free-form, but must be short, reusable, semantic, and in UPPER_SNAKE_CASE.
- Return only valid JSON using the provided OUTPUT SCHEMA.
- Do not invent entities or relationships not supported by the text.
- Merge duplicate mentions of the same real-world entity within the same chunk.

## ENTITY LABELS
{entity_labels}
{context_sections}## ENTITY RULES
- Create a node only when the text supports a specific, meaningful, and stable real-world entity, or an official titled contextual entity such as a DOCUMENT, EVENT, PROCESS, NOTICE, or PUBLICATION.
- `labels` must contain exactly one allowed ENTITY LABEL.
- `id` format: "node_[canonical_name]".
- ID must be derived from the final properties.name of the same node (not from any earlier draft name).
- If properties.name is updated during extraction/merge, regenerate id accordingly before returning JSON.
- Use lowercase_with_underscores for the canonical_name part of the id.
- `name` must be the most specific canonical and stable name supported by the text.
- Prefer official names, proper names, or full document/event titles.
- Do NOT use generic or unresolved references as primary `name`, such as:
  - "nhà trường"
  - "trường"
  - "đơn vị"
  - "khoa"
  - "phòng"
  - "ban"
  - "người học"
  - "sinh viên"
- Do NOT use a loose action phrase as `name` unless it is clearly the official title of a DOCUMENT, EVENT, PROCESS, NOTICE, or CAMPAIGN.
- If the text only contains a generic mention and does not resolve it to a specific entity, do not create the entity.
- If a generic mention refers to an already identified entity in the same chunk, store it in `aliases` instead of creating a new node.
- `aliases` should contain abbreviations, acronyms, alternative names, translations, or coreferential mentions found in the text.
- Do not mix broad generic mentions and narrowly scoped subgroup names in the same entity unless the text clearly states they are equivalent.
- `chunk_id` must be exactly "{chunk_id}".
- `model_extracted` must be exactly "{model_name}".
- `description` must be concise, factual, and grounded in the text.

## RELATIONSHIP RULES
- Relationship types are not predefined.
- Generate short semantic relation types in UPPER_SNAKE_CASE.
- Prefer reusable relation names such as:
  - PART_OF
  - LOCATED_IN
  - OFFERS
  - PROVIDES
  - ORGANIZES
  - MANAGES
  - APPLIES_TO
  - ASSOCIATED_WITH
  - HAS_CONTACT_POINT
- Do not generate long sentence-like relationship names.
- Create a relationship only if the connection is explicitly supported by the text.
- `id` format: "rel_[source_id]_[target_id]_[relationship_type]".
- `source` must be the source node id.
- `target` must be the target node id.
- `chunk_id` must be exactly "{chunk_id}".
- `model_extracted` must be exactly "{model_name}".
- `description` MUST clearly articulate the exact semantic link between the source and target. Write a complete, descriptive sentence explaining HOW they interact based on the text (e.g., "The Faculty of Information Technology organizes the Annual AI Conference"). You MUST incorporate the context or snippet from the text that justifies this relationship directly into this description. Do NOT just write generic statements like "supported by text".

## IMPORTANT NOTE ON IDENTIFIERS
- id:
  - Use a local extraction identifier only, not a global canonical identifier.
  - For nodes, use: "node_[sanitized_canonical_name]".
  - For relationships, use: "rel_[source_id]_[target_id]_[relationship_type]".
  - `sanitized_canonical_name` must be lowercase, underscore-separated, and stripped of punctuation or unstable wording.
  - The id must be unique within the current extraction output.
  - Note: Entities with the same canonical name across different files will share the same ID and be automatically merged during preprocessing.

## OUTPUT SCHEMA
{json_output}

---BEGIN TEXT---
{text}
---END TEXT---
"""


def _cap_context(value: str | None, max_chars: int | None, truncation_suffix: str) -> str:
    if not value:
        return ""
    if not max_chars or len(value) <= max_chars:
        return value
    if max_chars <= len(truncation_suffix):
        return truncation_suffix[:max_chars]
    return value[: max_chars - len(truncation_suffix)] + truncation_suffix



def _build_context_sections(
    core_pack: str | None,
    local_context: str | None,
    rolling_summary: str | None,
    context_char_budget: int | None,
    truncation_suffix: str,
) -> str:
    if context_char_budget and context_char_budget > 0:
        section_budget = max(context_char_budget // 3, len(truncation_suffix) + 1)
    else:
        section_budget = None

    sections = []
    core_value = _cap_context(core_pack, section_budget, truncation_suffix)
    local_value = _cap_context(local_context, section_budget, truncation_suffix)
    summary_value = _cap_context(rolling_summary, section_budget, truncation_suffix)

    if core_value:
        sections.append(f"## CORE PACK\n{core_value}")
    if local_value:
        sections.append(f"## LOCAL CONTEXT\n{local_value}")
    if summary_value:
        sections.append(f"## ROLLING SUMMARY\n{summary_value}")

    return "\n\n".join(sections) + ("\n\n" if sections else "")



def get_extraction_prompt(
    text: str,
    chunk_id: str,
    model_name: str,
    core_pack: str | None = None,
    local_context: str | None = None,
    rolling_summary: str | None = None,
    context_char_budget: int | None = None,
    truncation_suffix: str = "...(truncated)",
) -> str:
    context_sections = _build_context_sections(
        core_pack=core_pack,
        local_context=local_context,
        rolling_summary=rolling_summary,
        context_char_budget=context_char_budget,
        truncation_suffix=truncation_suffix,
    )

    return EXTRACTION_PROMPT_TEMPLATE.format(
        entity_labels=ENTITY_LABELS,
        context_sections=context_sections,
        model_name=model_name,
        chunk_id=chunk_id,
        json_output=JSON_OUTPUT,
        text=text,
    )


__all__ = ["get_extraction_prompt"]