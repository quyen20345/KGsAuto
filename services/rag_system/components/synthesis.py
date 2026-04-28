"""Answer generation using LLM"""

import re
from pprint import pformat
from typing import List, Dict, Any

from services.llms import get_llm
from services.rag_system.schemas import Answer


BASE_SYSTEM_PROMPT = """Bạn là trợ lý AI trả lời câu hỏi về Đại học Công nghệ - ĐHQGHN (University of Engineering and Technology - VNU).

Quy tắc chung:
1. Trả lời bằng tiếng Việt
2. Trả lời ngắn gọn, súc tích, đi thẳng vào vấn đề
3. Nếu không có đủ thông tin để trả lời, hãy nói rõ "Tôi không có đủ thông tin để trả lời câu hỏi này"
4. KHÔNG bịa đặt thông tin
5. Luôn trích dẫn nguồn khi có thể
"""

CITATION_INSTRUCTIONS = """
Cách trích dẫn:
- Với tài liệu: sử dụng [chunk_id] ở cuối câu
- Ví dụ: "GS.TS. Chử Đức Trình là Hiệu trưởng Trường ĐHCN [001_Đảng ủy]"
"""


def _score(value: Any) -> float:
    return float(value or 0.0)

MARKDOWN_SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + """
Chế độ: Markdown-only (chỉ sử dụng thông tin từ tài liệu văn bản)

Quy tắc bổ sung:
1. CHỈ sử dụng thông tin từ các đoạn văn bản được cung cấp bên dưới
2. KHÔNG sử dụng kiến thức bên ngoài hoặc thông tin không có trong ngữ cảnh
3. Nếu thông tin trong ngữ cảnh không đủ để trả lời, hãy nói rõ phần nào còn thiếu
4. Trích dẫn nguồn bằng cách sử dụng [chunk_id] ở cuối mỗi thông tin
""" + CITATION_INSTRUCTIONS


def build_markdown_prompt(question: str, chunks: List[Dict[str, Any]]) -> str:
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        chunk_id = chunk.get('chunk_id', 'unknown')
        title = chunk.get('title', '')
        section = chunk.get('section', '')
        text = chunk.get('text', '')
        score = _score(chunk.get('score'))

        context_parts.append(
            f"""[{i}] Tài liệu: {chunk_id}
Tiêu đề: {title}
Phần: {section}
Độ liên quan: {score:.3f}

Nội dung:
{text}
"""
        )

    context = "\n" + "=" * 60 + "\n".join(context_parts)

    return f"""Ngữ cảnh (các đoạn văn bản liên quan):
{context}

{"="*60}

Câu hỏi: {question}

Hướng dẫn trả lời:
- Dựa vào các đoạn văn bản trên để trả lời
- Trích dẫn nguồn bằng [chunk_id]
- Nếu không đủ thông tin, nói rõ thiếu gì

Trả lời:"""


class AnswerSynthesizer:
    """Synthesize answers from evidence using LLM"""

    def __init__(self, config):
        self.config = config
        self.llm = get_llm(config.llm_provider, model_name=config.llm_model)

    def synthesize(
        self,
        question: str,
        evidence: List[Dict[str, Any]],
        mode: str,
        system_prompt: str,
        user_prompt: str,
    ) -> Answer:
        try:
            response = self.llm.generate(prompt=user_prompt, system_prompt=system_prompt)

            answer_text = response.content.strip()
            token_usage = response.usage_tokens
            citations = self._extract_citations(answer_text)

            return Answer(
                text=answer_text,
                citations=citations,
                confidence=None,
                metadata={"model": response.model, "token_usage": token_usage, "mode": mode},
            )

        except Exception as e:
            return Answer(
                text=f"Xin lỗi, đã xảy ra lỗi khi xử lý câu hỏi: {str(e)}",
                citations=[],
                confidence=0.0,
                metadata={"error": str(e), "mode": mode},
            )

    def _extract_citations(self, text: str) -> List[str]:
        pattern = r'\[([^\]]+)\]'
        matches = re.findall(pattern, text)

        citations = []
        seen = set()
        for match in matches:
            if match not in seen:
                citations.append(match)
                seen.add(match)

        return citations

    def synthesize_markdown_only(self, question: str, chunks: List[Dict[str, Any]]) -> Answer:
        user_prompt = build_markdown_prompt(question, chunks)
        return self.synthesize(
            question=question,
            evidence=chunks,
            mode="semantic_search",
            system_prompt=MARKDOWN_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

    def synthesize_graph_only(self, question: str, facts: List[Dict[str, Any]]) -> Answer:
        system_prompt = BASE_SYSTEM_PROMPT + """
Chế độ: Graph-only (chỉ sử dụng thông tin từ knowledge graph)

Quy tắc bổ sung:
1. CHỈ sử dụng thông tin từ các fact được cung cấp bên dưới
2. KHÔNG sử dụng kiến thức bên ngoài
3. Trích dẫn nguồn bằng cách sử dụng [entity_name] ở cuối mỗi thông tin
4. Nếu không đủ thông tin, nói rõ phần nào còn thiếu
""" + CITATION_INSTRUCTIONS

        context_parts = []
        for i, fact in enumerate(facts, 1):
            entity_name = fact.get('entity_name', 'unknown')
            fact_type = fact.get('fact_type', 'property')
            fact_text = fact.get('fact_text', '')
            score = _score(fact.get('score'))

            context_parts.append(
                f"""[{i}] Entity: {entity_name}
Type: {fact_type}
Relevance: {score:.3f}

Fact: {fact_text}
"""
            )

        context = "\n" + "=" * 60 + "\n".join(context_parts)

        user_prompt = f"""Ngữ cảnh (các fact từ knowledge graph):
{context}

{"="*60}

Câu hỏi: {question}

Hướng dẫn trả lời:
- Dựa vào các fact trên để trả lời
- Trích dẫn nguồn bằng [entity_name]
- Nếu không đủ thông tin, nói rõ thiếu gì

Trả lời:"""

        return self.synthesize(
            question=question,
            evidence=facts,
            mode="graph_search",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    def _format_markdown_evidence(self, markdown_chunks: List[Dict[str, Any]]) -> str:
        markdown_parts = []
        for i, chunk in enumerate(markdown_chunks, 1):
            markdown_parts.append(
                f"""[M{i}] Tài liệu: {chunk.get('chunk_id', 'unknown')}
Tiêu đề: {chunk.get('title', '')}
Phần: {chunk.get('section', '')}
Độ liên quan: {_score(chunk.get('score')):.3f}

Nội dung:
{chunk.get('text', '')}
"""
            )
        return chr(10).join(markdown_parts) if markdown_parts else "Không có markdown evidence."

    def synthesize_hybrid(
        self,
        question: str,
        markdown_chunks: List[Dict[str, Any]],
        graph_facts: List[Dict[str, Any]],
    ) -> Answer:
        system_prompt = BASE_SYSTEM_PROMPT + """
Chế độ: Hybrid (kết hợp semantic search trên markdown và graph search trên knowledge graph)

Quy tắc bổ sung:
1. CHỈ sử dụng thông tin từ hai nhóm evidence được cung cấp bên dưới
2. Phân biệt rõ nguồn từ tài liệu markdown và nguồn từ knowledge graph khi lập luận
3. Nếu hai nguồn mâu thuẫn, nêu rõ mâu thuẫn và ưu tiên trả lời có điều kiện thay vì suy đoán
4. Trích dẫn markdown bằng [chunk_id] và graph bằng [entity_name] khi có thể
5. Nếu cả hai nguồn không đủ thông tin, nói rõ thiếu thông tin gì
""" + CITATION_INSTRUCTIONS

        graph_parts = []
        for i, fact in enumerate(graph_facts, 1):
            graph_parts.append(
                f"""[G{i}] Entity: {fact.get('entity_name', 'unknown')}
Type: {fact.get('fact_type', 'fact')}
Relevance: {_score(fact.get('score')):.3f}

Fact:
{fact.get('fact_text', '')}
"""
            )

        user_prompt = f"""Semantic evidence từ markdown:
{"=" * 60}
{self._format_markdown_evidence(markdown_chunks)}

Graph evidence từ knowledge graph:
{"=" * 60}
{chr(10).join(graph_parts) if graph_parts else "Không có graph evidence."}

{"=" * 60}

Câu hỏi: {question}

Hướng dẫn trả lời:
- Tổng hợp cả hai nhóm evidence nếu chúng bổ sung cho nhau
- Nêu rõ khi câu trả lời chỉ được hỗ trợ bởi một nguồn
- Không dùng kiến thức ngoài context

Trả lời:"""

        return self.synthesize(
            question=question,
            evidence=[*markdown_chunks, *graph_facts],
            mode="hybrid",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    def synthesize_hybrid_graphsearch(
        self,
        question: str,
        markdown_chunks: List[Dict[str, Any]],
        graph_context: Dict[str, Any] | None,
        graph_answer: str,
        graph_reasoning: Dict[str, Any] | None = None,
    ) -> Answer:
        system_prompt = BASE_SYSTEM_PROMPT + """
Chế độ: Hybrid (kết hợp semantic search trên markdown và deep graph_search trên knowledge graph)

Quy tắc bổ sung:
1. CHỈ sử dụng thông tin từ markdown evidence và graph_search evidence được cung cấp bên dưới
2. Phân biệt rõ nguồn từ tài liệu markdown và nguồn từ knowledge graph khi lập luận
3. Nếu hai nguồn mâu thuẫn, nêu rõ mâu thuẫn và ưu tiên trả lời có điều kiện thay vì suy đoán
4. Trích dẫn markdown bằng [chunk_id] khi có thể
5. Không bịa citation cho graph_search nếu graph evidence không có citation trực tiếp
6. Nếu cả hai nguồn không đủ thông tin, nói rõ thiếu thông tin gì
""" + CITATION_INSTRUCTIONS

        user_prompt = f"""Semantic evidence từ markdown:
{"=" * 60}
{self._format_markdown_evidence(markdown_chunks)}

Deep graph_search answer:
{"=" * 60}
{graph_answer or "Không có câu trả lời từ graph_search."}

Deep graph_search evidence/context:
{"=" * 60}
{pformat(graph_context, compact=False) if graph_context else "Không có graph_search context."}

Deep graph_search reasoning summary:
{"=" * 60}
{pformat(graph_reasoning, compact=True) if graph_reasoning else "Không có reasoning steps."}

{"=" * 60}

Câu hỏi: {question}

Hướng dẫn trả lời:
- Tổng hợp markdown evidence và graph_search evidence nếu chúng bổ sung cho nhau
- Nếu chỉ một nguồn hỗ trợ được câu trả lời, hãy nói rõ nguồn nào hỗ trợ
- Nếu graph_search không tìm được nhưng markdown có bằng chứng rõ ràng, có thể trả lời dựa trên markdown và nói rõ graph chưa đối chiếu được
- Nếu markdown và graph_search mâu thuẫn, nêu mâu thuẫn thay vì chọn bừa
- Không dùng kiến thức ngoài context

Trả lời:"""

        return self.synthesize(
            question=question,
            evidence=[*markdown_chunks, graph_context or {}, graph_reasoning or {}],
            mode="hybrid",
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
