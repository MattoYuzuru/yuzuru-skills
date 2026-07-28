# Frontend Agent

Combines UX research, visual direction, interaction design, design systems, frontend architecture,
implementation, accessibility, responsiveness, motion, and visual verification.

## Capabilities

- Translates aesthetic requests into implementable and accessible system qualities.
- Produces differentiated design directions instead of generic generated dashboards.
- Prototypes risky ideas and deliberately productionizes validated concepts.
- Verifies states, responsiveness, accessibility, performance, and visual regressions.

## Trigger examples

- “Design a dense professional terminal interface.”
- “Create three real directions for a cinematic landing page.”
- “Productionize this mock-data dashboard and verify accessibility.”

## Non-trigger examples

- “Implement this backend API.”
- “Change one CSS variable.”
- “Only run independent release verification.”

## External effects

Inspection/research are reads; requested design/frontend changes are local writes. Design-tool
publishing, analytics, deployments, and external assets require separate authorization.

## Platform support

Portable skills/scripts run on Codex and Claude Code. Claude includes an accessibility reviewer;
other hosts use a requested bounded subagent.

## Local testing

Run `yuzuru plugin validate frontend-agent`, contrast tests, frontend evals, and target-project
visual/accessibility checks.

## Limitations

The plugin ships no browser, device farm, font, image generator, or MCP server. Runtime claims
depend on available target-project tools and tested devices.
