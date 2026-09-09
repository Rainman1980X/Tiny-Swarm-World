# Implementation Summary: #285 / CRED-07

CRED-07 exposed and repaired four live-path issues while proving the standard
internal-test path on WSL2:

- Portainer now receives its admin credential through an external Docker secret
  and deploy-time `--admin-password-file` bootstrap. The prerequisite decision
  remains in the stack strategy layer; the runtime does not branch on a stack
  name.
- Secret inventory treats `password_source` as source metadata, not unmanaged
  secret material.
- SonarQube's current password policy is represented in the immutable catalog
  (lowercase plus special character) and the deterministic value is derived
  accordingly.
- The installer now uses `TSW_LIVE_EVIDENCE_ROOT` (or the WSL-native XDG state
  default) for its own reset/setup evidence and creates private `0700`
  root/host/run directories. It no longer writes the outer live evidence to a
  Windows-mounted checkout when a protected root is configured.

The protected WSL2 run at
`/home/micro/.local/state/tiny-swarm-world/evidence/cred07-wsl2-secure-20260903/wsl2/20260903T072101Z`
completed reset and setup with exit 0. It used the deterministic catalog
source labels, completed all configured phases, and left no raw credentials in
the redacted evidence or installer output.

Separate WSL2 reconcile and Portainer restart checks also passed. Native Linux,
custom/Infisical override, credential-drift comparison, and browser acceptance
remain open because their required target/input contract was not available.

The 2026-09-09 local continuation qualifies the evidence root before browser
access in both Classic suites. They share the live-root override, legacy
Classic fallback and Linux-native state default; post-install run directories
are private as well. Regression tests exercise routing, retained historical
files, insecure permissions and Windows-filesystem rejection without live
services. Jenkins historical HTTP 200 and post-restart readiness are explicitly
separated from the still-missing authenticated-identity evidence.
