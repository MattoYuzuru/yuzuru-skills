# Messenger connector contract

Use this reference to map intent onto whatever compatible messenger connector is installed. Tool
names are not portable; inspect schemas rather than guessing names.

## Capability map

| Semantic capability | Minimum inputs | Expected result |
|---|---|---|
| account/workspace identity | none | stable account and workspace identity |
| destination lookup | exact handle/name query | candidate IDs, kind, display name |
| history | destination ID, optional thread/time/cursor/limit | chronological messages and next cursor |
| search | query plus bounded scope/time/limit | matching messages with destination/thread IDs |
| send | destination ID, content, optional thread ID | created message ID and final content |
| reaction | message ID and reaction | resulting reaction state |
| pin | destination and message IDs | resulting pin state |
| unread and mentions | bounded list/filter | counters/messages without implicit read mutation |
| mark read/unread | exact destination and provider-required anchor | resulting read state |
| thread | destination plus root/thread ID | bounded replies and next cursor |
| topic | destination plus native topic ID | topic metadata/messages or explicit unsupported outcome |
| attachment | file/message ID or authorized local path | metadata/cache path/upload ID/send result |
| conversation management | resolved conversation plus requested change | resulting conversation state |

The connector may omit capabilities. Degrade explicitly: never emulate a missing write with an
undocumented endpoint, and never claim a complete search when pagination or scope is unavailable.

## Target resolution

- Distinguish users, DMs, group conversations, public channels, private channels, and threads.
- Keep ordinary reply threads distinct from forum/channel topics even when one provider uses a
  related numeric ID internally.
- Prefer IDs from a prior read in the same workflow. Display names and handles are not globally
  unique unless the connector guarantees it.
- For a reply, retain the parent thread ID. Do not post a new top-level message merely because the
  reply tool is unavailable.
- Before a destructive operation, re-read the target and bind confirmation to its stable ID.

## Bounded reads

- Start with a narrow time range and 20–50 results. Expand only when evidence is insufficient.
- For commitment extraction, record owner, action, deadline, evidence message, and confidence.
- Treat edited/deleted messages and inaccessible pages as coverage gaps.
- Keep direct quotations short and necessary. Return links or IDs instead of copying entire threads.

## Write failures

- On validation errors, correct the preview before executing again.
- On 401/403, stop and report the missing identity, membership, or scope.
- On 404, re-resolve the target once; do not guess a replacement.
- On timeout, 429, or 5xx after submission, treat the outcome as ambiguous. Re-read by returned ID or
  an exact bounded content/time query before deciding whether another send is safe.

## Read state and files

- Listing history, unread items, or mentions must not silently mark anything read.
- Call a read-state mutation only when the user explicitly requests it and authorization applies.
- Keep downloads inside the connector's documented cache unless the user authorizes an exact local
  destination. Do not overwrite an existing file implicitly.
- Upload/send only an exact authorized local file within the connector's size bound.
- Prefer provider-native forwarding; do not bypass protected-content behavior by copying text.
