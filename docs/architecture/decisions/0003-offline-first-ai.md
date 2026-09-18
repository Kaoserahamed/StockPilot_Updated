# ADR 0003 — Deterministic analytics first, Gemini only as a polisher

- **Date:** 2026-09-16
- **Status:** Accepted

## Context

AI endpoints (FR-30..FR-37: chat, insights, forecast, reorder, anomalies) must
be testable in CI with no API key, no network, and no billing — while still
offering LLM-quality prose when an operator configures a key.

## Decision

Every AI endpoint computes a **deterministic answer from live SQL aggregates
first** (`ai_service`, `ai2_service`, `ai3_service`). `maybe_polish_with_gemini`
then optionally rewrites the wording via Gemini, guarded by
`settings.has_gemini_configured`; on any failure it returns the draft
unchanged. `GEMINI_API_KEY` empty ⇒ pure offline mode.

## Consequences

- Tests assert on real numbers (profit, best seller, reorder qty) with no mocks.
- No prompt-injection path can change figures: the LLM only rephrases text.
- Operators get graceful degradation: AI pages work on day one, prose
  improves when a key is added.
