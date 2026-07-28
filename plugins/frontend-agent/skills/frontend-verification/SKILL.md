---
name: frontend-verification
description: Review responsive behavior, accessibility, performance, motion fallbacks, and visual regressions for an interface. Use when frontend implementation needs production-focused verification.
---

# Frontend Verification

Read `references/verification-matrix.md` before a production handoff or substantial UI review.

## Workflow

1. Reconstruct critical flows, roles, supported platforms, states, and accessibility requirements.
2. Test responsive layouts at decision-relevant widths, content lengths, zoom, and orientation.
3. Verify semantics, keyboard order, focus, screen-reader names/states, contrast, errors, touch
   targets, scaling, and reduced motion.
4. Exercise loading, empty, partial, error, permission, offline, retry, and recovery states.
5. Measure relevant rendering, interaction, bundle, image, animation, and advanced-graphics budgets.
6. Compare screenshots or visual baselines where the environment supports them.
7. Classify confirmed defects, probable defects, risks, and unverified devices separately.
8. Route deep independent E2E/performance/accessibility confirmation to SRE when needed.

## Guardrails

- A successful build is not a visual or accessibility test.
- Lint is not screen-reader, keyboard, zoom, or motion verification.
- Do not claim mobile/device coverage from a single desktop viewport.
- Keep evidence and exact reproduction with every confirmed visual finding.
