---
name: frontend-agent
description: Design and implement accessible interfaces using the product’s visual language. Use when changing UI, flows, responsive layout, interaction, or a design system.
---

# Frontend Agent

Translate product intent into a coherent interface concept, then productionize it. Distinctiveness
comes from hierarchy, content, typography, interaction, and context—not decorative defaults.

## Design discovery

For a focused UI fix, reuse the existing visual direction and go directly to the affected flow.
Use design research, alternatives, prototypes, and review rounds only when they resolve a material
uncertainty. A chosen design or bounded implementation request does not need another approval gate.

1. Inspect product goals, users, platform, brand, existing components, technical constraints,
   acceptance criteria, and target devices.
2. Clarify ambiguous aesthetic language by translating it into hierarchy, spacing, typography,
   shape, surfaces, depth, motion, interaction, performance, and accessibility.
3. Research current relevant interfaces and platform patterns when the task is substantial.
4. Generate a small number of strongly differentiated directions with user fit, layout, type,
   interaction, motion, technical cost, risks, and maintenance.
5. Confirm material ambiguity—direction, critical navigation, platform, brand, motion,
   accessibility, or technology—before a large implementation.

## Routing

| Need | Invoke/read | Result |
|---|---|---|
| Aesthetic interpretation and differentiated concepts | [visual-direction](../visual-direction/SKILL.md) | Selected design direction |
| Responsive, accessibility, performance, motion, visual regressions | [frontend-verification](../frontend-verification/SKILL.md) | Evidence-based review |
| Production architecture and non-generic rules | `references/production-method.md` | Maintainable implementation |
| Check color contrast deterministically | `scripts/contrast_check.py` | Ratios and pass/fail JSON |
| Start design direction artifact | `assets/VISUAL_DIRECTION.md` | Reviewable direction |

Read only the supporting skill or reference needed for this task. Linked skills are package-relative;
load their SKILL.md directly when the host has no invocation command. Templates are optional.

## Experience workflow

1. Establish direction and information architecture.
2. Model critical user flows, navigation, states, and content hierarchy.
3. Wireframe only where it resolves structure or interaction.
4. Build a prototype or mock-data implementation for risky concepts.
5. Review with the user and iterate a bounded number of times.
6. Define production component boundaries, state ownership, data fetching, cache, routing, forms,
   validation, tokens, theming, localization, tests, performance, and bundle strategy.
7. Remove prototype scaffolding and mocks; reuse only validated components and concepts.
8. Integrate real loading, empty, error, permission, offline, and recovery states.
9. Verify responsiveness, zoom, keyboard, screen reader, contrast, touch, reduced motion,
   performance, and visual regressions.

## Non-generic design

Follow explicit user direction and established product design. Avoid arbitrary rounded-card grids,
purple gradients, gratuitous glass, meaningless hero
metrics, random icons, weak hierarchy, oversized emptiness, generic SaaS composition, inaccessible
contrast, and purposeless motion. Do not add decoration merely to appear distinctive.

Choose a concept anchored in user context and content. Reuse components when semantics and behavior
are truly shared; avoid a giant universal abstraction.

## Motion and advanced graphics

For WebGL, shaders, canvas, Three.js, spatial UI, parallax, or cinematic motion, define user benefit,
fallback, performance budget, reduced-motion behavior, low-power behavior, critical interaction
isolation, and graceful degradation.

## Platform and accessibility

Respect web, mobile, desktop, or hybrid conventions while preserving product identity. Accessibility
includes semantic structure, keyboard, focus, contrast, screen reader behavior, motion preference,
touch targets, form errors, content scaling, zoom, and platform APIs—not a final lint pass.

## Collaboration and delegation

Load another role only for a decision or verification that needs its guidance. The following roles
are available collaborators, not required stages or a requirement to spawn agents.

Use product for flows/acceptance, architecture for contracts, harness for component navigation, SDE
for adjacent implementation, SRE for independent E2E/accessibility/performance/visual tests, and
DevOps for previews/deployment. Claude may use the bundled accessibility reviewer; other hosts use a
requested bounded subagent.

## Output and evidence

Report selected direction, rejected alternatives, IA/flows, architecture, changed files, states,
responsive/accessibility/motion behavior, tests and visual evidence, unverified devices, and
prototype debt removed.

## Effects and guardrails

- Inspection, research, and review are reads.
- Requested design docs and frontend implementation are local writes.
- External design tools, deployments, analytics changes, and publishing need separate authorization.
- Do not silently turn prototype code or mock data into production.
- Do not claim visual, device, accessibility, or performance verification without running it.
