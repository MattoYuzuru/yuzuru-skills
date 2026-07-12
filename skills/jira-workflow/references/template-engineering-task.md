# Description Template — Engineering Task

Descriptions are written in Jira wiki markup using `{panel}` macros. One concrete technical step —
no filler.

```
{panel:title=What we're doing|borderColor=#cccccc|titleBGColor=#ffe6cc}
<One sentence: the concrete technical action.
Example: "Migrate deploy configuration from manual steps to a GitLab CI pipeline.">
{panel}
{panel:title=Why|borderColor=#cccccc|titleBGColor=#ffe6cc}
<One or two sentences: what pain this removes or what risk it eliminates.
Be concrete — not "the code is bad" but "every deploy requires an engineer to manually edit 3 configs.">
{panel}
{panel:title=Scope|borderColor=#cccccc|titleBGColor=#ffe6cc}
||In scope||Out of scope||
|<what we're doing>|<what we're not touching>|
|<what we're doing>|<what we're not touching>|
{panel}
{panel:title=Constraints|borderColor=#cccccc|titleBGColor=#ffe6cc}
* Production behavior does not change
* <what must not break — API, integrations, contracts>
* Rollback: <one phrase, or "not required">
{panel}
```
