# ── 1. ONTOLOGY ───────────────────────────────────────────────────────────────
# ref: https://papers.iafor.org/wp-content/uploads/papers/bce2023/BCE2023_74278.pdf

ONTOLOGY_STR = """
### ENTITY LABELS
UNIVERSITY | INSTITUTION | ORGANIZATION | STUDY_PROGRAM | CONTACT_DETAILS
STUDENT    | SERVICE     | APPLICATION  | RESEARCH      | CONTINUING_EDUCATION
LOCATION

### ALLOWED RELATIONSHIPS — Subject → HAS_... → Object
UNIVERSITY          → HAS_NEWS, HAS_PUBLICATIONS, HAS_OFFICES, HAS_FACULTIES,
                      HAS_RESEARCH, HAS_ORGANIZATION, HAS_LABS, HAS_PARTNERSHIPS,
                      HAS_EVENTS, HAS_ADDRESS, HAS_PARKING_FACILITIES, HAS_ALUMNI,
                      HAS_INSTITUTIONS, HAS_STUDY_PROGRAM, HAS_LOCATION,
                      HAS_CONTINUING_EDUCATION, HAS_JOBS, HAS_SCHOLARSHIPS
INSTITUTION         → HAS_OPENING_HOURS, HAS_CONSULTATION_HOURS, HAS_ADDRESS,
                      HAS_CONTACT_PERSON, HAS_OFFERS, HAS_EVENTS, HAS_TASKS,
                      HAS_FORMS, HAS_SERVICE
ORGANIZATION        → HAS_EMPLOYEES, HAS_TASKS, HAS_CONTACT_DETAILS
STUDY_PROGRAM       → HAS_DEGREE, HAS_ABBREVIATION_STUDY, HAS_LOCATION,
                      HAS_SEMESTER, HAS_COURSE_ADVICE, HAS_STUDY_PROGRAM_ADVICE,
                      HAS_LANGUAGE, HAS_STUDIENART_STUDY, HAS_STUDY_TYPE,
                      HAS_DURATION, HAS_ADMISSION_LIMIT, HAS_APPLICATION
CONTACT_DETAILS     → HAS_ADDRESS, HAS_EMAIL, HAS_PHONE, HAS_TIME,
                      HAS_URL, HAS_FUNCTION, HAS_GENDER
STUDENT             → HAS_STUDY_PROGRAM, HAS_STUDY_TYPE, HAS_TIME_TABLE,
                      HAS_FINANCING, HAS_SERVICE, HAS_HEALTH_INSURANCE,
                      HAS_LANGUAGE, HAS_MOODLE, HAS_PRIMUS, HAS_FEEDBACK,
                      HAS_STUDY_TIPS, HAS_CHANGES, HAS_EXAMS,
                      HAS_START_OF_SEMESTER, HAS_INTERNSHIP, HAS_APPLICATION
SERVICE             → HAS_STUDENT_SERVICES, HAS_PROSPECTIVE_STUDENT_SERVICES,
                      HAS_HIGH_SCHOOL_GRADUATES_SERVICES, HAS_ACCREDITATION,
                      HAS_CONSULTATION
APPLICATION         → HAS_DEADLINES, HAS_APPROVAL, HAS_DOCUMENTS,
                      HAS_RESTRICTIONS, HAS_PROCEDURE, HAS_ENROLLMENT,
                      HAS_STUDY_PROGRAM
RESEARCH            → HAS_RESEARCH_PROFILE, HAS_RESEARCH_PROFESSORSHIPS,
                      HAS_PROJECTS, HAS_PUBLICATIONS, HAS_COOPERATIVE_DOCTORATE,
                      HAS_FUNDING_ADVICE
CONTINUING_EDUCATION→ HAS_FORMAT, HAS_DEGREE, HAS_LOCATION, HAS_DURATION,
                      HAS_CONTACT_PERSON, HAS_LANGUAGE, HAS_ADMISSION_LIMIT
LOCATION            → HAS_APARTMENTS, HAS_ACTIVITIES, HAS_WEATHER,
                      HAS_EVENTS, HAS_INFRASTRUCTURE, HAS_INHABITANTS,
                      HAS_STUDY_PROGRAM
"""

# ── 2. EXTRACTION RULES ───────────────────────────────────────────────────────
# prompt: EXTRACT → ENTITY → RELATIONSHIP → PROPERTY

EXTRACT_RULES = """
1. ZERO HALLUCINATION: Only extract information explicitly present in the text. Do not infer or invent details.
2. CO-REFERENCE RESOLUTION: Absolutely do not use pronouns (it, he, this university, etc.). They must be replaced with the full, resolved entity name.
3. ATOMIC EVENTS: Each relationship must contain a single connection between 2 nodes (Subject → Predicate → Object).
4. TEMPORAL SCOPE: If an event is tied to a specific time (deadline, academic year), it must be extracted and attached to the corresponding entity or relationship property.
"""

ENTITY_RULES = """
1. STRICT LABELS: Use ONLY the 11 labels defined in the Ontology.
2. ID FORMAT: Lowercase, no accents/diacritics, underscore-separated, with label prefix. Use acronyms to ensure deterministic auto-linking. E.g.: `university_vnu_uet`, `study_program_ktpm_uet`.
3. CANONICALIZATION: Actively map aliases, abbreviations, and different surface forms to the EXACT SAME ID. Keep the "name" property as the full formal name and add variations to the "aliases" array.
4. OUT-OF-KB: If an entity CANNOT be mapped to one of the 11 allowed labels -> IGNORE IT entirely. Do not force incorrect mappings (e.g., do not force a "city" into an INSTITUTION label).
"""

# ref: https://en.wikipedia.org/wiki/Property_graph
RELATIONSHIP_RULES = """
1. STRICT RELATIONSHIPS: Only use the "HAS_..." relationships defined in the ontology. Absolutely do not create new relationship types.
2. DOMAIN/RANGE: The Subject (start node) and Object (end node) must be valid for the specific relationship according to the Ontology.
"""

PROPERTY_RULES = """
1. DYNAMIC PROPERTIES (FALLBACK): Only when a standard property key is missing, you may create a new key in English using snake_case.
2. FLATTENING: Values must be String, Number, Boolean, or Array. Nested Objects are strictly prohibited.
3. DATA TYPE STANDARDIZATION: Dates -> ISO 8601 format (e.g., 2024-08-15). Numbers -> pure numeric format (e.g., 4, 1500.5). Do not leave them as raw natural language text ("October this year").
"""

# ── 3. FEW-SHOT EXAMPLE ───────────────────────────────────────────────────────
# ref: https://github.com/neo4j-labs/llm-graph-builder/blob/main/data/llm_comparision.json

FEW_SHOT_EXAMPLE = """
INPUT:
  "VNU University of Engineering and Technology (UET) offers a Software 
   Engineering (SE) undergraduate program, located in Hanoi, with a duration of 4 years.
   Application deadline: 2024-08-15."

OUTPUT:
{
  "nodes": [
    {
      "id": "university_vnu_uet",
      "labels": ["UNIVERSITY"],
      "properties": {
        "name": "VNU University of Engineering and Technology",
        "aliases": ["UET", "VNU-UET"],
        "description": "A member university of VNU specializing in technology",
        "source": "doc_001"
      }
    },
    ...
  ],
  "relationships": [
    {
      "id": "university_vnu_uet_HAS_STUDY_PROGRAM_study_program_se_uet",
      "type": "HAS_STUDY_PROGRAM",
      "start_id": "university_vnu_uet",
      "end_id": "study_program_se_uet",
      "properties": {
        "source": "doc_001"
      }
    },
    ...
  ]
}
"""


# ── 4. OUTPUT SCHEMA ──────────────────────────────────────────────────────────
# ref: https://www.dataversity.net/articles/property-graphs-vs-knowledge-graphs/

OUTPUT_SCHEMA = """
{
  "LLM": "<model_name>",
  "File": "<file_path>",
  "Processing Time": "<time>",
  "Node count": <int>,
  "Relation count": <int>,
  "nodes": [
    {
      "id":         "<label_slug>",
      "labels":     ["LABEL"],
      "properties": {
        "name":        "<string>",
        "aliases":     [<string>],
        "description": "<optional_short_text>",
        "source":      "<doc_id>",
        "<key_others>":  "<string | number | boolean | array>"
      }
  ],
  "relationships": [
    {
      "id":        "<start_id>_<type>_<end_id>",
      "type":      "HAS_RELATIONSHIP_TYPE",
      "start_id":  "<node_id>",
      "end_id":    "<node_id>",
      "properties": {
        "source": "<doc_id>",
        "description" : "<optional_short_text>",
        "<key_others>":  "<string | number | boolean | array>"
      }
    }
  ]
}
"""

# ── 5. PROMPT TEMPLATE ────────────────────────────────────────────────────────
# Chain-of-Thought via <think> tag — model reasons before outputting JSON

EXTRACTION_PROMPT_TEMPLATE = """\
You are an expert in building Knowledge Graphs based on the Property Graph standard.
Your task: Read the TEXT, extract nodes and relationships according to the ontology, and return a valid JSON object.

## 1. ONTOLOGY
{schema_str}

## 2. EXTRACTION RULES — DECREASING PRIORITY (P1 > P2 > P3 > P4)
When there is a conflict between rules, P1 always overrides the others.

### P1 — GENERAL EXTRACTION RULES
{extract_rules}

### P2 — ENTITY RULES
{entity_rules}

### P3 — RELATIONSHIP RULES
{relationship_rules}

### P4 — PROPERTY RULES
{property_rules}

## 3. FEW-SHOT EXAMPLE
{few_shot_example}

## 4. OUTPUT FORMAT (VALID JSON)
{output_schema}

## 5. TEXT TO PROCESS
doc_id: {doc_id}

---BEGIN---
{text}
---END---en

## 6. REASONING INSTRUCTIONS
Before outputting the JSON, you must reason step-by-step inside a <think> tag:
  1. List all recognized entities and their candidate labels.
  2. Resolve co-references: which names/pronouns point to the exact same entity?
  3. Verify relationships: check if the domain/range of each relationship matches the provided ontology.
  4. Filter: discard anything not explicitly present in the text or lacking a valid label.

After the </think> tag, output ONLY the raw JSON object — no markdown formatting (like ```json), and no extra explanations.
"""
# ── 6. PROMPT GENERATOR ───────────────────────────────────────────────────────
def get_extraction_prompt(text: str, doc_id: str = "doc_001") -> str:
    """
    Generate extraction prompt with ontology, rules, few-shot example, and output schema.

    Args:
        text: Input text to extract entities and relationships from
        doc_id: Document identifier for source tracking

    Returns:
        Formatted prompt string ready for LLM
    """
    return EXTRACTION_PROMPT_TEMPLATE.format(
        schema_str=ONTOLOGY_STR,
        extract_rules=EXTRACT_RULES,
        entity_rules=ENTITY_RULES,
        relationship_rules=RELATIONSHIP_RULES,
        property_rules=PROPERTY_RULES,
        few_shot_example=FEW_SHOT_EXAMPLE,
        output_schema=OUTPUT_SCHEMA,
        text=text,
        doc_id=doc_id
    )
