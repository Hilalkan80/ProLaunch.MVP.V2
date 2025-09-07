# M0 — Feasibility Snapshot (Generator Prompt)
_Last updated: 2025-08-24_

## Purpose
Create a 1‑page snapshot with **0–100 viability score**, lean plan tiles, **top competitors**, **price band**, and **next 5 steps**, using only provided evidence.

## Inputs (JSON)
```json
{
  "idea_summary": "...",
  "user_profile": {"experience":"none|some|experienced","budget_band":"<5k|5k-25k|25k-100k|100k+","timeline_months":0},
  "signals": {"demand": "...", "trend": "...", "risk": "..."}, 
  "evidence": [{"id":"ref_001","title":"...","date":"YYYY-MM-DD","snippet":"...","url":"..."}, ...],
  "max_words": 500
}
```

## Steps
1. **Score (0–100).** Weigh demand, unit economics plausibility, competitive intensity, and execution simplicity.
2. **Lean tiles (6–8).** Problem, solution, audience, channels, price band, differentiators, risks, assumptions.
3. **Competitors (3).** Name + quick angle; cite evidence IDs with dates.
4. **Next 5 steps.** Bite‑sized, high‑leverage actions for this founder profile.
5. **Citations.** Inline `[[{ref_id} — YYYY‑MM‑DD]]` after claims.

## Output (Markdown)
- H1: Idea name (from input or inferred)
- **Viability Score:** N/100 with one‑line rationale
- **Lean Plan Tiles:** bullets
- **Top Competitors:** bullets with citations
- **Likely Price Band:** \$X–\$Y (if unknown, provide a range as Assumption)
- **Next 5 Steps**

## Guardrails
- Use **only** provided `evidence`. If thin, label ranges as **Assumption**.
- Stay ≤ `max_words`. Prefer bullets over paragraphs.
