# RC1-R04 Test Results

Candidate: `c921e69533450fba86d908e2990c106bef87769a`.
PR #335 head: `8eb5db338aed9965a49ed6879198fd1053b97dcc`.
Both have whole Git tree `a14e635dd22cb02fc063a319d73383f676572bca`.

| Scope | Run | Result |
|---|---|---|
| PR Python quality | [34725658814](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34725658814) | PASS |
| PR Python 3.12/3.13 compatibility | [34725658760](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34725658760) | PASS |
| PR waited Sonar gate, actual analysis 8eb5db33 | [34725802800](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34725802800) | EXTERNAL_GATE_VERIFIED |
| Main Python quality | [34726339297](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34726339297) | PASS |
| Main Python 3.12/3.13 compatibility | [34726339319](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34726339319) | PASS |
| Main waited Sonar gate, actual analysis c921e695 | [34726472444](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/actions/runs/34726472444) | EXTERNAL_GATE_VERIFIED |

The PR Sonar workflow metadata SHA is 2183006e; its verified checkout and scanner
SCM revision are 8eb5db33. It is not counted as a scan of 2183006e. The main scan
actually checked out and analyzed c921e695 and separately waited for PASSED.

Local source validation retained: 15 focused TLS tests; final product full gate
on Python 3.12.14 passed 2,066 tests (18 intentional skips), 18 architecture tests,
three import contracts, lint and mypy over 674 source files. Live/browser checks
are separate. This documentation-only follow-up runs git diff --check and the
verification-policy gate; the full runtime suite is not rerun because source,
tests, configuration, dependencies and workflows are unchanged (QUALITY.md).

Fresh security runs executed 2026-09-12 23:42–23:44 UTC on the archived 8eb5db33
source, whose complete tree equals c921e695:

- Canonical security_gate.py dependencies: exit 0; 13 locked runtime packages,
  no known vulnerabilities reported (pip-audit 2.10.1).
- Canonical security_gate.py sbom: exit 0; CycloneDX 1.4, 13 components, no
  reported vulnerability entries.
- Pinned Trivy 0.74.0 config --severity HIGH,CRITICAL --exit-code 1: exit 0;
  three Dockerfiles, 60 successful checks, zero failing selected-severity checks.
  The initial container launch exited 125 before scanning; the explicitly
  recorded networking correction and successful retry preserve that distinction.

[Provenance and allowlisted log lines](candidate-c921e695/provenance.json),
[scan](candidate-c921e695/container-config.json),
[SBOM](candidate-c921e695/runtime-dependencies.cdx.json), and
[SHA-256 manifest](candidate-c921e695/sha256.json) are retained in Git.
