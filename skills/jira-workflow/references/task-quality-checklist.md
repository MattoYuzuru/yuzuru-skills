# Jira Task Quality Checklist

Use this checklist for the quality-check workflow before moving an issue to Review, or before
handing it off to a delivery workflow.

## Minimum pass

| Check | Pass | Warning | Fail |
| --- | --- | --- | --- |
| Summary | Clear action and target | Somewhat general, but understandable from the description | Cannot tell what needs to be done |
| Context | Has a reason, problem, or source link | Context is partial | No context at all |
| Scope | Clear what's in and what's out | Scope is implied | Scope is vague |
| Acceptance criteria | Has verifiable criteria | Has an expected result but no criteria | No criteria for done |
| Links | Has Epic / parent / related issues where relevant | Links are incomplete | Issue is disconnected from the initiative |
| Owner | Has an assignee or a clear next owner | Owner is being discussed | Owner is undefined |
| Priority | Priority is set and looks reasonable | Priority is unclear | Priority is missing |
| Risks | Risks are explicitly stated for production/data/money/security | Risks can be inferred from the text | Risks aren't considered |
| Validation | Clear how to verify the result | Verification is described vaguely | Unclear how to prove it's done |

## Output for the user

Always return the result in this format:

```markdown
## Quality check <ISSUE_KEY>

### Verdict
<PASS / WARN / FAIL>

### Findings
- ok: ...
- warning: ...
- fail: ...

### Required before Review
- ...

### Suggested improvements
- ...
```

## Rules

- `PASS`: the issue can be picked up or moved forward.
- `WARN`: the issue can be picked up, but missing details must be explicitly noted.
- `FAIL`: clarify the issue first, then run the delivery workflow.
- Don't invent project-specific fields. If a field needs checking, read Jira metadata or the issue
  itself first.
