import json

import pytest

from llm_regression.domain import Generation
from llm_regression.judge import semantic_judge


class FakeJudge:
    async def generate(self, prompt: str) -> Generation:
        return Generation(json.dumps({"score": 0.8, "reason": "meets rubric"}), 1)


@pytest.mark.asyncio
async def test_semantic_judge_parses_score():
    score, reason = await semantic_judge(FakeJudge(), "be helpful", "question", "answer")
    assert score == 0.8
    assert reason == "meets rubric"