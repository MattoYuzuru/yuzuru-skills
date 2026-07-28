# MCP Authoring

Create an MCP server only for authenticated external services, controlled persistent tools,
queryable code intelligence, centrally observable execution, or shared state that local files
cannot safely provide.

Do not convert ordinary scripts into MCP for packaging. A server requires:

- named owning plugins and use cases;
- official protocol and host compatibility research;
- tool schemas with bounded output;
- authentication and least-privilege design;
- read/write/destructive classification;
- host/origin and redirect controls;
- timeouts, idempotency, and audit behavior;
- isolated tests and documented data retention;
- `.mcp.json` entries only after the server exists.

No MCP server is justified in the first engineering-suite release. Local repository analysis,
calculations, validation, and artifact assembly are safer as deterministic package scripts.
