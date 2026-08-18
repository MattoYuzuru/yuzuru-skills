---
name: russian-editorial-style
description: Edit, rewrite, or draft Russian prose for clarity, audience fit, genre, and a natural authorial voice while preserving facts and intent. Use when the user requests Russian technical documentation, essays, articles, business copy, short-form writing, social posts, or asks «убери канцелярит», «сделай естественнее», or «перепиши под эту аудиторию»; do not use for translation-only, grammar explanation, factual research, or AI-authorship detection.
---

# Russian Editorial Style

## Overview

Edit or draft Russian prose around the reader's task, the requested genre, and
the author's intent. Optimize for comprehension, usefulness, content
preservation, and an appropriate voice—not for AI-detector scores or a generic
idea of “human” writing.

## Routing

| Intent | Read | Deliver |
|---|---|---|
| Diagnose without rewriting | `references/editorial-core.md` | Prioritized findings |
| General edit or rewrite | `references/editorial-core.md` | Minimally sufficient revision |
| Adapt audience, register, or voice | `references/audience-and-voice.md` | Audience-calibrated text |
| Edit technical or instructional prose | `references/technical-writing.md` | Precise task-oriented text |
| Edit an essay, article, or explanation | `references/long-form.md` | Coherent long-form prose |
| Write short copy or a social post | `references/short-form.md` | Concise channel-fit text |

Read only the selected reference. Read `references/evidence-and-limitations.md`
when evaluating or changing the method itself, not for ordinary editing.

## Workflow

1. Determine the requested artifact, audience, reader task, genre, channel,
   tone, length, and edit depth. Infer conservatively from context. Ask only
   when a choice would materially change the result.
2. Record protected content before editing:
   - names, numbers, dates, units, URLs, citations, and quotations;
   - code, commands, UI labels, identifiers, and required terminology;
   - negation, causality, conditions, comparisons, and uncertainty;
   - claims whose strength or attribution must not change.
3. Diagnose the few highest-impact problems by reader effect:
   - the main point or required action is hard to find;
   - actor, action, referent, condition, or sequence is unclear;
   - a premise is missing or a claim is unsupported;
   - terminology or point of view drifts;
   - structure, register, or detail does not fit the audience;
   - repetition adds no function.
4. Revise content and organization before sentence style. Make only changes
   that serve the requested goal; stop when the goal is met.
5. Prefer familiar precise wording, explicit referents, and concrete evidence
   already present in the source. Preserve necessary abstraction and stable
   technical terms.
6. Preserve useful author-specific choices. Do not manufacture quirks,
   anecdotes, emotion, slang, or biographical details.
7. Run a separate preservation pass. For high-risk or substantial rewrites,
   run `scripts/check_invariants.py` with the source and revision paths, inspect
   every warning, and add repeatable `--term` arguments for protected terminology.
8. Return the requested artifact first. Add diagnosis or a change summary only
   when requested or when unresolved ambiguity matters.

## Edit Depth

- **Audit:** identify problems and their reader impact; do not rewrite.
- **Copyedit:** correct local clarity, grammar, punctuation, and consistency
  while preserving structure and voice.
- **Structural edit:** reorganize and rewrite where needed for the reader task.
- **Draft:** write from supplied facts, outline, examples, and constraints;
  separate missing information from facts.

Use the least invasive level that satisfies the request. If the source already
works, retain it with little or no change.

## Output Contract

Unless the user asks for commentary, output only the finished Russian text.
For audit mode, use compact findings with:

1. the affected excerpt or location;
2. the reader-facing problem;
3. priority (`blocker`, `material`, or `minor`);
4. a proposed direction, not a full rewrite.

When a constraint cannot be met without changing meaning, preserve meaning and
state the conflict briefly.

## Guardrails

- Do not invent facts, sources, numbers, examples, experience, urgency,
  consensus, or an author's opinion.
- Do not silently strengthen possibility into certainty, association into
  causation, recommendation into obligation, or a limited claim into a general one.
- Do not alter quotations, code, commands, identifiers, links, or legally
  operative wording unless the user explicitly includes them in scope.
- Do not replace a repeated technical term merely for lexical variety.
- Prefer active voice when it clarifies responsibility. Keep passive voice
  when the affected object, procedure, result, or unknown actor is the topic.
- Keep nominalizations that name stable concepts; unpack them when they hide
  actors, actions, or causal relations the reader needs.
- Preserve normative Russian spelling and punctuation. Never add deliberate
  errors, rough typography, profanity, idioms, particles, or sentence-length
  variation as proof of human authorship.
- Use headings, lists, and connectives when they expose real structure. Do not
  add or remove them by quota.
- Do not infer authorship or report an “AI percentage.” If asked to evade a
  detector, offer substantive editorial improvement and explain that detector
  outcomes are unreliable; never promise a pass.
- For legal, medical, financial, policy, or other high-stakes text, limit work
  to the requested editorial scope and flag wording whose alteration may change
  obligations or risk.
