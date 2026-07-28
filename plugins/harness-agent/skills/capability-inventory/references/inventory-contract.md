# Capability Inventory Contract

Each entry should provide:

- stable ID and kind;
- when to use it;
- invocation or native manager;
- read/local-write/external-write/destructive effect;
- credential names or profiles, never values;
- availability, installation, enabled, auth, and health state as separate facts;
- owner and documentation;
- last evidence and source revision when available.

Use `schemas/capability-inventory.schema.json` in a Yuzuru repository or reproduce its compact
fields in another project.
