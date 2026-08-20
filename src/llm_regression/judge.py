import json

from .providers import LLMProvider


async def semantic_judge(provider: LLMProvider, rubric: str, input_text: str, output: str) -> tuple[float, str | None]:
    prompt = (
        "Score the response against this rubric. Return only JSON with score (0 to 1) and reason.\n"
        f"Rubric: {rubric}\nInput: {input_text}\nResponse: {output}"
    )
    generation = await provider.generate(prompt)
    try:
        result = json.loads(generation.text)
        score = float(result["score"])
        if not 0 <= score <= 1:
            raise ValueError("score outside 0..1")
        return score, result.get("reason")
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return 0.0, f"judge output invalid: {exc}"
