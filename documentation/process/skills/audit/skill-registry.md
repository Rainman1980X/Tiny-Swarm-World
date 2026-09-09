# Skill Registry

## Status

```text
CURRENT_WITH_VALIDATED_DISCOVERY_AND_ISSUE_COMPLETION_GATES
```

This is the canonical Tiny Swarm World skill registry path. Repository files
remain the source of truth; this registry is an audit and navigation artifact.

## Authority

- Root engineering authority: `AGENTS.md`.
- Quality authority: `QUALITY.md`.
- Issue completion authority:
  `documentation/process/issue-completion-discipline.md`.
- Project-specific skills: `.agents/skills/<skill-name>/SKILL.md`.
- Reusable Codex skills: `.codex/skills/<skill-name>/SKILL.md`.
- Owner map: `documentation/process/skills/audit/owner-map.md`.
- Organigramm: `documentation/process/skills/audit/organigramm.md`.

## Current Registry Decision

- Required Tiny Swarm World project skills use the discoverable
  `.agents/skills/<skill-name>/SKILL.md` format.
- Grouped `.md` files under category directories are non-authoritative unless a
  later workflow changes local skill discovery.
- `.codex` skills remain reusable fallback or portable team assets, not the
  place for project-specific Tiny Swarm World policy.
- The removed `microservice-senior-expert` route is replaced by Senior System
  Architect plus `service-decomposition-bounded-context`,
  `microservice-runtime-readiness-expert`,
  `microservice-migration-safety-gate`, and `contract-governance-expert`.

## Current Counts

- Project-specific discoverable skills: 132.
- Project skill entrypoints with valid name and description frontmatter: 132.
- Reusable `.codex` skills: 6.
- Canonical required Tiny Swarm World skills: 48.
- Removed stale microservice-specific artifacts: 4.

## Audit-Derived Governance Skills

These skills were added for audit remediation workflows #121 through #130 and
local completion-discipline hardening. No existing skill was removed or
renamed; the new skills narrow ownership for issue completion, audit evidence,
QMS-light, ISMS-light, traceability, live evidence, ASVS mapping, supply chain
security, branch/CI governance, documentation audiences, and release baselines.

| Skill | Group | Owner Role | Primary Paths | Related Issues |
| --- | --- | --- | --- | --- |
| `issue-completion-auditor` | Governance and quality | Senior Requirement Engineer | `.agents/skills/issue-completion-auditor/SKILL.md`, `documentation/process/issue-completion-discipline.md`, `.tiny-swarm/evidence/` | local governance hardening |
| `audit-evidence-manager` | Audit and quality | Senior Documentation Engineer | `documentation/audit/` | #121 |
| `qms-light-governance-expert` | Audit and quality | Senior Tester | `documentation/qms/`, `QUALITY.md`, `AGENTS.md` | #122 |
| `traceability-engineer` | Audit and quality | Senior Requirement Engineer | `documentation/traceability/` | #124 |
| `isms-light-security-governance-expert` | Security | Security Owner | `documentation/security/` | #123 |
| `owasp-asvs-local-infrastructure-expert` | Security | Security Owner | `documentation/security/owasp-asvs-mapping.md`, `documentation/security/admin-surface-rbac.md`, `documentation/security/service-access-threat-model.md` | #126 |
| `supply-chain-security-expert` | Security | Security Owner | `documentation/security/supply-chain-security.md`, `documentation/security/sbom-policy.md`, `documentation/security/dependency-scan-policy.md`, `documentation/security/container-image-scan-policy.md`, `tools/security_gate.py` | #127 |
| `live-evidence-validation-expert` | Operations, CI, and release governance | Senior DevOps Engineer | `documentation/evidence/`, `documentation/system/live-operation-surfaces.adoc` | #125 |
| `branch-ci-governance-expert` | Operations, CI, and release governance | Senior DevOps Engineer | `documentation/governance/branch-protection.md`, `documentation/governance/ci-quality-gates.md`, `documentation/governance/pr-review-policy.md` | #128 |
| `release-baseline-governance-expert` | Operations, CI, and release governance | Root Architect | `documentation/release/`, `pyproject.toml`, `README.md` | #130 |
| `documentation-audience-architect` | Documentation governance | Senior Documentation Engineer | `documentation/manuals/`, `README.md`, `documentation/README.adoc`, `documentation/user_guide/user-handbook.adoc` | #129 |

Conflict decision: no equivalent project skill with the same narrow ownership
was found in the current registry. Existing broader skills remain escalation and
collaboration partners.

Routing validation: workflow authoring uses Requirement, System Architecture,
Python Automation, and Test as mandatory review roles. Console/status UI review
is conditional on terminal UX impact. Browser React, forensic analysis storage,
Joern, and Code Property Graph routing remain outside the project unless a later
explicit workflow changes the root project scope.

## Verification

Refresh this registry after `.agents/**`, `.codex/**`, `AGENTS.md`,
`QUALITY.md`, `documentation/workflow/**`, `documentation/process/skills/audit/**` or
process documentation changes.
