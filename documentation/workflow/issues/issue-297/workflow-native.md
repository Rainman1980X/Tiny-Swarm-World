# RC1-E02: Native Linux update evidence

Issue: #297; also reconciles #298. Selected by `../../workflow.index.md`.
Common governance, consent, redaction, quality and completion rules are those
in `workflow.md`. This slice executes after the WSL repair/validation slice so
both hosts use the same repaired candidate. Native live operations are serial.

```yaml
slice_id: RC1-E02
profile: FULL_PATH
owner: senior-devops
secondary_reviewers: [senior-system-architect, senior-tester, issue-completion-auditor]
affected_files: [.tiny-swarm/evidence/issue-297/, .tiny-swarm/evidence/issue-298/]
affected_modules: [native-Linux lifecycle, canonical update]
affected_contracts: [candidate provenance, persisted data, image convergence]
dependencies: [RC1-E00, RC1-E01]
parallel_group: rc1-evidence-serial
file_locks: [issue-297-evidence, issue-298-evidence]
contract_locks: [native-test-target, candidate-provenance, redaction]
architecture_locks: [linux-wsl2-only, incus-lxc-provider, hexagonal-boundaries]
quality_gates:
  targeted: [git diff --check]
  required: [python3 tools/quality_gate.py quality]
stop_conditions: [unqualified native target, failed preflight, failed recovery]
```

Qualify native kernel, private configuration/evidence storage, target ownership
and resources before mutation. Observe distinct source/target image identities,
seed harmless persistent records, and capture service/node identities. Apply,
repeat and recover the canonical update, waiting for actual task convergence.
After each phase verify the records, unrelated configuration, private credential
equality and the existing authenticated browser/API acceptance suite without
skips. Record exact SHA, durations, exit codes and redacted artifacts. Shut down
the native VM when native work finishes.

Historical native reboot evidence remains historical. Acceptance requires the
current candidate's actual native results and independent review, with all six
issue evidence files reconciled before claiming completion.
