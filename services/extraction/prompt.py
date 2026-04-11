JSON_OUTPUT = """
{
  "nodes": [
    {
      "id": "node_[LABEL]_[snake_case_name]",
      "labels": ["<UPPER_CASE_LABEL>"],
      "properties": {
        "name": "<string>",
        "aliases": ["<string>"] | null,
        "source_document_id": "<string>",
        "model_extracted": "<string>",
        "evidence_text": "<string>" | null,
        "<key_others>": "<string | number | boolean | array | null>"
      }
    }
  ],
  "relationships": [
    {
      "id": "rel_[source_id]_[type]_[target_id]",
      "type": "<ALLOWED_RELATIONSHIP_TYPE>",
      "source": "<node_id>",
      "target": "<node_id>",
      "properties": {
        "source_document_id": "<string>",
        "model_extracted": "<string>",
        "evidence_text": "<string>" | null,
        "<key_others>": "<string | number | boolean | array | null>"
      }
    }
  ]
}
"""


OBJECTS = """
UNIVERSITY
ORGANIZATIONAL_UNIT
PERSON
ROLE
STUDY_PROGRAM
COURSE
DEGREE
RESEARCH_PROJECT
PUBLICATION
ADMISSION_METHOD
SCHOLARSHIP
SERVICE
CAMPUS
BUILDING
ROOM
CONTACT_DETAILS
DOCUMENT
ANNOUNCEMENT
"""


RELATIONSHIP_TYPES = """
HAS_UNIT
SUBUNIT_OF
MEMBER_OF
HAS_ROLE
OFFERS_PROGRAM
HAS_DEGREE
HAS_CURRICULUM
INCLUDES_COURSE
USES_ADMISSION_METHOD
REQUIRES_DOCUMENT
REQUIRES_FORM
REGULATED_BY
HAS_DEADLINE
PROVIDES_SERVICE
CONDUCTS_PROJECT
PRODUCES_PUBLICATION
COLLABORATES_WITH
LOCATED_IN
HAS_CONTACT_DETAILS
MAINTAINS_WEBSITE
PUBLISHES
"""


NODE_RULES = """
- id:
  - A semantic unique identifier.
  - MUST follow this exact format: `node_[LABEL]_[snake_case_name]`.
  - `LABEL` must match the primary label in `labels`.
  - `snake_case_name` must be derived from the canonical `name`, not from an alias.

- labels:
  - Must be an array containing exactly 1 label.
  - The label must be one of the allowed ENTITY LABELS.
  - Must be in UPPER CASE.

- properties:
  - name:
    - The primary official name of the entity as a string.
    - Use the most specific canonical real-world entity name supported by the text.
  - aliases:
    - An array of strings containing alternative names, acronyms, abbreviations, translations, or coreferences.
    - If no aliases are explicitly supported, set to null.
  - source_document_id:
    - MANDATORY.
    - Always set this value to the exact string: "{doc_id}".
  - model_extracted:
    - MANDATORY.
    - Always set this value to the exact string: "{model_name}".
  - evidence_text:
    - MANDATORY.
    - A short exact text span that directly supports the existence or naming of the entity.
    - Prefer a verbatim span from the source text.
    - If no short supporting span can be isolated, set to null.
  - key_others:
    - Only extract real-world semantic properties of the entity.
    - Examples: `email`, `phone`, `address`, `founded_year`, `code`.
    - Use snake_case keys.
    - Values must be primitive JSON values or arrays.
    - Do not create nested objects, dicts, or maps.
    - Only include properties explicitly supported by the text or metadata.
"""


RELATIONSHIP_RULES = """
- id:
  - A semantic unique identifier for the edge.
  - MUST follow this exact format: `rel_[source_id]_[type]_[target_id]`.

- type:
  - Must be a string in UPPER_SNAKE_CASE.
  - Must be one of the allowed RELATIONSHIP TYPES.
  - Do not invent new relationship types.

- source:
  - The `id` of the originating node.
  - Must strictly exist in the nodes array.

- target:
  - The `id` of the destination node.
  - Must strictly exist in the nodes array.

- properties:
  - source_document_id:
    - MANDATORY.
    - Always set this value to the exact string: "{doc_id}".
  - model_extracted:
    - MANDATORY.
    - Always set this value to the exact string: "{model_name}".
  - evidence_text:
    - MANDATORY.
    - A short exact text span that directly supports the relationship.
    - Prefer a verbatim span from the source text.
    - If no short supporting span can be isolated, set to null.
  - key_others:
    - Additional edge context must use snake_case formatting.
    - Examples: `role_title`, `start_year`, `end_year`, `confidence_score`.
    - Values must be primitive JSON values or arrays.
    - Do not create nested objects, dicts, or maps.
    - Only include context explicitly supported by the text or metadata.
"""


INSTRUCTIONS = """
1. ZERO HALLUCINATION
Only extract entities, aliases, properties, and relationships that are explicitly supported by the source text or metadata.
Never invent facts, dates, URLs, aliases, labels, or relationships.
When a field is missing, set it to null.

2. CANONICAL ENTITY RESOLUTION
Do not use pronouns or vague generic mentions as node names.
Resolve mentions such as "it", "they", "the university", "the faculty", "nhà trường", "khoa", "trường" to the most specific official entity name supported by context.
Use the canonical official name in `name`.

3. ENTITY DEDUPLICATION
Create only one node per real-world entity within the same extraction.
Merge abbreviations, acronyms, alternate spellings, translations, and shortened mentions into the same node.
Store these alternate mentions in `aliases`.

4. LABEL DISCIPLINE
Use only labels from the allowed ENTITY LABELS list.
Assign exactly one label per node.
Choose the most specific label supported by the text.
Do not create overly generic nodes when a more precise real-world entity is available.

5. ORGANIZATIONAL LABEL MAPPING
Use these label rules consistently:
- UNIVERSITY: the top-level university entity
- ORGANIZATIONAL_UNIT: faculty, school, department, center, institute, office, college, lab, division, or any named sub-unit
- PERSON: any named individual person
- ROLE: named or specific organizational/academic role when it appears as an entity worth preserving
- STUDY_PROGRAM: named major, program, curriculum, subject area, or training program
- COURSE: named course, module, class, or subject instance in curriculum context
- DEGREE: degree type or named degree designation
- RESEARCH_PROJECT: named project, grant, task, or research program
- PUBLICATION: paper, article, thesis, patent, report, or publication-like output
- ADMISSION_METHOD: named admission route, scheme, quota category, or selection method
- SCHOLARSHIP: named scholarship or funding support program
- SERVICE: named service, support offering, or administrative/student-facing service
- CAMPUS: named campus or site
- BUILDING: named building or block
- ROOM: named room, lab room, office room, classroom, hall
- CONTACT_DETAILS: named contact point, hotline, office contact, email contact entity
- DOCUMENT: named document, regulation, form, guideline, notice file
- ANNOUNCEMENT: named announcement, notice, call, event posting

6. RELATIONSHIP DISCIPLINE
Use only relationship types from the allowed RELATIONSHIP TYPES list.
Each relationship must represent exactly one atomic fact between exactly two valid nodes.
Do not create inferred, approximate, or composite relationships.

7. RELATIONSHIP DIRECTION
Use these preferred directions:
- UNIVERSITY HAS_UNIT ORGANIZATIONAL_UNIT
- ORGANIZATIONAL_UNIT SUBUNIT_OF UNIVERSITY or ORGANIZATIONAL_UNIT
- PERSON MEMBER_OF ORGANIZATIONAL_UNIT
- PERSON HAS_ROLE ROLE
- ORGANIZATIONAL_UNIT OFFERS_PROGRAM STUDY_PROGRAM
- STUDY_PROGRAM HAS_DEGREE DEGREE
- STUDY_PROGRAM HAS_CURRICULUM DOCUMENT
- DOCUMENT INCLUDES_COURSE COURSE
- STUDY_PROGRAM USES_ADMISSION_METHOD ADMISSION_METHOD
- STUDY_PROGRAM REQUIRES_DOCUMENT DOCUMENT
- SERVICE REQUIRES_FORM DOCUMENT
- SERVICE REGULATED_BY DOCUMENT
- SERVICE HAS_DEADLINE ANNOUNCEMENT or DOCUMENT
- ORGANIZATIONAL_UNIT PROVIDES_SERVICE SERVICE
- ORGANIZATIONAL_UNIT CONDUCTS_PROJECT RESEARCH_PROJECT
- RESEARCH_PROJECT PRODUCES_PUBLICATION PUBLICATION
- ORGANIZATIONAL_UNIT COLLABORATES_WITH ORGANIZATIONAL_UNIT
- BUILDING LOCATED_IN CAMPUS
- ROOM LOCATED_IN BUILDING
- ORGANIZATIONAL_UNIT HAS_CONTACT_DETAILS CONTACT_DETAILS
- ORGANIZATIONAL_UNIT MAINTAINS_WEBSITE DOCUMENT
- ORGANIZATIONAL_UNIT PUBLISHES ANNOUNCEMENT

8. ENTITY SPECIFICITY
Do not create meaningless generic nodes such as "students", "lecturers", "staff", "everyone", or "the university" unless the text provides a specific named entity.
For broad beneficiary statements, connect the named SERVICE to the named ORGANIZATIONAL_UNIT instead of creating a generic audience node.

9. PROPERTY CONSTRAINTS
Do not use nested objects, maps, or dictionaries in properties.
All extra properties must use snake_case keys.
All values must be JSON primitives, arrays, or null.

10. EVIDENCE REQUIREMENT
Every node and every relationship must include `evidence_text`.
Use a short exact supporting span from the source whenever possible.
Keep it concise and directly relevant.

11. NO ORPHAN NOISE
Avoid extracting isolated nodes unless they are clearly important named entities with semantic value.

12. FINAL VALIDATION
Before returning the result, verify:
- output is valid JSON
- every relationship source exists in nodes
- every relationship target exists in nodes
- no duplicate node ids
- no duplicate relationships with same source, type, target
- all required properties exist
- all missing optional values are null
"""

EXTRACTION_PROMPT_TEMPLATE = """
You are an expert Knowledge Graph extraction system.

Extract entities and relationships from the provided text following the schema and rules below.

## ENTITY LABELS
{object}

## ALLOWED RELATIONSHIP TYPES
{relationship_types}

## OUTPUT SCHEMA
{json_output}

## NODE RULES
{node_rules}

## RELATIONSHIP RULES
{relationship_rules}

---BEGIN TEXT---
{text}
---END TEXT---

## INSTRUCTIONS
{instructions}

Return only valid JSON.
"""


def get_extraction_prompt(text: str, doc_id: str, model_name: str) -> str:
    formatted_node_rules = NODE_RULES.format(
        model_name=model_name,
        doc_id=doc_id,
    )

    formatted_rel_rules = RELATIONSHIP_RULES.format(
        model_name=model_name,
        doc_id=doc_id,
    )

    return EXTRACTION_PROMPT_TEMPLATE.format(
        object=OBJECTS,
        relationship_types=RELATIONSHIP_TYPES,
        json_output=JSON_OUTPUT,
        node_rules=formatted_node_rules,
        relationship_rules=formatted_rel_rules,
        instructions=INSTRUCTIONS,
        text=text,
    )