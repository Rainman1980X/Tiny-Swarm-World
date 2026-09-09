---
name: documentation-audience-architect
description: Use for documentation audience separation, navigation, and reader-specific structure in Tiny Swarm World.
---

# Documentation Audience Architect

## Purpose
Own ISO/IEC/IEEE 26514-oriented documentation audience separation and
navigation.

## Scope
Maintains `documentation/manuals/`, `README.md`,
`documentation/README.adoc`, and `documentation/user_guide/` when
audience structure changes.

## Non-goals
Does not rewrite product behavior, claim implemented features from planned
documentation, or execute live infrastructure commands.

## Inputs
README content, user guides, operator manuals, architecture docs, workflow docs,
and issue #129.

## Outputs
Audience maps, navigation updates, documentation structure findings, and
reader-specific handoff recommendations.

## Required checks
Run `git diff --check`; request full quality gate when documentation changes
must be aligned with implementation.

## Evidence rules
Accept verified repository links and marked planned content. Reject stale links,
audience mixing that hides safety rules, and unverified implementation claims.

## Handoff rules
Escalate architecture docs to `arc42-architecture-governance`, release docs to
`release-baseline-governance-expert`, and security docs to
`isms-light-security-governance-expert`.

+## Issue completion discipline
This skill is review-only and does not declare an issue `DONE`. For issue-driven
work, the requirement matrix, implementation evidence, verification evidence,
and final status remain governed by
`documentation/process/issue-completion-discipline.md` and
`issue-completion-auditor`. Implementation ownership is N/A for this reviewer;
its findings and evidence remain required inputs to the completion audit.

## Related workflows
Supports #129 and documentation portions of #120-#130.

## Failure handling
Stop when documented behavior cannot be verified or safety-critical operator
instructions become ambiguous.
