"""Token/cost estimates. Pricing is user-configured; missing prices stay unknown."""
from __future__ import annotations


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def estimate_cost(input_tokens: int, output_tokens: int, pricing: dict) -> float | None:
    input_rate, output_rate = pricing.get("input_per_million_usd"), pricing.get("output_per_million_usd")
    if input_rate is None or output_rate is None: return None
    return (input_tokens * float(input_rate) + output_tokens * float(output_rate)) / 1_000_000
