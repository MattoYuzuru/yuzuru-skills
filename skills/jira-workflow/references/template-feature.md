# Description Template — Feature

Descriptions are written in Jira wiki markup using `{panel}` macros. Keep the text tight, no filler.

---

## Business Feature

```
{panel:title=What we're doing|borderColor=#cccccc|titleBGColor=#d5e8d4}
<One or two sentences: the concrete feature, what it gives the user.>
{panel}
{panel:title=Who and why|borderColor=#cccccc|titleBGColor=#d5e8d4}
<Who uses it, what problem it solves. No filler.>
{panel}
{panel:title=Scope|borderColor=#cccccc|titleBGColor=#d5e8d4}
||In scope||Out of scope||
|<what we're doing>|<what we're not doing>|
|<what we're doing>|<what we're not doing>|
{panel}
```

---

## Technical Feature

```
{panel:title=What we're doing|borderColor=#cccccc|titleBGColor=#d5e8d4}
<One or two sentences: the concrete technical improvement.>
{panel}
{panel:title=Why now|borderColor=#cccccc|titleBGColor=#d5e8d4}
<Why this is needed now, what risk it reduces.>
{panel}
{panel:title=What's affected|borderColor=#cccccc|titleBGColor=#d5e8d4}
* <component / module> — <what changes>
* <component / module> — <what changes>
{panel}
{panel:title=Scope|borderColor=#cccccc|titleBGColor=#d5e8d4}
||In scope||Out of scope||
|<what we're doing>|<what we're not doing>|
|<what we're doing>|<what we're not doing>|
{panel}
```
