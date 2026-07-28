# Candidate evidence

A deletion recommendation needs the path and owner, why it appears obsolete, static reference
results, dynamic/configuration/loading risk, build and deployment use, tests, Git history, retention
requirements, reproducibility, recovery path, confidence, and post-change checks.

Filename patterns are weak evidence. Common runtime outputs may be high-confidence only when the
project does not intentionally version them. “No static references” remains insufficient for public
APIs, reflection, framework conventions, plugins, migrations, configuration keys, assets, or files
consumed by another repository.
