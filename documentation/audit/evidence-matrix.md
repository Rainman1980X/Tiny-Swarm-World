# Evidence Matrix

This matrix separates the location and state of evidence from the finding or
requirement it supports. `Present` means that the referenced repository path
exists; it does not mean that the related requirement is accepted or that an
audit is closed.

## Evidence categories and states

Required categories are `repository documentation`, `static quality-gate`,
`architecture`, `security`, `live`, `review` and `release`.

Evidence states include `Present`, `Evidence pending`, `Planned`, `Missing`,
`Blocked`, `Refused`, `Resource-gated`, `Failed-to-apply` and
`Failed-to-verify`. None of the non-present states is a pass. A local quality
gate is repository/static evidence only; it is not live, browser, installation
or external-service evidence.

## Matrix

| Evidence ID | Evidence name | Evidence type | Source path/expected path | Related requirement/finding | Status | Redaction requirement | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `EVD-121-001` | Repository README | repository documentation | `README.md` | REQ-121-071; documentation baseline | Present | No secrets or private host data | Source path exists; content applicability is reviewed separately. |
| `EVD-121-002` | Agent governance | repository documentation | `AGENTS.md` | REQ-121-072; architecture/safety rules | Present | Do not add local environment output | Governing repository instructions. |
| `EVD-121-003` | Quality policy | repository documentation | `QUALITY.md` | REQ-121-073, REQ-121-103, REQ-121-104 | Present | Do not record credentials or raw logs | Defines local and external verification distinctions. |
| `EVD-121-004` | Import boundary contract | static quality-gate; architecture | `.importlinter` | REQ-121-074; architecture evidence | Present | No runtime output required | Configuration source for architecture linting. |
| `EVD-121-005` | Repository quality gate | static quality-gate | `tools/quality_gate.py` | REQ-121-075, REQ-121-103, REQ-121-104 | Present | Record summaries, not raw sensitive output | The full gate result is recorded in issue evidence. |
| `EVD-121-022` | Hexagonal architecture test | architecture; static quality-gate | `tests/architecture/test_hexagonal_imports.py` | REQ-121-107; architecture evidence | Present | No raw environment data | Architecture-test source path named by issue #121. |
| `EVD-121-006` | Assembled arc42 book | architecture | `documentation/arc42.adoc` | REQ-121-076; architecture boundary | Present | No local host data | Canonical assembled architecture entry point. |
| `EVD-121-007` | Quality requirements | architecture; repository documentation | `documentation/arc42/10_quality_requirements.adoc` | REQ-121-077; MAJ-03 | Present | No raw run data | Architecture quality baseline. |
| `EVD-121-008` | Risks and technical debt | architecture; security | `documentation/arc42/11_risks_and_debt.adoc` | REQ-121-078; MAJ-01, MAJ-04 | Present | No secrets or private infrastructure data | Risk source; unresolved risks remain unresolved. |
| `EVD-121-009` | Live operation surfaces | repository documentation; security | `documentation/system/live-operation-surfaces.adoc` | REQ-121-079; MAJ-02, MAJ-04 | Present | Do not copy raw command output | Documents potentially mutating surfaces, not evidence of a live run. |
| `EVD-121-010` | User guides | repository documentation | `documentation/user_guide/` | REQ-121-080, REQ-121-102; MIN-01 | Present | No credentials, tokens or private host data | Canonical installation, usage and troubleshooting sources. |
| `EVD-121-011` | Issue-named operator contract path | repository documentation | `documentation/configuration/operator-configuration-contract.md` | REQ-121-081 | Missing | Must not contain copied local config | Missing/stale path named by issue #121; it is not treated as present. |
| `EVD-121-012` | Canonical operator contract | repository documentation; security | `documentation/arc42/08_configuration/operator-configuration-contract.md` | REQ-121-081; REQ-121-010 | Present | No secret values | Present canonical replacement for the stale issue-named path. |
| `EVD-121-013` | Audit evidence index | repository documentation; review | `documentation/audit/README.md` | REQ-121-011, REQ-121-016 through REQ-121-038 | Present | Redaction rules apply to future additions | This issue creates the governance index; it is not certification evidence. |
| `EVD-121-014` | Audit and findings registers | review | `documentation/audit/audit-register.md`, `documentation/audit/findings-register.md` | REQ-121-012, REQ-121-013, REQ-121-039 through REQ-121-068 | Present | No raw finding logs or private data | Stable IDs and dispositions are recorded. |
| `EVD-121-015` | Remediation workflow plan | review; release governance | `documentation/audit/remediation-plan.md` | REQ-121-015, REQ-121-083 through REQ-121-097 | Present | No secrets or unredacted run output | Ten #120 workflows are mapped. |
| `EVD-121-016` | Requirement matrix | review | `.tiny-swarm/evidence/issue-121/requirement_matrix.md` | REQ-121-001 through REQ-121-106; MAJ-03 | Present | Matrix contains no live payloads | Intentionally tracked issue evidence. |
| `EVD-121-017` | Security governance/control mapping | security | Expected: `documentation/security/` and issue-specific control artifacts | MAJ-01, MAJ-04, MIN-02, MIN-07 | Planned | Redacted summaries only | Follow-up work is owned by #123, #126 and #150; no absent path is claimed present. |
| `EVD-121-018` | Live green-path run evidence | live | Expected: protected redacted run evidence defined by #125 | REQ-121-048, REQ-121-082; MAJ-02 | Planned | Explicit consent; redact secrets, tokens, paths, IPs and raw output | No live infrastructure was run for #121. |
| `EVD-121-019` | Review and completion evidence | review | `.tiny-swarm/evidence/issue-121/` | REQ-121-105; MIN-08 | Present | No raw logs or private data | Matrix, implementation summary, checks, risks and acceptance evidence. |
| `EVD-121-020` | Release/baseline evidence | release | Expected: release/baseline artifact defined by #120 | REQ-121-097, REQ-121-106; MIN-06 | Planned | Redacted release metadata only | Planned until release/baseline governance is executed. |
| `EVD-121-021` | Supply-chain prerequisite evidence | security; release | `documentation/security/supply-chain-security.md`, `documentation/security/sbom-policy.md`, `documentation/security/dependency-scan-policy.md`, `documentation/security/container-image-scan-policy.md`, `tools/security_gate.py` | MIN-02; #127 prerequisite | Present | Never copy credentials or registry output. | The workflow index records #127 as closed; this row does not re-close it. |
| `EVD-121-022` | Audit summary snapshot | repository documentation; review | `documentation/audit/audit-summary.md` | REQ-121-051, REQ-121-052; MAJ-01 through MAJ-05; MIN-01 through MIN-08 | Present | No raw issue payloads or private data | Local source snapshot for the explicitly enumerated #120/#121 finding set; no closure claim. |

## Evidence review rules

- Every evidence row must identify a source or explicitly say `Expected`.
- A missing path is recorded as `Missing`, not silently redirected.
- A planned future artifact stays `Planned` until the named workflow produces
  and reviews it.
- Raw live output is not an acceptable committed evidence artifact.
- A quality-gate result must name the command, environment, result and scope;
  local success must not be described as live or external success.
