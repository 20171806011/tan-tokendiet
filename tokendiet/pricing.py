"""Reference LLM input pricing & monthly cost modeling (USD & GBP)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

USD_TO_GBP = 0.79  # Reference display rate; overrideable via CLI/UI


@dataclass(frozen=True)
class ModelPricing:
    id: str
    name: str
    provider: str
    input_per_1m_usd: float
    cached_input_per_1m_usd: float


MODELS: Dict[str, ModelPricing] = {
    "claude-sonnet": ModelPricing(
        id="claude-sonnet",
        name="Claude Sonnet 4.x",
        provider="Anthropic",
        input_per_1m_usd=3.00,
        cached_input_per_1m_usd=0.30,
    ),
    "claude-opus": ModelPricing(
        id="claude-opus",
        name="Claude Opus 4.x",
        provider="Anthropic",
        input_per_1m_usd=15.00,
        cached_input_per_1m_usd=1.50,
    ),
    "gpt-5": ModelPricing(
        id="gpt-5",
        name="GPT-5 / Flagship",
        provider="OpenAI",
        input_per_1m_usd=2.50,
        cached_input_per_1m_usd=0.25,
    ),
    "gpt-4.1-mini": ModelPricing(
        id="gpt-4.1-mini",
        name="GPT-4.1 / Mini Tier",
        provider="OpenAI",
        input_per_1m_usd=0.40,
        cached_input_per_1m_usd=0.10,
    ),
    "gemini-2.5-pro": ModelPricing(
        id="gemini-2.5-pro",
        name="Gemini 2.5 Pro",
        provider="Google",
        input_per_1m_usd=1.25,
        cached_input_per_1m_usd=0.31,
    ),
    "gemini-2.5-flash": ModelPricing(
        id="gemini-2.5-flash",
        name="Gemini 2.5 Flash",
        provider="Google",
        input_per_1m_usd=0.30,
        cached_input_per_1m_usd=0.075,
    ),
}


def estimate_monthly_cost(
    tokens_per_turn: int,
    turns_per_day: int = 120,
    team_size: int = 1,
    model_id: str = "claude-sonnet",
    cache_hit_rate: float = 0.0,
    days_per_month: int = 30,
) -> Dict[str, float]:
    """Compute monthly static-context token cost in USD and GBP."""
    model = MODELS.get(model_id, MODELS["claude-sonnet"])
    hit = min(1.0, max(0.0, cache_hit_rate))
    monthly_tokens = max(0, tokens_per_turn) * max(0, turns_per_day) * max(1, team_size) * days_per_month
    effective_rate_per_1m = (
        (1.0 - hit) * model.input_per_1m_usd + hit * model.cached_input_per_1m_usd
    )
    uncached_usd = (monthly_tokens / 1_000_000.0) * model.input_per_1m_usd
    effective_usd = (monthly_tokens / 1_000_000.0) * effective_rate_per_1m
    return {
        "monthly_tokens": float(monthly_tokens),
        "uncached_monthly_usd": round(uncached_usd, 2),
        "effective_monthly_usd": round(effective_usd, 2),
        "effective_monthly_gbp": round(effective_usd * USD_TO_GBP, 2),
        "cache_savings_usd": round(uncached_usd - effective_usd, 2),
    }
