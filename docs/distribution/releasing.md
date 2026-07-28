# Release and Versioning

Every plugin has `plugin-version.json` as its canonical semantic version. Both manifests must match.
Marketplace entries omit versions and defer to the plugin manifest.

Release procedure:

1. update the canonical version for changed plugins;
2. run `python3 scripts/sync_plugin_versions.py`;
3. update relevant package README limitations or behavior;
4. run all structural, unit, cleanliness, eval, and available official validations;
5. review the exact diff and migration registry;
6. create a focused local commit and tag only when the release target is approved;
7. push or publish only after separate explicit confirmation.

Use major versions for incompatible package or artifact contracts, minor versions for new
capabilities, and patch versions for compatible fixes. Do not publish a marketplace or claim
release readiness based only on file creation.
