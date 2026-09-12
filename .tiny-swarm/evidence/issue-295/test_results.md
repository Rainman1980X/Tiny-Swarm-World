# Verification results

Local focused: 56 tests passed via
`PYTHONPATH=src python3 -m unittest tests.e2e.classic.test_authenticated_acceptance_runner tests.e2e.classic.test_authenticated_service_contract tests.e2e.classic.test_browser_e2e_contract`.

First full gate reached typecheck and failed a tuple annotation in a new mock
fixture. Corrected without weakening tests. Final `python3 tools/quality_gate.py quality`
passed all six stages, exit 0: 1972 tests (18 skipped), 18 architecture tests,
three import contracts, lint, verification policy and typecheck across 655 files.
Skipped local tests are not live execution. `git diff --check` passed.

Diagnostic WSL2 runs discovered and repaired Nexus modal interaction, distinct
Portainer/Infisical/Pulsar Manager rejection messages, and explicit Portainer
HTTP 422 rejection schema. Diagnostic reports retain dirty_checkout=true and
LIVE_PARTIAL; they do not establish final-candidate success.

Native existing VM reachable and trusted key verified; isolated Selenium
installation and actual headless Firefox startup succeeded. Service acceptance
and restart evidence pending. No native browser success inferred from startup.

## Three Amigos loop 2 — SPA DOM replacement

Candidate `e5994d3aa9bc0a81bb3a47b56794425f37293743` native baseline
`20260912T082939927270Z`: all nine browser routes and seven protected API
checks passed, including invalid rejection; LIVE_VERIFIED for that candidate.
WSL baseline `20260912T082919110392Z`: Sonar browser returned
StaleElementReferenceException; all API probes passed. That run remains
LIVE_PARTIAL. The retained exception class does not establish the exact throw
site. Password-form observation had an uncovered stale-DOM failure path.

QA approved reacquiring DOM elements on bounded stale-only retries, with
exhaustion raising instead of implying absence. Credentials are not resubmitted.
Regressions cover stale-to-visible, stale-to-absent, exhaustion and unrelated
exception propagation. Focused browser contract: 27 tests PASS. Full local gate: all six stages PASS,
exit 0; 1974 tests (18 local skips), 18 architecture tests, three contracts and
655 typechecked files. Corrected-candidate reruns follow; no historical run is
relabeled.
