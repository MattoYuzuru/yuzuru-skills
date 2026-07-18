# batchUpdate recipes

Save the JSON array in a local file and run
`batch-update <spreadsheet-id> --requests-file <path>`. The helper validates a maximum of 100
single-operation requests and rejects destructive operation types before calling
`spreadsheets.batchUpdate`. Get the target `sheetId`
(an integer, not the sheet's title) from `info <spreadsheet-id>` first — never guess it.

Always run once with `--dry-run`, obtain approval, then add `--confirm-write`.

## Freeze a header row

```json
[{"updateSheetProperties": {
  "properties": {"sheetId": 0, "gridProperties": {"frozenRowCount": 1}},
  "fields": "gridProperties.frozenRowCount"
}}]
```

## Resize a column

```json
[{"updateDimensionProperties": {
  "range": {"sheetId": 0, "dimension": "COLUMNS", "startIndex": 0, "endIndex": 1},
  "properties": {"pixelSize": 200},
  "fields": "pixelSize"
}}]
```

## Merge cells

```json
[{"mergeCells": {
  "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 0, "endColumnIndex": 3},
  "mergeType": "MERGE_ALL"
}}]
```

## Bold + background a header row

```json
[{"repeatCell": {
  "range": {"sheetId": 0, "startRowIndex": 0, "endRowIndex": 1},
  "cell": {"userEnteredFormat": {"textFormat": {"bold": true}, "backgroundColor": {"red": 0.85, "green": 0.85, "blue": 0.85}}},
  "fields": "userEnteredFormat(textFormat,backgroundColor)"
}}]
```

## Conditional formatting (highlight values > 100)

```json
[{"addConditionalFormatRule": {
  "rule": {
    "ranges": [{"sheetId": 0, "startRowIndex": 1, "endRowIndex": 100, "startColumnIndex": 2, "endColumnIndex": 3}],
    "booleanRule": {
      "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "100"}]},
      "format": {"backgroundColor": {"red": 1.0, "green": 0.9, "blue": 0.9}}
    }
  },
  "index": 0
}}]
```

## Pivot table

A pivot table is a single cell's value, placed via `updateCells`. Typical flow:

1. `info <id>` to get the source data sheet's `sheetId` and its used row/column bounds.
2. `add-sheet <id> --title "Pivot"` for a destination sheet, then `info <id>` again to read its
   new `sheetId`.
3. `batch-update` with the source range (include the header row — its cells become field
   labels) and `sourceColumnOffset` values counted from the *start* of that source range:

```json
[{"updateCells": {
  "rows": [{"values": [{"pivotTable": {
    "source": {"sheetId": 0, "startRowIndex": 0, "startColumnIndex": 0, "endRowIndex": 100, "endColumnIndex": 4},
    "rows": [{"sourceColumnOffset": 0, "showTotals": true, "sortOrder": "ASCENDING"}],
    "columns": [{"sourceColumnOffset": 1, "showTotals": true, "sortOrder": "ASCENDING"}],
    "values": [{"summarizeFunction": "SUM", "sourceColumnOffset": 3}]
  }}]}],
  "start": {"sheetId": 1, "rowIndex": 0, "columnIndex": 0},
  "fields": "pivotTable"
}}]
```

This groups by source column 0 (rows), pivots on source column 1 (columns), and sums source
column 3 into the values area, anchored at the top-left cell of the destination sheet
(`sheetId: 1` above — substitute the real destination `sheetId` from step 2).
`summarizeFunction` also accepts `COUNT`, `AVERAGE`, `MIN`, `MAX`, `COUNTA`, `PRODUCT`, and more
— match it to what the user actually asked to summarize.

## Combining requests

The `requests` array runs atomically in order — put several of the recipes above in one array
to do them in a single `batch-update` call instead of one call per change.
