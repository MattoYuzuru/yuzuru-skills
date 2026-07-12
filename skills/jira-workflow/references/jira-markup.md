# Jira Wiki Markup Cheat Sheet

Issue descriptions are written in Jira wiki markup, **not Markdown**.

| Need                 | Markdown            | Jira wiki markup       |
|-----------------------|--------------------|-------------------------|
| Heading h2            | `## Heading`        | `h2. Heading`           |
| Heading h3            | `### Heading`       | `h3. Heading`           |
| Bold                  | `**text**`          | `*text*`                |
| Italic                | `_text_`            | `_text_`                |
| Inline code           | `` `code` ``        | `{{code}}`              |
| Code block            | ` ```code``` `      | `{code}code{code}`      |
| Link                  | `[text](url)`       | `[text\|url]`           |
| Bullet list           | `- item`            | `* item`                |
| Numbered list         | `1. item`           | `# item`                |
| Table header          | `\| col \| col \|`  | `\|\|col\|\|col\|\|`    |
| Table row             | `\| val \| val \|`  | `\|val\|val\|`          |
| Horizontal rule       | `---`               | `----`                  |
| Quote                 | `> text`            | `{quote}text{quote}`    |

## Table example

```
||Component||Change||Risk||
|Source code|Split into modules|Medium|
|CI/CD pipeline|Automate deploy|High|
```

## Code block example

```
{code:language=bash}
git push origin main
{code}
```

## Key differences from Markdown

- Bold in Jira is `*text*`, not `**text**`.
- Headings are `h2. Text`, not `## Text`.
- Tables use double `||` for headers and single `|` for cells.
- Links are `[label|url]`, not `[label](url)`.
