# Description Template — Epic

Descriptions are written in Jira wiki markup using `{panel}` macros.
Write connected prose, not mechanically filled placeholders. Use tables only for Scope and
component/risk breakdowns.

---

## Business Epic

```
{panel:title=Context|borderColor=#cccccc|titleBGColor=#dae8fc}
<Two or three sentences: who is affected, what the problem is, how it's handled today.
Example: "Managers manually transfer data from system A to B every day.
This takes 2 hours and causes errors in roughly 10% of cases.">
{panel}
{panel:title=Goal|borderColor=#cccccc|titleBGColor=#dae8fc}
Make it so <role> can <action>, in order to <benefit>.

<One or two sentences: what changes for the user once this ships.>
{panel}
{panel:title=User scenarios|borderColor=#cccccc|titleBGColor=#dae8fc}
*Main scenario:* As a <role>, I want <action>, so that <value>.

*Alternative:* <what else the user should be able to do>

*On error:* <what happens if something goes wrong>
{panel}
{panel:title=Scope|borderColor=#cccccc|titleBGColor=#dae8fc}
||In scope||Out of scope||
|<what we're doing>|<what we're not doing>|
|<what we're doing>|<what we're not doing>|
{panel}
{panel:title=Constraints and metrics|borderColor=#cccccc|titleBGColor=#dae8fc}
* <constraint / dependency>
* Success metric: <how we'll know it improved>
{panel}
```

---

## Technical Epic

```
{panel:title=Context|borderColor=#cccccc|titleBGColor=#dae8fc}
<Two or three sentences: what's wrong today, what concrete pain it causes.
Be specific — not "the code is bad" but "every deploy requires manually changing a link in three places.">

Continuing as-is is risky: <one sentence about the consequences of inaction>.
{panel}
{panel:title=Goal|borderColor=#cccccc|titleBGColor=#dae8fc}
<One clear sentence — what becomes possible once this ships.>

Business logic and system behavior do not change. <If there are external consumers: API contracts are preserved.>
{panel}
{panel:title=What's affected|borderColor=#cccccc|titleBGColor=#dae8fc}
||Component||What changes||Risk||
|<service / module / folder>|<description of the change>|High / Medium / Low|
|<CI/CD pipeline>|<description>|High / Medium / Low|
{panel}
{panel:title=Scope|borderColor=#cccccc|titleBGColor=#dae8fc}
||In scope||Out of scope||
|<what we're doing>|<what we're not doing>|
|<what we're doing>|<what we're not doing>|
{panel}
{panel:title=Constraints|borderColor=#cccccc|titleBGColor=#dae8fc}
* <compatibility / what must not break>
* <testing requirements>
* Rollback: <one phrase>
{panel}
```
