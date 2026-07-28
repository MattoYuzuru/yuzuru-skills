# Frontend Production Method

## Architecture

Define component composition, state ownership, server/client boundary, fetching and cache,
navigation, forms and validation, loading/empty/error/offline states, tokens, theming, localization,
accessibility, testing, performance, and bundle strategy using the target stack's conventions.

## Non-generic review

Ask whether each card, surface, icon, gradient, animation, and empty region serves hierarchy,
comprehension, interaction, or brand. Remove decorative defaults. A strong concept should remain
recognizable in grayscale and without animation.

## Productionization gate

Before integrating:

- replace mock data and placeholder copy;
- model failure, permissions, latency, and cancellation;
- remove prototype routing/state shortcuts;
- preserve only proven abstractions;
- add responsive, keyboard, screen-reader, reduced-motion, and performance behavior;
- define visual/E2E regression evidence.
