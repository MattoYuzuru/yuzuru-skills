---
name: defensive-security-review
description: Perform an authorized defensive security review and validate suspected vulnerabilities against project-specific trust boundaries. Use when code, configuration, dependencies, or behavior needs security-focused verification.
---

# Defensive Security Review

Read `references/security-method.md` before classifying a suspected vulnerability.

## Workflow

1. Confirm authorization, target, revision, data sensitivity, excluded systems, and allowed effects.
2. Reconstruct assets, actors, tenants, trust boundaries, authn/authz, inputs, redirects, secrets,
   storage, dependencies, and audit requirements.
3. Inspect injection, IDOR, SSRF, traversal, deserialization, XSS, CSRF, secret exposure,
   dependencies/supply chain, defaults, privilege, credential forwarding, isolation, rate limits,
   sensitive logging, and temporary files as relevant.
4. Validate reachability, preconditions, exploitability, mitigating controls, impact, and evidence.
5. Use safe local fixtures or authorized environments; avoid harmful payloads and unrelated targets.
6. Classify with the finding-validation skill and propose regression evidence.

## Guardrails

- A scanner warning is not a confirmed vulnerability.
- Do not expose secrets in evidence or forward credentials across hosts.
- Do not test third-party or production systems beyond exact authorization.
- Do not provide a formal threat-model claim unless that scope was performed.

## Output

Return scope, trust model, confirmed/probable/risk/hypothesis findings, evidence, affected
requirement, remediation direction, regression checks, and untested attack surfaces.
