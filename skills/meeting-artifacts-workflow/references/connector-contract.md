# Meeting connector contract

Use semantic capabilities instead of relying on a particular server or tool name.

## Capability map

| Semantic capability | Minimum inputs | Expected result |
|---|---|---|
| session/current user | none | authenticated state and non-secret user identity |
| refresh recent artifacts | bounded day range | refreshed meeting count and coverage window |
| list meetings | cursor/offset and limit | stable meeting IDs, title, date, participants, next page |
| search artifacts | terms, optional meeting IDs, artifact kinds, cursor/limit | snippets with meeting/artifact identity and position |
| get summary or minutes | meeting or recording ID, cursor/limit | ordered text lines and next page |
| get transcript or chat | meeting ID, cursor/limit | timestamped/speaker-attributed lines when available |

If a connector exposes fewer capabilities, state the missing surface. A local cache is not evidence
that its coverage window is current; report its last refresh when available.

## Retrieval strategy

1. Resolve an explicit recording URL or stable ID directly.
2. Otherwise list a narrow recent window and match title/date/participants.
3. For topical questions, search first and fetch surrounding pages only for relevant hits.
4. Use summary/minutes to identify claims, then transcript/chat to substantiate disputed or precise
   wording. Do not fetch every artifact by default.

## Evidence model

- Mark a statement as a recorded decision only when the artifact presents it as decided.
- An action item needs an action and an owner; if either is absent, place it under open follow-ups.
- Preserve explicit deadlines exactly. Do not derive a date from words such as “soon” or “next”.
- Attribute transcript text only when speaker mapping is present; otherwise label the speaker unknown.
- Cite stable meeting ID plus timestamp/line position or source link. If none exists, cite artifact kind
  and page/offset and say that the connector supplied no stable deep link.

## Failure handling

- On missing/expired session, stop and request login; do not inspect credential stores.
- On 401/403, report the access boundary without repeated retries.
- On missing artifact, try one alternate available kind (for example summary instead of transcript)
  only when it can answer the same question.
- On truncated results, distinguish “not found in inspected coverage” from “does not exist”.
