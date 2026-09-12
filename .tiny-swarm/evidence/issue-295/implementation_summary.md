# CRED-08 implementation

Status: INCOMPLETE pending final-candidate both-host execution and independent audit.

Reuse canonical Classic effective-model routes and credential inputs. Login tests
now submit credentials, reject one invalid attempt, create a fresh Firefox
session, wait for the form to disappear and verify authenticated session access
for Jenkins, SonarQube and Nexus. Nexus uses its actual modal login controls.
Public navigation words alone cannot bypass submission. API probes use fresh
sessions, bounded invalid/valid attempts, explicit rejection schemas, TLS trust
and protected identity/read operations. No credentials are returned in evidence.

Mixed skipped/passed or empty inventories cannot pass. WebDriver startup failures
are recorded; arbitrary exception text is excluded. Each runner invocation has a
private unique phase directory and records the actual revision and dirty state.
A dirty checkout cannot yield LIVE_VERIFIED. The phase runner performs no restart;
external task-replacement evidence must accompany post-restart authentication.

Three Amigos loop: Requirement, Architecture, Developer and QA reviews identified
and corrected anonymous landing bypass, incomplete aggregation, service-specific
form/rejection semantics, Sonar isLoggedIn validation, Nexus protected-operation
wording, source qualification and missing runner regressions. No production
architecture change. API worker used isolated /tmp/tsw-c08-auth; root consolidated
two explicit files, retained integration and runtime ownership.
