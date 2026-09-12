# RC1-R01 Implementation Summary

Status: `INCOMPLETE` — local implementation and verification are complete;
qualified live host and protected-runner evidence remain open.

The canonical `platform update` workflow now validates one supported
stack/service image transition, supports read-only preview, requires the
existing live-consent boundary for mutation, persists private rollback
metadata, and exposes `--recover` for the last recorded transition. It
reuses the existing deployment port and limits the deployment plan to the
selected stack.

Unsupported services, source-image drift, missing rollback state and missing
consent fail closed before downstream mutation. The Classic acceptance runner
and Nightly workflow consume the same canonical update command contract.
