"""Reference LLM input pricing & 5m/1h prompt-cache write cost modeling (USD & GBP)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

USD_TO_GBP = 0.79  # Reference display rate


@dataclass(frozen=True)
class ModelPricing:
    id: str
    name: str
    provider: str
    input_per_1m_usd: float
    cached_input_per_1m_usd: float
    cache_write_5m_mult: float = 1.25
    cache_write_1h_mult: float = 2.00


MODELS: Dict[str, ModelPricing] = {
    "claude-sonnet": ModelPricing(
        id="claude-sonnet",
        name="Claude Sonnet 4.x",
        provider="Anthropic",
        input_per_1m_usd=3.00,
        cached_input_per_1m_usd=0.30,
        cache_write_5m_mult=1.25,
        cache_write_1h_mult=2.00,
    ),
    "claude-opus": ModelPricing(
        id="claude-opus",
        name="Claude Opus 4.x",
        provider="Anthropic",
        input_per_1m_usd=15.00,
        cached_input_per_1m_usd=1.50,
        cache_write_5m_mult=1.25,
        cache_write_1h_mult=2.00,
    ),
    "gpt-5": ModelPricing(
        id="gpt-5",
        name="GPT-5 / Flagship",
        provider="OpenAI",
        input_per_1m_usd=2.50,
        cached_input_per_1m_usd=0.25,
        cache_write_5m_mult=1.00,
        cache_write_1h_mult=1.00,
    ),
    "gpt-4.1-mini": ModelPricing(
        id="gpt-4.1-mini",
        name="GPT-4.1 / Mini Tier",
        provider="OpenAI",
        input_per_1m_usd=0.40,
        cached_input_per_1m_usd=0.10,
        cache_write_5m_mult=1.00,
        cache_write_1h_mult=1.00,
    ),
    "gemini-2.5-pro": ModelPricing(
        id="gemini-2.5-pro",
        name="Gemini 2.5 Pro",
        provider="Google",
        input_per_1m_usd=1.25,
        cached_input_per_1m_usd=0.31,
        cache_write_5m_mult=1.00,
        cache_write_1h_mult=1.00,
    ),
    "gemini-2.5-flash": ModelPricing(
        id="gemini-2.5-flash",
        name="Gemini 2.5 Flash",
        provider="Google",
        input_per_1m_usd=0.30,
        cached_input_per_1m_usd=0.075,
        cache_write_5m_mult=1.00,
        cache_write_1h_mult=1.00,
    ),
}


def estimate_monthly_cost(
    tokens_per_turn: int,
    turns_per_day: int = 120,
    team_size: int = 1,
    model_id: str = "claude-sonnet",
    cache_hit_rate: float = 0.0,
    days_per_month: int = 30,
    cache_write_ttl: str = "none",
) -> Dict[str, float]:
    """Compute monthly static-context token cost in USD and GBP.

    Args:
        cache_write_ttl: "none" (standard uncached miss), "5m" (1.25x Anthropic 5m cache write
            on cache misses), or "1h" (2.0x Anthropic 1h cache write on cache misses, e.g. Claude Code).
    """
    model = MODELS.get(model_id, MODELS["claude-sonnet"])
    hit = min(1.0, max(0.0, cache_hit_rate))
    monthly_tokens = max(0, tokens_per_turn) * max(0, turns_per_day) * max(1, team_size) * days_per_month

    miss_mult = 1.0
    if cache_write_ttl == "5m":
        miss_mult = model.cache_write_5m_mult
    elif cache_write_ttl == "1h":
        miss_mult = model.cache_write_1h_mult

    miss_rate_per_1m = model.input_per_1m_usd * miss_mult
    effective_rate_per_1m = (1.0 - hit) * miss_rate_per_1m + hit * model.cached_input_per_1m_usd

    uncached_usd = (monthly_tokens / 1_000_000.0) * model.input_per_1m_usd
    effective_usd = (monthly_tokens / 1_000_000.0) * effective_rate_per_1m
    return {
        "monthly_tokens": float(monthly_tokens),
        "uncached_monthly_usd": round(uncached_usd, 2),
        "effective_monthly_usd": round(effective_usd, 2),
        "effective_monthly_gbp": round(effective_usd * USD_TO_GBP, 2),
        "cache_savings_usd": round(uncached_usd - effective_usd, 2),
        "cache_write_multiplier": miss_mult,
    }
