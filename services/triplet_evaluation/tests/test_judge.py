import json

import pytest

from services.triplet_evaluation.judge import evaluate_triplet, parse_judgement


class FakeResponse:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def generate(self, prompt, system_prompt=None):
        self.calls += 1
        return FakeResponse(self.responses.pop(0))


def test_parse_judgement_accepts_canonical_label():
    judgement = parse_judgement(
        json.dumps(
            {
                "label": "supported",
                "confidence": 0.8,
                "reason": "The evidence supports it.",
                "evidence_sources": ["subject.properties.description"],
            }
        )
    )

    assert judgement.label == "supported"
    assert judgement.confidence == 0.8
    assert judgement.evidence_sources == ["subject.properties.description"]


def test_parse_judgement_normalizes_legacy_label():
    judgement = parse_judgement(
        '{"label":"false_verifiable","confidence":0.7,"reason":"Contradicted."}'
    )

    assert judgement.label == "contradicted"


def test_parse_judgement_accepts_fenced_json():
    judgement = parse_judgement(
        '```json\n{"label":"not_enough_info","confidence":0.4,"reason":"Insufficient evidence."}\n```'
    )

    assert judgement.label == "not_enough_info"


def test_evaluate_triplet_returns_invalid_after_retries():
    llm = FakeLLM(["not json", '{"label":"unknown","confidence":0.5,"reason":"bad"}'])

    judgement = evaluate_triplet({}, llm=llm, max_retries=2)

    assert judgement.valid is False
    assert judgement.label == "invalid_response"
    assert llm.calls == 2


def test_parse_judgement_rejects_label_reason_mismatch():
    raw = json.dumps(
        {
            "label": "contradicted",
            "confidence": 0.9,
            "reason": "Initial analysis was wrong. On closer inspection, the evidence matches. Therefore, the triplet is supported.",
            "evidence_sources": [],
        }
    )

    with pytest.raises(ValueError, match="reason appears to imply"):
        parse_judgement(raw)
