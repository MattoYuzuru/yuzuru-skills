# Security and Trust Model

Skills and plugins are executable trusted content. Users must review a marketplace source, package,
scripts, hooks, and MCP definitions before installation.

## Boundaries

- The repository stores no credentials, session cookies, user config, or enabled state.
- Native platform managers own marketplace registration, plugin cache, installation, and enabled
  state.
- Plugin scripts resolve exact local targets and reject path traversal.
- Hooks receive minimal event data, do not log secrets, and never call production systems.
- External writes require explicit authorization; destructive operations require the exact target.
- Production, uncontrolled load testing, and third-party targets remain outside default scope.

## Runtime locations

Repository CLI data follows XDG locations. Platform plugin data lives in the host-provided data
directory. Uninstall semantics are host-owned; the CLI does not delete platform data directly.

Secrets belong in environment variables, OS keychains, native secret stores, or scoped external
managers. Scripts must not echo them, forward them across origins, or embed them in artifacts.

## Supply chain

Marketplace entries use local package paths in this source repository. Remote consumers should pin
trusted refs or reviewed releases. Third-party dependency installation must be isolated, locked,
and explicit. This first release adds no MCP server or runtime dependency.
