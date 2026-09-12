import unittest
from tests.support.async_helpers import async_checkpoint

from tiny_swarm_world.application.ports.method_trace import (
    MethodTraceEvent,
    PortMethodTrace,
)
from tiny_swarm_world.application.ports.progress import (
    PortWorkflowProgress,
    WorkflowProgressEvent,
)
from tiny_swarm_world.application.services.platform import (
    DESTROY_TINY_SWARM_PLATFORM_CONFIRMATION,
    PLATFORM_WORKFLOW_TAXONOMY,
    RESET_TINY_SWARM_PLATFORM_CONFIRMATION,
    PlatformDestroyWorkflow,
    PlatformExposeWorkflow,
    PlatformInitWorkflow,
    PlatformRepairLxcProxyDriftWorkflow,
    PlatformReconcileWorkflow,
    PlatformResetWorkflow,
    PlatformVerifyWorkflow,
    PlatformWorkflowKind,
    PlatformWorkflowResult,
    PlatformWorkflowStatus,
)
from tiny_swarm_world.domain.inventory import VerificationResult, VerificationStatus
from tiny_swarm_world.domain.preflight import (
    PreflightCategory,
    PreflightCheck,
    PreflightResult,
    PreflightSeverity,
    PreflightStatus,
)


class TestPlatformWorkflowTaxonomy(unittest.TestCase):
    def test_workflow_semantics_are_explicit(self):
        expected = {
            PlatformWorkflowKind.INIT: (True, False, False),
            PlatformWorkflowKind.RECONCILE: (True, False, False),
            PlatformWorkflowKind.UPDATE: (True, False, False),
            PlatformWorkflowKind.EXPOSE: (True, False, False),
            PlatformWorkflowKind.REPAIR_LXC_PROXY_DRIFT: (True, False, False),
            PlatformWorkflowKind.RESET: (True, True, True),
            PlatformWorkflowKind.DESTROY: (True, True, True),
            PlatformWorkflowKind.VERIFY: (False, False, False),
        }

        self.assertEqual(set(expected), set(PLATFORM_WORKFLOW_TAXONOMY))
        for kind, (mutating, destructive, requires_confirmation) in expected.items():
            semantics = PLATFORM_WORKFLOW_TAXONOMY[kind]
            self.assertEqual(mutating, semantics.mutating)
            self.assertEqual(destructive, semantics.destructive)
            self.assertEqual(requires_confirmation, semantics.requires_confirmation)

    def test_workflow_result_outcome_distinguishes_noop_converged_and_blocked(self):
        no_op = PlatformWorkflowResult.completed(
            PLATFORM_WORKFLOW_TAXONOMY[PlatformWorkflowKind.RECONCILE],
            executed=True,
            verification_results=(
                VerificationResult(
                    target_id="platform:node:swarm-manager",
                    status=VerificationStatus.VERIFIED,
                    message="Node already matches configured state.",
                    evidence={"phase": "verify", "classification": "already_present"},
                ),
            ),
        )
        converged = PlatformWorkflowResult.completed(
            PLATFORM_WORKFLOW_TAXONOMY[PlatformWorkflowKind.RECONCILE],
            executed=True,
            verification_results=(
                VerificationResult(
                    target_id="platform:node:swarm-manager",
                    status=VerificationStatus.VERIFIED,
                    message="Node was started and verified.",
                    evidence={
                        "phase": "apply",
                        "classification": "started",
                        "applied": "true",
                    },
                ),
            ),
        )
        blocked = PlatformWorkflowResult.blocked(
            PLATFORM_WORKFLOW_TAXONOMY[PlatformWorkflowKind.RECONCILE],
            "reconcile step blocked.",
            (
                VerificationResult(
                    target_id="platform:node:swarm-manager",
                    status=VerificationStatus.BLOCKED,
                    message="Live mutation is required.",
                    evidence={"phase": "pre_apply"},
                ),
            ),
        )

        self.assertEqual(no_op.to_dict()["outcome"]["mutation"]["result"], "no_op")
        self.assertEqual(no_op.to_dict()["outcome"]["verification"], "verified")
        self.assertEqual(converged.to_dict()["outcome"]["mutation"]["result"], "converged")
        self.assertEqual(converged.to_dict()["outcome"]["verification"], "verified")
        self.assertEqual(blocked.to_dict()["outcome"]["mutation"]["result"], "blocked")
        self.assertEqual(blocked.to_dict()["outcome"]["verification"], "blocked")


class TestPlatformWorkflows(unittest.IsolatedAsyncioTestCase):
    async def test_init_reconcile_expose_and_repair_run_configured_safe_steps(self):
        init_step = _RecordingAction("init")
        reconcile_step = _RecordingAction("reconcile")
        expose_step = _RecordingAction("expose")
        repair_step = _RecordingAction("repair")

        init_result = await PlatformInitWorkflow([init_step]).run()
        reconcile_result = await PlatformReconcileWorkflow([reconcile_step]).run()
        expose_result = await PlatformExposeWorkflow([expose_step]).run()
        repair_result = await PlatformRepairLxcProxyDriftWorkflow([repair_step]).run()

        self.assertEqual(["init"], init_step.calls)
        self.assertEqual(["reconcile"], reconcile_step.calls)
        self.assertEqual(expose_step.calls, ["expose"])
        self.assertEqual(repair_step.calls, ["repair"])
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, init_result.status)
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, reconcile_result.status)
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, expose_result.status)
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, repair_result.status)
        self.assertFalse(PlatformInitWorkflow.semantics.destructive)
        self.assertFalse(PlatformReconcileWorkflow.semantics.destructive)
        self.assertFalse(PlatformExposeWorkflow.semantics.destructive)
        self.assertFalse(PlatformRepairLxcProxyDriftWorkflow.semantics.destructive)
        self.assertEqual(1, len(init_step.verifications))
        self.assertEqual(1, len(reconcile_step.verifications))
        self.assertEqual(len(expose_step.verifications), 1)
        self.assertEqual(len(repair_step.verifications), 1)
        self.assertEqual(
            ("init",),
            tuple(item.target_id for item in init_result.verification_results),
        )
        self.assertEqual(
            ("reconcile",),
            tuple(item.target_id for item in reconcile_result.verification_results),
        )
        self.assertEqual(
            tuple(item.target_id for item in expose_result.verification_results),
            ("expose",),
        )
        self.assertEqual(
            tuple(item.target_id for item in repair_result.verification_results),
            ("repair",),
        )

    async def test_init_reports_method_trace_for_completion(self):
        trace = _RecordingMethodTrace()
        result = await PlatformInitWorkflow(
            [_RecordingAction("init")],
            method_trace=trace,
            trace_correlation_id="trace-platform",
        ).run()

        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertEqual(
            trace.summary(),
            [
                ("PlatformInitWorkflow", "run", "entered", "pending", None),
                ("PlatformInitWorkflow", "run", "returned", "completed", None),
            ],
        )
        self.assertEqual({event.correlation_id for event in trace.events}, {"trace-platform"})

    async def test_init_reports_safe_failure_trace_when_apply_exception_is_converted(self):
        trace = _RecordingMethodTrace()
        result = await PlatformInitWorkflow(
            [_FailingApplyAction("init")],
            method_trace=trace,
            trace_correlation_id="trace-platform",
        ).run()

        self.assertEqual(PlatformWorkflowStatus.FAILED_TO_APPLY, result.status)
        self.assertEqual(
            trace.summary(),
            [
                ("PlatformInitWorkflow", "run", "entered", "pending", None),
                (
                    "PlatformInitWorkflow",
                    "run",
                    "returned",
                    "failed_to_apply",
                    None,
                ),
            ],
        )

    async def test_verify_is_non_mutating_and_runs_configured_safe_steps(self):
        verify_step = _RecordingAction("verify")

        result = await PlatformVerifyWorkflow([verify_step]).run()

        self.assertEqual(["verify"], verify_step.calls)
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertFalse(PlatformVerifyWorkflow.semantics.mutating)
        self.assertFalse(PlatformVerifyWorkflow.semantics.destructive)

    async def test_verify_reports_failed_preflight_as_failed_to_verify(self):
        verify_step = _PreflightAction(
            PreflightResult(
                (
                    PreflightCheck(
                        check_id="HOST",
                        category=PreflightCategory.HOST,
                        status=PreflightStatus.FAILED,
                        severity=PreflightSeverity.MANDATORY,
                        message="Host is not ready.",
                        remediation="Run from Linux or WSL.",
                    ),
                )
            )
        )

        result = await PlatformVerifyWorkflow([verify_step]).run()

        self.assertEqual(["preflight"], verify_step.calls)
        self.assertEqual(PlatformWorkflowStatus.FAILED_TO_VERIFY, result.status)
        self.assertTrue(result.executed)
        self.assertEqual(
            VerificationStatus.FAILED_TO_VERIFY,
            result.verification_results[0].status,
        )
        self.assertEqual(
            {"phase": "verify", "failed_check_count": "1"},
            dict(result.verification_results[0].evidence),
        )

    async def test_verify_retries_transient_failed_preflight(self):
        verify_step = _PreflightSequenceAction(
            (
                PreflightResult(
                    (
                        PreflightCheck(
                            check_id="PORT-12000",
                            category=PreflightCategory.PORT,
                            status=PreflightStatus.FAILED,
                            severity=PreflightSeverity.MANDATORY,
                            message="Port 12000 for SonarQube is occupied.",
                            remediation="Wait for expected service readiness.",
                        ),
                    )
                ),
                PreflightResult(()),
            )
        )

        result = await PlatformVerifyWorkflow(
            [verify_step],
            verify_retry_attempts=2,
            verify_retry_delay_seconds=0,
        ).run()

        self.assertEqual(verify_step.calls, ["preflight", "preflight"])
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertEqual(VerificationStatus.VERIFIED, result.verification_results[0].status)
        self.assertEqual(result.verification_results[0].evidence["verify_attempt"], "2")

    async def test_init_pre_apply_guard_blocks_before_steps(self):
        progress = _RecordingProgress()
        guard = _PreflightAction(
            PreflightResult(
                (
                    PreflightCheck(
                        check_id="PROVIDER-LXC-DAEMON",
                        category=PreflightCategory.RUNTIME,
                        status=PreflightStatus.FAILED,
                        severity=PreflightSeverity.MANDATORY,
                        message="LXC provider daemon is not reachable.",
                        remediation="Repair LXD/Incus runtime access.",
                    ),
                )
            )
        )
        step = _RecordingAction("init")

        result = await PlatformInitWorkflow(
            [step],
            pre_apply_guard=guard,
            progress=progress,
        ).run()

        self.assertEqual(guard.calls, ["preflight"])
        self.assertEqual(step.calls, [])
        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertFalse(result.executed)
        self.assertEqual(result.verification_results[0].target_id, "platform:init:preflight")
        self.assertEqual(VerificationStatus.BLOCKED, result.verification_results[0].status)
        self.assertEqual(result.verification_results[0].evidence["runtime_failure_count"], "1")
        self.assertEqual(
            progress.summary(),
            [
                ("pre_apply", "pre-apply guard", "started", "pending"),
                ("pre_apply", "pre-apply guard", "blocked", "blocked"),
                ("platform", "workflow stopped", "blocked", "blocked"),
            ],
        )

    async def test_init_provider_guard_blocks_before_any_platform_step(self):
        progress = _RecordingProgress()
        guard = _ProviderGuardAction(
            VerificationResult(
                target_id="platform:node-provider:lxc_native",
                status=VerificationStatus.BLOCKED,
                message="Provider selection blocked platform mutation.",
                evidence={
                    "phase": "pre_apply",
                    "reason": "provider_selection_blocked",
                    "requested_provider": "lxc_native",
                    "selected_provider": "lxc_native",
                    "selection_status": "blocked",
                    "backend_status": "missing",
                    "backend_candidate_count": "0",
                    "remediation_count": "1",
                },
            )
        )
        step = _RecordingAction("init")

        result = await PlatformInitWorkflow(
            [step],
            pre_apply_guard=guard,
            progress=progress,
        ).run()

        self.assertEqual(guard.calls, ["provider"])
        self.assertEqual(step.calls, [])
        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertFalse(result.executed)
        self.assertEqual(result.verification_results[0].target_id, "platform:node-provider:lxc_native")
        self.assertEqual(result.verification_results[0].evidence["reason"], "provider_selection_blocked")
        self.assertEqual(result.verification_results[0].evidence["requested_provider"], "lxc_native")
        self.assertNotIn("multipass_legacy", repr(result.to_dict()))
        self.assertEqual(
            progress.summary(),
            [
                ("pre_apply", "pre-apply guard", "started", "pending"),
                ("pre_apply", "pre-apply guard", "blocked", "blocked"),
                ("platform", "workflow stopped", "blocked", "blocked"),
            ],
        )

    async def test_init_pre_apply_guard_passes_before_steps(self):
        progress = _RecordingProgress()
        guard = _PreflightAction(PreflightResult(()))
        step = _RecordingAction("init")

        result = await PlatformInitWorkflow(
            [step],
            pre_apply_guard=guard,
            progress=progress,
        ).run()

        self.assertEqual(guard.calls, ["preflight"])
        self.assertEqual(step.calls, ["init"])
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertEqual(
            tuple(item.target_id for item in result.verification_results),
            ("platform:init:preflight", "init"),
        )
        self.assertEqual(
            tuple(item.status for item in result.verification_results),
            (VerificationStatus.VERIFIED, VerificationStatus.VERIFIED),
        )
        self.assertEqual(
            progress.summary(),
            [
                ("pre_apply", "pre-apply guard", "started", "pending"),
                ("pre_apply", "pre-apply guard", "verified", "verified"),
                ("apply", "apply", "started", "pending"),
                ("apply", "apply", "completed", "completed"),
                ("verify", "verify", "started", "pending"),
                ("verify", "verify", "verified", "verified"),
                ("platform", "workflow completed", "completed", "completed"),
            ],
        )

    async def test_reset_refuses_missing_or_wrong_confirmation_before_running_steps(self):
        destructive_step = _ForbiddenAction()
        workflow = PlatformResetWorkflow([destructive_step])

        missing_result = await workflow.run()
        wrong_result = await workflow.run("wrong")

        self.assertEqual(PlatformWorkflowStatus.REFUSED, missing_result.status)
        self.assertEqual(PlatformWorkflowStatus.REFUSED, wrong_result.status)
        self.assertFalse(missing_result.executed)
        self.assertFalse(wrong_result.executed)

    async def test_destroy_refuses_missing_or_wrong_confirmation_before_running_steps(self):
        destructive_step = _ForbiddenAction()
        workflow = PlatformDestroyWorkflow([destructive_step])

        missing_result = await workflow.run()
        wrong_result = await workflow.run("wrong")

        self.assertEqual(PlatformWorkflowStatus.REFUSED, missing_result.status)
        self.assertEqual(PlatformWorkflowStatus.REFUSED, wrong_result.status)
        self.assertFalse(missing_result.executed)
        self.assertFalse(wrong_result.executed)

    async def test_reset_and_destroy_confirmations_are_not_cross_accepted(self):
        reset_result = await PlatformResetWorkflow([_ForbiddenAction()]).run(
            DESTROY_TINY_SWARM_PLATFORM_CONFIRMATION
        )
        destroy_result = await PlatformDestroyWorkflow([_ForbiddenAction()]).run(
            RESET_TINY_SWARM_PLATFORM_CONFIRMATION
        )

        self.assertEqual(PlatformWorkflowStatus.REFUSED, reset_result.status)
        self.assertEqual(PlatformWorkflowStatus.REFUSED, destroy_result.status)
        self.assertFalse(reset_result.executed)
        self.assertFalse(destroy_result.executed)

    async def test_reset_runs_steps_only_after_exact_confirmation(self):
        destructive_step = _RecordingAction("reset")

        result = await PlatformResetWorkflow([destructive_step]).run(
            RESET_TINY_SWARM_PLATFORM_CONFIRMATION
        )

        self.assertEqual(["reset"], destructive_step.calls)
        self.assertEqual(destructive_step.verifications, ["reset"])
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertEqual(
            tuple(item.target_id for item in result.verification_results),
            ("reset",),
        )

    async def test_destroy_runs_steps_only_after_exact_confirmation(self):
        destructive_step = _RecordingAction("destroy")

        result = await PlatformDestroyWorkflow([destructive_step]).run(
            DESTROY_TINY_SWARM_PLATFORM_CONFIRMATION
        )

        self.assertEqual(["destroy"], destructive_step.calls)
        self.assertEqual(destructive_step.verifications, ["destroy"])
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertEqual(
            tuple(item.target_id for item in result.verification_results),
            ("destroy",),
        )

    async def test_destructive_workflows_run_all_steps_and_verifications_after_exact_confirmation(self):
        cases = (
            (
                PlatformResetWorkflow,
                RESET_TINY_SWARM_PLATFORM_CONFIRMATION,
                ("reset-one", "reset-two"),
            ),
            (
                PlatformDestroyWorkflow,
                DESTROY_TINY_SWARM_PLATFORM_CONFIRMATION,
                ("destroy-one", "destroy-two"),
            ),
        )

        for workflow_class, confirmation, names in cases:
            with self.subTest(workflow=workflow_class.__name__):
                steps = tuple(_RecordingAction(name) for name in names)

                result = await workflow_class(steps).run(confirmation)

                self.assertTrue(result.executed)
                self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
                self.assertEqual(names, tuple(call for step in steps for call in step.calls))
                self.assertEqual(
                    names,
                    tuple(verification for step in steps for verification in step.verifications),
                )
                self.assertEqual(
                    names,
                    tuple(item.target_id for item in result.verification_results),
                )
                self.assertEqual(
                    tuple(item.status for item in result.verification_results),
                    (VerificationStatus.VERIFIED, VerificationStatus.VERIFIED),
                )

    async def test_confirmed_reset_without_steps_is_blocked_until_policy_exists(self):
        result = await PlatformResetWorkflow().run(RESET_TINY_SWARM_PLATFORM_CONFIRMATION)

        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertFalse(result.executed)

    async def test_confirmed_destroy_without_steps_is_blocked_until_policy_exists(self):
        result = await PlatformDestroyWorkflow().run(DESTROY_TINY_SWARM_PLATFORM_CONFIRMATION)

        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertFalse(result.executed)

    async def test_mutating_workflow_without_verify_spec_is_blocked_before_apply(self):
        apply_only_step = _ApplyOnlyAction("apply-only")
        later_step = _RecordingAction("later")

        result = await PlatformInitWorkflow([apply_only_step, later_step]).run()

        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertEqual([], apply_only_step.calls)
        self.assertEqual([], later_step.calls)
        self.assertEqual(VerificationStatus.BLOCKED, result.verification_results[0].status)
        self.assertIn(
            "command-backed verification is not configured",
            result.message,
        )
        self.assertEqual(
            "command-backed verification is not configured",
            result.verification_results[0].evidence["reason"],
        )

    async def test_pre_apply_verification_blocks_before_apply_and_later_steps(self):
        blocked_step = _PreApplyAction(
            "pre-apply-blocked",
            VerificationResult(
                target_id="pre-apply-blocked",
                status=VerificationStatus.BLOCKED,
                message="Command-backed verification is not configured.",
                evidence={
                    "phase": "pre_apply",
                    "reason": "command_backed_verification_missing",
                },
            ),
        )
        later_step = _RecordingAction("later")

        result = await PlatformInitWorkflow([blocked_step, later_step]).run()

        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertEqual([], blocked_step.calls)
        self.assertEqual([], blocked_step.verifications)
        self.assertEqual([], later_step.calls)
        self.assertEqual(VerificationStatus.BLOCKED, result.verification_results[0].status)
        self.assertEqual(
            "command_backed_verification_missing",
            result.verification_results[0].evidence["reason"],
        )

    async def test_destructive_workflows_block_on_pre_apply_verification_before_apply(self):
        cases = (
            (PlatformResetWorkflow, RESET_TINY_SWARM_PLATFORM_CONFIRMATION),
            (PlatformDestroyWorkflow, DESTROY_TINY_SWARM_PLATFORM_CONFIRMATION),
        )

        for workflow_class, confirmation in cases:
            with self.subTest(workflow=workflow_class.__name__):
                blocked_step = _PreApplyAction(
                    "destructive-pre-apply-blocked",
                    VerificationResult(
                        target_id="destructive-pre-apply-blocked",
                        status=VerificationStatus.BLOCKED,
                        message="Command-backed verification is not configured.",
                        evidence={
                            "phase": "pre_apply",
                            "reason": "command_backed_verification_missing",
                        },
                    ),
                )
                later_step = _RecordingAction("later")

                result = await workflow_class([blocked_step, later_step]).run(confirmation)

                self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
                self.assertFalse(result.executed)
                self.assertEqual(blocked_step.calls, [])
                self.assertEqual(blocked_step.verifications, [])
                self.assertEqual(later_step.calls, [])
                self.assertEqual(VerificationStatus.BLOCKED, result.verification_results[0].status)
                self.assertEqual(result.verification_results[0].evidence["phase"], "pre_apply")

    async def test_pre_apply_verified_step_blocks_after_apply_without_observed_verification(self):
        step = _PreApplyAction(
            "pre-apply-verified",
            VerificationResult(
                target_id="pre-apply-verified",
                status=VerificationStatus.VERIFIED,
                message="Command-backed verification contract is configured.",
                evidence={"phase": "pre_apply"},
            ),
        )

        result = await PlatformInitWorkflow([step]).run()

        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertEqual(["pre-apply-verified"], step.calls)
        self.assertEqual(
            ("pre_apply", "verify"),
            tuple(item.evidence["phase"] for item in result.verification_results),
        )
        self.assertEqual("Verification evidence is missing.", result.verification_results[1].message)

    async def test_verification_result_step_records_provider_lifecycle_result(self):
        progress = _RecordingProgress()
        step = _VerificationResultAction(
            VerificationResult(
                target_id="platform:node:swarm-manager",
                status=VerificationStatus.VERIFIED,
                message="Provider lifecycle reached the desired state.",
                evidence={
                    "phase": "verify",
                    "classification": "verified",
                    "provider": "lxc_native",
                    "node": "swarm-manager",
                    "backend": "incus",
                },
            )
        )

        result = await PlatformInitWorkflow([step], progress=progress).run()

        self.assertEqual(step.calls, ["platform:node:swarm-manager"])
        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertEqual(result.verification_results[0].target_id, "platform:node:swarm-manager")
        self.assertEqual(VerificationStatus.VERIFIED, result.verification_results[0].status)
        self.assertEqual(
            progress.summary(),
            [
                ("apply", "apply", "started", "pending"),
                ("apply", "apply", "completed", "completed"),
                ("verify", "direct verification", "verified", "verified"),
                ("platform", "workflow completed", "completed", "completed"),
            ],
        )

    async def test_blocked_verification_result_step_stops_before_later_steps(self):
        progress = _RecordingProgress()
        blocked_step = _VerificationResultAction(
            VerificationResult(
                target_id="platform:node:swarm-manager",
                status=VerificationStatus.BLOCKED,
                message="Provider lifecycle is blocked before mutation.",
                evidence={
                    "phase": "pre_apply",
                    "classification": "live_mutation_consent_missing",
                    "provider": "lxc_native",
                    "node": "swarm-manager",
                },
            )
        )
        later_step = _RecordingAction("later")

        result = await PlatformInitWorkflow(
            [blocked_step, later_step],
            progress=progress,
        ).run()

        self.assertEqual(blocked_step.calls, ["platform:node:swarm-manager"])
        self.assertEqual(later_step.calls, [])
        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertEqual(result.verification_results[0].target_id, "platform:node:swarm-manager")
        self.assertEqual(
            progress.summary(),
            [
                ("apply", "apply", "started", "pending"),
                ("apply", "apply", "completed", "completed"),
                ("pre_apply", "direct verification", "blocked", "blocked"),
                ("platform", "workflow stopped", "blocked", "blocked"),
            ],
        )

    async def test_pre_apply_verified_step_completes_with_observed_verification(self):
        step = _PreApplyVerifiableAction(
            "pre-apply-verified",
            VerificationResult(
                target_id="pre-apply-verified",
                status=VerificationStatus.VERIFIED,
                message="Command-backed verification contract is configured.",
                evidence={"phase": "pre_apply"},
            ),
        )

        result = await PlatformInitWorkflow([step]).run()

        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertEqual(["pre-apply-verified"], step.calls)
        self.assertEqual(["pre-apply-verified"], step.verifications)
        self.assertEqual(
            ("pre_apply", "verify"),
            tuple(item.evidence["phase"] for item in result.verification_results),
        )

    async def test_failed_apply_stops_workflow_before_verify_and_later_steps(self):
        progress = _RecordingProgress()
        failing_step = _FailingApplyAction("failing")
        later_step = _RecordingAction("later")

        result = await PlatformInitWorkflow(
            [failing_step, later_step],
            progress=progress,
        ).run()

        self.assertEqual(PlatformWorkflowStatus.FAILED_TO_APPLY, result.status)
        self.assertEqual(["failing"], failing_step.calls)
        self.assertEqual([], failing_step.verifications)
        self.assertEqual([], later_step.calls)
        self.assertEqual(VerificationStatus.FAILED_TO_APPLY, result.verification_results[0].status)
        self.assertEqual(
            progress.summary(),
            [
                ("apply", "apply", "started", "pending"),
                ("apply", "apply result", "failed_to_apply", "failed_to_apply"),
                ("platform", "workflow stopped", "failed_to_apply", "failed_to_apply"),
            ],
        )

    async def test_failed_apply_result_is_not_treated_as_success(self):
        progress = _RecordingProgress()
        failing_step = _FailedApplyResultAction("failed-result")

        result = await PlatformInitWorkflow([failing_step], progress=progress).run()

        self.assertEqual(PlatformWorkflowStatus.FAILED_TO_APPLY, result.status)
        self.assertEqual(VerificationStatus.FAILED_TO_APPLY, result.verification_results[0].status)
        self.assertEqual([], failing_step.verifications)
        self.assertEqual(
            progress.summary(),
            [
                ("apply", "apply", "started", "pending"),
                ("apply", "apply result", "failed_to_apply", "failed_to_apply"),
                ("platform", "workflow stopped", "failed_to_apply", "failed_to_apply"),
            ],
        )

    async def test_failed_verify_stops_before_later_apply_steps(self):
        progress = _RecordingProgress()
        failing_verify = _FailingVerifyAction("verify-fails")
        later_step = _RecordingAction("later")

        result = await PlatformInitWorkflow(
            [failing_verify, later_step],
            progress=progress,
        ).run()

        self.assertEqual(PlatformWorkflowStatus.FAILED_TO_VERIFY, result.status)
        self.assertEqual(["verify-fails"], failing_verify.calls)
        self.assertEqual(["verify-fails"], failing_verify.verifications)
        self.assertEqual([], later_step.calls)
        self.assertEqual(VerificationStatus.FAILED_TO_VERIFY, result.verification_results[0].status)
        self.assertEqual(
            progress.summary(),
            [
                ("apply", "apply", "started", "pending"),
                ("apply", "apply", "completed", "completed"),
                ("verify", "verify", "started", "pending"),
                ("verify", "verify", "failed_to_verify", "failed_to_verify"),
                ("platform", "workflow stopped", "failed_to_verify", "failed_to_verify"),
            ],
        )

    async def test_reset_failed_verify_stops_before_later_destructive_step(self):
        progress = _RecordingProgress()
        failing_verify = _FailingVerifyAction("reset-verify-fails")
        later_step = _RecordingAction("later-reset")

        result = await PlatformResetWorkflow(
            [failing_verify, later_step],
            progress=progress,
        ).run(RESET_TINY_SWARM_PLATFORM_CONFIRMATION)

        self.assertEqual(PlatformWorkflowStatus.FAILED_TO_VERIFY, result.status)
        self.assertTrue(result.executed)
        self.assertEqual(failing_verify.calls, ["reset-verify-fails"])
        self.assertEqual(failing_verify.verifications, ["reset-verify-fails"])
        self.assertEqual(later_step.calls, [])
        self.assertEqual(VerificationStatus.FAILED_TO_VERIFY, result.verification_results[0].status)
        self.assertEqual(
            progress.summary(),
            [
                ("apply", "apply", "started", "pending"),
                ("apply", "apply", "completed", "completed"),
                ("verify", "verify", "started", "pending"),
                ("verify", "verify", "failed_to_verify", "failed_to_verify"),
                ("platform", "workflow stopped", "failed_to_verify", "failed_to_verify"),
            ],
        )

    async def test_destroy_missing_verify_evidence_blocks_before_later_destructive_step(self):
        progress = _RecordingProgress()
        missing_evidence = _MissingEvidenceAction("destroy-missing-evidence")
        later_step = _RecordingAction("later-destroy")

        result = await PlatformDestroyWorkflow(
            [missing_evidence, later_step],
            progress=progress,
        ).run(DESTROY_TINY_SWARM_PLATFORM_CONFIRMATION)

        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertTrue(result.executed)
        self.assertEqual(missing_evidence.calls, ["destroy-missing-evidence"])
        self.assertEqual(missing_evidence.verifications, ["destroy-missing-evidence"])
        self.assertEqual(later_step.calls, [])
        self.assertEqual(VerificationStatus.BLOCKED, result.verification_results[0].status)
        self.assertEqual(result.verification_results[0].message, "Verification evidence is missing.")

    async def test_reset_blocked_direct_verification_after_apply_reports_executed(self):
        blocked_step = _VerificationResultAction(
            VerificationResult(
                target_id="platform:reset:managed-nodes",
                status=VerificationStatus.BLOCKED,
                message="Managed node reset was blocked after apply.",
                evidence={
                    "phase": "verify",
                    "classification": "reset_blocked",
                    "applied": "true",
                },
            )
        )

        result = await PlatformResetWorkflow([blocked_step]).run(
            RESET_TINY_SWARM_PLATFORM_CONFIRMATION
        )

        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertTrue(result.executed)
        self.assertEqual(blocked_step.calls, ["platform:reset:managed-nodes"])

    async def test_lxc_aggregate_direct_verification_progress_uses_safe_counts(self):
        progress = _RecordingProgress()
        step = _VerificationResultAction(
            VerificationResult(
                target_id="platform:init:lxc-container-runtime",
                status=VerificationStatus.VERIFIED,
                message="Container runtime phase reached a terminal state.",
                evidence={
                    "phase": "verify",
                    "classification": "container_runtime_verified",
                    "result_count": "2",
                    "verified_count": "2",
                    "blocked_count": "0",
                    "failed_apply_count": "0",
                    "failed_verify_count": "0",
                    "node": "swarm-manager",
                },
            )
        )

        result = await PlatformInitWorkflow([step], progress=progress).run()

        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertGreater(len(progress.events), 2)
        _, _, direct_event, *_ = progress.events
        self.assertEqual(direct_event.step, "direct verification")
        self.assertIn("result_count=2", direct_event.safe_message)
        self.assertIn("verified_count=2", direct_event.safe_message)
        self.assertIn("blocked_count=0", direct_event.safe_message)
        self.assertIn("failed_apply_count=0", direct_event.safe_message)
        self.assertIn("failed_verify_count=0", direct_event.safe_message)
        self.assertNotIn("swarm-manager", direct_event.safe_message)
        self.assertNotIn("incus", direct_event.safe_message)
        self.assertNotIn("container_runtime_verified", direct_event.safe_message)

    async def test_missing_verify_evidence_blocks_continuation(self):
        progress = _RecordingProgress()
        missing_evidence = _MissingEvidenceAction("missing-evidence")
        later_step = _RecordingAction("later")

        result = await PlatformInitWorkflow(
            [missing_evidence, later_step],
            progress=progress,
        ).run()

        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertEqual(["missing-evidence"], missing_evidence.calls)
        self.assertEqual(["missing-evidence"], missing_evidence.verifications)
        self.assertEqual([], later_step.calls)
        self.assertEqual(
            progress.summary(),
            [
                ("apply", "apply", "started", "pending"),
                ("apply", "apply", "completed", "completed"),
                ("verify", "verify", "started", "pending"),
                ("verify", "verify", "blocked", "blocked"),
                ("platform", "workflow stopped", "blocked", "blocked"),
            ],
        )

    async def test_verified_steps_append_evidence_when_repository_is_configured(self):
        evidence_repository = _RecordingEvidenceRepository()
        step = _RecordingAction("init")

        result = await PlatformInitWorkflow(
            [step],
            verification_evidence_repository=evidence_repository,
        ).run()

        self.assertEqual(PlatformWorkflowStatus.COMPLETED, result.status)
        self.assertEqual(("init",), tuple(item.target_id for item in evidence_repository.results))
        self.assertEqual(("init",), tuple(item.target_id for item in result.verification_results))

    async def test_missing_verify_evidence_appends_blocked_result_when_repository_is_configured(self):
        evidence_repository = _RecordingEvidenceRepository()
        missing_evidence = _MissingEvidenceAction("missing-evidence")

        result = await PlatformInitWorkflow(
            [missing_evidence],
            verification_evidence_repository=evidence_repository,
        ).run()

        self.assertEqual(PlatformWorkflowStatus.BLOCKED, result.status)
        self.assertEqual(
            (VerificationStatus.BLOCKED,),
            tuple(item.status for item in evidence_repository.results),
        )


class _RecordingAction:
    def __init__(self, name: str):
        self.name = name
        self.calls: list[str] = []
        self.verifications: list[str] = []
        self.verification_target_id = name

    async def run(self) -> object:
        await async_checkpoint()
        self.calls.append(self.name)
        return self.name

    async def verify(self) -> VerificationResult:
        await async_checkpoint()
        self.verifications.append(self.name)
        return VerificationResult(
            target_id=self.verification_target_id,
            status=VerificationStatus.VERIFIED,
            message="Step verified.",
            evidence={"phase": "verify"},
        )


class _PreApplyAction:
    def __init__(self, name: str, pre_apply_result: VerificationResult):
        self.name = name
        self.calls: list[str] = []
        self.verifications: list[str] = []
        self.verification_target_id = name
        self.pre_apply_result = pre_apply_result

    async def run(self) -> object:
        await async_checkpoint()
        self.calls.append(self.name)
        return self.name

    def verify_pre_apply(self) -> VerificationResult:
        return self.pre_apply_result

    async def verify(self) -> object:
        await async_checkpoint()
        return None


class _PreApplyVerifiableAction(_PreApplyAction):
    async def verify(self) -> VerificationResult:
        await async_checkpoint()
        self.verifications.append(self.name)
        return VerificationResult(
            target_id=self.verification_target_id,
            status=VerificationStatus.VERIFIED,
            message="Step verified.",
            evidence={"phase": "verify"},
        )


class _ApplyOnlyAction:
    def __init__(self, name: str):
        self.name = name
        self.calls: list[str] = []

    async def run(self) -> object:
        await async_checkpoint()
        self.calls.append(self.name)
        return self.name


class _FailingApplyAction(_RecordingAction):
    async def run(self) -> object:
        await async_checkpoint()
        self.calls.append(self.name)
        raise RuntimeError("apply failed")


class _FailedApplyResultAction(_RecordingAction):
    async def run(self) -> object:
        await async_checkpoint()
        self.calls.append(self.name)
        return VerificationResult(
            target_id=self.verification_target_id,
            status=VerificationStatus.FAILED_TO_APPLY,
            message="Apply reported failure.",
            evidence={"phase": "apply"},
        )


class _FailingVerifyAction(_RecordingAction):
    async def verify(self) -> VerificationResult:
        await async_checkpoint()
        self.verifications.append(self.name)
        raise RuntimeError("verify failed")


class _MissingEvidenceAction:
    def __init__(self, name: str):
        self.name = name
        self.calls: list[str] = []
        self.verifications: list[str] = []
        self.verification_target_id = name

    async def run(self) -> object:
        await async_checkpoint()
        self.calls.append(self.name)
        return self.name

    async def verify(self) -> object:
        await async_checkpoint()
        self.verifications.append(self.name)
        return None


class _ForbiddenAction:
    async def run(self) -> object:
        await async_checkpoint()
        raise AssertionError("destructive step must not run without confirmation")


class _PreflightAction:
    def __init__(self, result: PreflightResult):
        self.result = result
        self.calls: list[str] = []

    async def run(self) -> PreflightResult:
        await async_checkpoint()
        self.calls.append("preflight")
        return self.result


class _PreflightSequenceAction:
    def __init__(self, results: tuple[PreflightResult, ...]):
        self.results = results
        self.calls: list[str] = []

    async def run(self) -> PreflightResult:
        await async_checkpoint()
        self.calls.append("preflight")
        index = min(len(self.calls) - 1, len(self.results) - 1)
        return self.results[index]


class _ProviderGuardAction:
    def __init__(self, result: VerificationResult):
        self.result = result
        self.calls: list[str] = []

    async def run(self) -> VerificationResult:
        await async_checkpoint()
        self.calls.append("provider")
        return self.result


class _VerificationResultAction:
    returns_verification_result = True

    def __init__(self, result: VerificationResult):
        self.result = result
        self.verification_target_id = result.target_id
        self.calls: list[str] = []

    async def run(self) -> VerificationResult:
        await async_checkpoint()
        self.calls.append(self.verification_target_id)
        return self.result


class _RecordingEvidenceRepository:
    def __init__(self) -> None:
        self.results: list[VerificationResult] = []

    def append(self, result: VerificationResult) -> None:
        self.results.append(result)

    def list_all(self) -> tuple[VerificationResult, ...]:
        return tuple(self.results)


class _RecordingProgress(PortWorkflowProgress):
    def __init__(self) -> None:
        self.events: list[WorkflowProgressEvent] = []

    def report(self, event: WorkflowProgressEvent) -> None:
        self.events.append(event)

    def summary(self) -> list[tuple[str, str, str, str]]:
        return [
            (event.phase, event.step, event.status, event.result)
            for event in self.events
        ]


class _RecordingMethodTrace(PortMethodTrace):
    def __init__(self) -> None:
        self.events: list[MethodTraceEvent] = []

    def report(self, event: MethodTraceEvent) -> None:
        self.events.append(event)

    def summary(self) -> list[tuple[str, str, str, str | None, str | None]]:
        return [
            (
                event.class_name,
                event.method_name,
                event.status,
                event.safe_result,
                event.exception_type,
            )
            for event in self.events
        ]


if __name__ == "__main__":
    unittest.main()
