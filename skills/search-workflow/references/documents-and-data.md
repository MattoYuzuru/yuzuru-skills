# Documents and structured data

Read this reference only for non-plain-text formats or queries that depend on data structure.

## Documents and archives

Use `rga` for PDFs with a text layer, Office documents, ebooks, SQLite databases, media metadata,
and nested archives. It wraps `rg`, so keep the same staged workflow:

```bash
rga -l -F 'invoice number' documents/
rga -n -F 'invoice number' documents/selected.pdf
rga --rga-list-adapters
```

The Poppler adapter supplies PDF extraction; Pandoc supplies Office, ebook, notebook, and markup
conversion. `rga` caches extracted text, so repeated searches may be much faster. A scanned image
PDF has no searchable text layer: report that limitation and use an authorized OCR workflow rather
than claiming the term is absent.

Official adapter list: <https://github.com/phiresky/ripgrep-all#available-adapters>

## JSON

Use `jq` when nesting, types, or escaped values matter. Emit compact values or paths and cap the
result:

```bash
jq -c 'path(.. | select(type == "string" and contains("needle")))' data.json | sed -n '1,50p'
jq -c '.items[] | select(.status == "failed") | {id,status}' data.json | sed -n '1,50p'
```

Use `rg` instead when the task is only to locate a literal across many unknown files.

## YAML and related formats

Use Mike Farah `yq` v4 for YAML, XML, TOML, CSV, and properties files. Verify the implementation
with `yq --version`; another unrelated Python package uses the same executable name.

```bash
yq -o=json '.services[] | select(.enabled == true)' config.yaml
```

Constrain or summarize large arrays before returning output to model context.
