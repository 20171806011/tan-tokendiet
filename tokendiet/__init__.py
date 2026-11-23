"""TAN TokenDiet — Audit, benchmark, and compact MCP schemas & AI agent context files."""

__version__ = "1.0.0"

from .analyzer import AuditReport, Finding, audit_payload, audit_path, audit_text
from .minifier import MinifyResult, minify_tools_payload
from .pricing import MODELS, estimate_monthly_cost
from .tokenizer import count_tokens

__all__ = [
    "__version__",
    "AuditReport",
    "Finding",
    "MODELS",
    "MinifyResult",
    "audit_path",
    "audit_payload",
    "audit_text",
    "count_tokens",
    "estimate_monthly_cost",
    "minify_tools_payload",
]
