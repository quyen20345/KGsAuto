import json
import logging
import re
from urllib.parse import urlparse

from services.rag_system.graph.graph_search.parsing import KEYWORD_FIELDS, parse_keyword_extraction
from services.rag_system.graph.graph_search.prompts import PROMPTS
from services.rag_system.graph.graph_search.utils import openai_complete

logger = logging.getLogger(__name__)


class GraphKeywordExtractionError(RuntimeError):
    pass


def _log_component_error(component: str, error: Exception) -> None:
    logger.warning("GraphSearch %s failed: %s", component, error)


def _has_keywords(keyword_groups: dict[str, list[str]]) -> bool:
    return any(keyword_groups.get(field) for field in KEYWORD_FIELDS)


def empty_keyword_extraction() -> dict[str, list[str]]:
    return {field: [] for field in KEYWORD_FIELDS}


STOPWORDS = {
    "ai",
    "bao",
    "bi",
    "bị",
    "boi",
    "bởi",
    "cai",
    "cái",
    "cac",
    "các",
    "cho",
    "cua",
    "của",
    "de",
    "duoc",
    "được",
    "em",
    "hoi",
    "hỏi",
    "khi",
    "la",
    "là",
    "nao",
    "nào",
    "o",
    "ở",
    "tai",
    "tại",
    "thi",
    "thì",
    "toi",
    "tôi",
    "trong",
    "va",
    "và",
    "ve",
    "về",
}
TOKEN_RE = re.compile(r"https?://\S+|[A-ZÀ-ỴĐ][\wÀ-ỹĐđ]*(?:\s+[A-ZÀ-ỴĐ0-9][\wÀ-ỹĐđ]*)+|[\wÀ-ỹĐđ]+", re.UNICODE)


def _fallback_keywords_from_query(query: str) -> dict[str, list[str]]:
    groups = empty_keyword_extraction()
    seen: set[str] = set()

    def add(field: str, value: str) -> None:
        words = value.strip(' .,;:!?()[]{}"\'`').split()
        while words and words[0].casefold() in STOPWORDS:
            words.pop(0)
        while words and words[-1].casefold() in STOPWORDS:
            words.pop()
        value = " ".join(words)
        if not value or len(value) < 2:
            return
        key = value.casefold()
        if key in seen:
            return
        seen.add(key)
        groups[field].append(value)

    for raw_match in TOKEN_RE.findall(query):
        match = raw_match.strip()
        if match.startswith("http"):
            parsed_url = urlparse(match)
            add("must_keep_phrases", match.rstrip('/.,;'))
            if parsed_url.netloc:
                add("expanded_keywords", parsed_url.netloc)
            continue
        if " " in match:
            add("must_keep_phrases", match)
            continue
        if match.casefold() not in STOPWORDS and (len(match) > 2 or any(char.isdigit() for char in match)):
            add("low_level_keywords", match)

    if not groups["must_keep_phrases"] and not groups["low_level_keywords"]:
        add("low_level_keywords", query)
    return groups


async def keywords_extraction(query):
    try:
        keyword_prompt = PROMPTS["keywords_extraction"].format(query=query)
        keywords_response = await openai_complete(prompt=keyword_prompt)
        parsed = parse_keyword_extraction(keywords_response)
        if _has_keywords(parsed):
            return parsed

        repair_prompt = PROMPTS["keywords_extraction_repair"].format(
            query=query,
            invalid_output=keywords_response,
        )
        repaired_response = await openai_complete(prompt=repair_prompt)
        repaired = parse_keyword_extraction(repaired_response)
        if _has_keywords(repaired):
            return repaired

        fallback = _fallback_keywords_from_query(query)
        if _has_keywords(fallback):
            logger.warning("GraphSearch keywords_extraction used query-derived fallback after empty LLM output")
            return fallback
        raise GraphKeywordExtractionError("keyword LLM returned no parseable keywords after repair")
    except Exception as error:
        _log_component_error("keywords_extraction", error)
        if isinstance(error, GraphKeywordExtractionError):
            raise
        raise GraphKeywordExtractionError(str(error)) from error

async def question_decomposition_deep(query):
    try:
        decomp_prompt = PROMPTS["query_decomposition_deep"].format(query=query)
        sub_queries = await openai_complete(prompt=decomp_prompt)
        return sub_queries.strip()
    except Exception as error:
        _log_component_error("question_decomposition_deep", error)
        return ""

async def question_decomposition_deep_kg(query):
    try:
        decomp_prompt = PROMPTS["query_decomposition_deep_kg"].format(query=query)
        sub_queries = await openai_complete(prompt=decomp_prompt)
        return sub_queries.strip()
    except Exception as error:
        _log_component_error("question_decomposition_deep_kg", error)
        return ""

async def query_completer(sub_query, context_data):
    try:
        completer_prompt = PROMPTS["query_completer"].format(
            sub_query=sub_query,
            context_data=context_data
        )
        completed_query = await openai_complete(prompt=completer_prompt)
        return completed_query.strip()
    except Exception as error:
        _log_component_error("query_completer", error)
        return ""

async def kg_query_completer(sub_query, context_data):
    try:
        completer_prompt = PROMPTS["kg_query_completer"].format(
            sub_query=sub_query,
            context_data=context_data
        )
        completed_query = await openai_complete(prompt=completer_prompt)
        return completed_query.strip()
    except Exception as error:
        _log_component_error("kg_query_completer", error)
        return ""
async def text_summary(query, context_data):
    try:
        summary_prompt = PROMPTS["retrieval_text_summarization"].format(
            query=query,
            context_data=context_data
        )
        text_summary = await openai_complete(prompt=summary_prompt)
        return text_summary.strip()
    except Exception as error:
        _log_component_error("text_summary", error)
        return ""

async def kg_summary(query, context_data):
    try:
        kg_summary_prompt = PROMPTS["knowledge_graph_summarization"].format(
            query=query,
            context_data=context_data
        )
        kg_summary = await openai_complete(prompt=kg_summary_prompt)
        return kg_summary.strip()
    except Exception as error:
        _log_component_error("kg_summary", error)
        return ""

async def answer_generation(query, context_data):
    try:
        answer_prompt = PROMPTS["answer_generation"].format(
            query=query,
            context_data=context_data
        )
        final_answer = await openai_complete(prompt=answer_prompt)
        return final_answer.strip()
    except Exception as error:
        _log_component_error("answer_generation", error)
        return ""

async def answer_generation_deep(query, context_data):
    try:
        answer_prompt = PROMPTS["answer_generation_deep"].format(
            query=query,
            context_data=context_data
        )
        final_answer = await openai_complete(prompt=answer_prompt)
        parsed = _parse_answer_generation_json(final_answer)
        return str(parsed.get("answer") or "").strip(), str(parsed.get("reasoning") or "").strip()
    except Exception as error:
        _log_component_error("answer_generation_deep", error)
        return "", ""


def _parse_answer_generation_json(raw: str) -> dict[str, str]:
    text = (raw or "").strip()
    candidates = [text]
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        candidates.append(fence.group(1).strip())
    balanced = _extract_balanced_json_object(text)
    if balanced:
        candidates.append(balanced)

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return {
                "answer": str(parsed.get("answer") or ""),
                "reasoning": str(parsed.get("reasoning") or ""),
            }
    return {"answer": text, "reasoning": ""}


def _extract_balanced_json_object(text: str) -> str | None:
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(text[start:], start=start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return None

async def evidence_verification(query, context_data, model_response):
    try:
        verify_prompt = PROMPTS["evidence_verification"].format(
            query=query,
            context_data=context_data,
            model_response=model_response
        )
        final_verification = await openai_complete(prompt=verify_prompt)
        return final_verification.strip()
    except Exception as error:
        _log_component_error("evidence_verification", error)
        return ""

async def query_expansion(query, context_data, model_response, evidence_verification):
    try:
        query_expansion_prompt = PROMPTS["query_expansion"].format(
            query=query,
            context_data=context_data,
            model_response=model_response,
            evidence_verification=evidence_verification
        )
        expanded_queries = await openai_complete(prompt=query_expansion_prompt)
        return expanded_queries.strip()
    except Exception as error:
        _log_component_error("query_expansion", error)
        return ""
