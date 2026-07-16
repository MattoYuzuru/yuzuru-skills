# A1 ranges and value semantics

## A1 notation

- `A1` — one cell.
- `A1:B10` — a rectangular range.
- `Sheet1!A1:B10` — sheet-qualified; required whenever the spreadsheet has more than one sheet
  and the target isn't the first one. Sheet names with spaces or special characters need single
  quotes: `'Q1 Budget'!A1:B10`.
- `A:A` / `1:1` — a whole column/row.
- Omitting the range entirely (just `Sheet1`) targets the sheet's full used range on read; on
  write, always give an explicit range so the write target is unambiguous.

`sheets_api.py` URL-encodes whatever string is passed to `--range`; pass the notation above
verbatim, quotes and all, in a single shell argument.

## Writing values: `USER_ENTERED` vs `RAW`

`write`/`append` accept `--values` as a JSON 2D array, one inner array per row:

```bash
python3 scripts/sheets_api.py write SPREADSHEET_ID --range "Sheet1!A1:B2" \
  --values '[["Item", "Total"], ["Widgets", "=SUM(C1:C10)"]]'
```

- `USER_ENTERED` (default): Sheets parses each string exactly as if a human typed it — leading
  `=` becomes a formula, `"1/2"` may become a date, `"3.14"` becomes a number. This is what
  "add a formula" almost always means.
- `RAW`: every value is stored exactly as given, as a string/number/bool with no reinterpretation.
  Use this when a literal value must not be reinterpreted (e.g. a text cell that legitimately
  starts with `=` or a code like `"007"` that must not become the number `7`).

Numbers and booleans in the JSON (`42`, `true`) are always sent as their native JSON type,
independent of `--value-input`; the option only changes how *string* values are interpreted.

## Reading values: `--value-render`

`read`/`read-batch` accept `--value-render`:

- `FORMATTED_VALUE` (default) — what the cell displays, e.g. `"$1,234.00"`.
- `UNFORMATTED_VALUE` — the underlying number/string/bool without display formatting.
- `FORMULA` — the formula text itself (`"=SUM(A1:A10)"`) instead of its computed result —
  use this specifically when the task is to inspect or reason about formulas, not their output.

## Batch reads

`read-batch` takes a comma-separated list and returns each range's values in one call — prefer
it over multiple `read` calls when several ranges (possibly across sheets) are needed for one
task, to keep request count and latency down.
