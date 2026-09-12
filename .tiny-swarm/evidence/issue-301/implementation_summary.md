# RC1-R05 Implementation Summary

Status: HOSTED_LIFECYCLE_AND_FAILURE_DRILL_VERIFIED.

The existing Nightly workflow keeps scheduled/manual dispatch, protected
environment, target-owner checks, Linux/Incus/Docker qualification, bounded
timeouts and concurrency protection. It now invokes the canonical runner with
an explicit `--test-only` profile for the disposable test target, so the
credential-rotation reference and its GitHub variable are not required there.
The runner payload records `disposable_test` and
`not_applicable_test_only` without persisting a reference value. Unmarked
protected/live invocations still require a valid rotation reference. The R03
lifecycle chain is consumed without duplicating installer logic in YAML.

The repository now has an online Linux/x64 runner with the workflow's
`tsw-classic` label and verified Incus/Docker capabilities. A clean local
test-only installation now passes on the Incus/LXC target, including Infisical
secret synchronization and endpoint verification. Hosted run 34719043422
completed the full disposable Fresh → Reconcile → Update → Recovery lifecycle,
including four passing 37-test acceptance operations and redacted artifact
upload. Controlled blocked dispatch 34720172182 also failed closed in the
qualification job before the live chain could mutate the target.
