"""
shared-types/schemas.py

Pydantic schemas shared across services.
Add schemas here as features are built — one schema per section, keep sections
sorted by feature number so future readers can trace when each was introduced.
"""

from typing import Literal

# ---------------------------------------------------------------------------
# Core types (established before Feature 1 — must be used by all services)
# ---------------------------------------------------------------------------

Locale = Literal["en-IN", "hi-IN"]
"""
Supported locales for MVP. English (en-IN) is primary; Hindi (hi-IN) is the
confirmed second language. See DEV_LOG [2026-08-08] for the decision rationale.
Do not add locales here without a corresponding DEV_LOG entry.
"""

# ---------------------------------------------------------------------------
# Feature 1 — Medical Report Understanding (schemas added at Feature 1 build)
# ---------------------------------------------------------------------------

# Feature 2 — Health Timeline & Anomaly Detection
# Feature 3 — Evidence-Based Q&A (RAG)

