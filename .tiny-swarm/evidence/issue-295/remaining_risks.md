# Remaining risks

No open live acceptance requirement remains for the tested code candidate
`d254b76980a344a67295d8395e61002bf0730b0c`; independent completion review returned PASS (completion_audit.md).

- Original WSL restart command failures retain unknown exact causes; observed
  task replacement, constrained spec checks and fresh authentication establish
  recovery. The individual Pulsar update timestamp was not retained; its bounded
  sequence and task-history predecessor are explicitly documented.
- PreviousSpec validates each last update, not all earlier repeated mutations.
  No claim is made that a failed raw-spec comparator itself passed.
- Service restart acceptance does not qualify whole-host reboot, database
  restart, power loss, all of #298/#299, or a blanket RC1 release.
- #296 provenance/override transition retains its own revision and evidence;
  this run does not imply Vault-only provenance from bootstrap source labels.
- Native Python 3.14 reflects the existing host; project compatibility remains
  Python 3.12, with external 3.12/3.13 checks separately passing.
- Browser sessions are closed; private value-free JSON is retained for audit.
  No credential rotation/reset, volume deletion or environment teardown occurred.
- Candidate CI/Sonar passed. Latest publication checks must be verified on the PR after push;
  the PR is not automatically merged.
