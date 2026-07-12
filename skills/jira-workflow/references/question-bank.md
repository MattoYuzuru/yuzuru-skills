# Questions For Creating Issues

Detailed questions for each issue type. Ask them in the grouped blocks below — ask the user to
confirm or choose an answer for each block before moving to the next one.

---

## Epic

Determine the subtype first: **Business Epic** or **Technical Epic**.

### Business Epic — 3 blocks

**Block 1 (context):**
- Who is this for? (end user / internal team / business stakeholder / other)
- What's the problem today? (missing functionality / inconvenient / slow / other)
- How is it handled today? (manually / workaround / not at all / other)

**Block 2 (goal):**
- What should become possible? (free text)
- What benefit is expected? (metric growth / time savings / fewer errors / other)
- Is there a success metric? (yes — specify / no / not yet known)

**Block 3 (boundaries):**
- What's in scope? / What's out of scope? / Are there deadlines?

### Technical Epic — 3 blocks

**Block 1 (context):**
- What's causing problems? (tangled code / no tests / manual processes / all of the above / other)
- What's the impact on the team? (slow to change / risky to deploy / frequent bugs / other)
- Why now? (team grew / large feature coming / tech debt piled up / other)

**Block 2 (goal):**
- What should change? (modularity / CI/CD / tests / all of the above / other)
- What stays unchanged? (API contracts / business logic / integrations / other)
- Is backward compatibility required? (yes / no / partially)

**Block 3 (components and boundaries):**
- What's affected? (multi-select: backend / frontend / database / CI/CD / infrastructure / other)
- Is a rollback plan needed? (yes / no / decide during implementation)

---

## Feature

Determine the subtype first: **Business Feature** or **Technical Feature**.

**Block 1 (context + goal):**
- What does this feature do? (free text)
- Who's it for? (end user / internal team / system / other)
- What problem does it solve? (free text)

**Block 2 (boundaries):**
- What's in scope? (free text)
- What's out of scope? (free text)

---

## Engineering Task

One block of 3 questions:
- What exactly are we doing? (refactor / migration / tech debt / CI/CD setup / other)
- Why is it needed now? (free text)
- What stays unchanged? (API contracts / business logic / production behavior / other)
