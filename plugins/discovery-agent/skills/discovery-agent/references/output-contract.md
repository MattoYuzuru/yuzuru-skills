# Discovery Output Contract

## Select depth

| Scope | Default output |
|---|---|
| Family, hobby, or small internal idea | One opportunity brief with assumptions and recommendation |
| Open-source or nonprofit initiative | Brief plus alternatives, maintenance/adoption risks, and contribution fit |
| Commercial or regional product | Brief, landscape, regional fit, risks, and open questions |
| Major feature expansion | Feature opportunities, impact on existing behavior, regressions, and evidence |

## Evidence ledger

For each material source record:

- stable source ID;
- URL or local path;
- source type and publisher;
- publication/update and access dates when available;
- geography;
- claim supported;
- confidence (`high`, `medium`, `low`);
- whether the statement is fact, reported experience, or inference.

Use `scripts/evidence_index.py` to detect duplicate IDs/URLs and summarize coverage. The script does
not judge source credibility; the agent owns that decision.

## Recommendation labels

- `pursue`: evidence supports the objective and risks are proportionate;
- `pursue-as-noncommercial`: valid personal/internal/open-source value but weak business case;
- `test-first`: a small experiment can resolve a decisive unknown;
- `use-existing`: an available product fits better than new construction;
- `reframe`: the underlying job is useful but the proposed solution is weak;
- `stop`: cost, redundancy, access, or risk is disproportionate to the objective.

Name the conditions that would change the recommendation.
