import unittest
from unittest.mock import Mock

from tiny_swarm_world.application.ports.host import PortHostPreparation
from tiny_swarm_world.application.services.deployment.verify_host_prerequisites import VerifyHostPrerequisites
from tiny_swarm_world.application.services.deployment.workflows import DeploymentApplyWorkflow
from tiny_swarm_world.domain.inventory import VerificationResult, VerificationStatus
from tiny_swarm_world.domain.preflight import HostPreparationResult, HostPreparationStatus


class TestHostPrerequisites(unittest.IsolatedAsyncioTestCase):
    def check(self, status=HostPreparationStatus.FAILED, verified=False, control="missing"):
        host = Mock(spec=PortHostPreparation)
        host.verify.return_value = HostPreparationResult(
            "verify", "native_linux", status, "host check", verified=verified,
            evidence={"net.bridge.bridge-nf-call-iptables": "active" if verified else control},
        )
        return VerifyHostPrerequisites(host)

    async def test_missing_kernel_blocks_before_any_preparation_or_deployment(self):
        check = self.check()
        prepare, deploy = Mock(), Mock()
        result = await DeploymentApplyWorkflow(
            steps=(deploy,), pre_apply_steps=(prepare,), prerequisite_checks=(check,),
        ).run()
        self.assertFalse(result.executed)
        self.assertEqual(result.verification_results[0].status, VerificationStatus.BLOCKED)
        self.assertEqual(result.verification_results[0].evidence["classification"],
                         "host_kernel_prerequisites_missing")
        prepare.run.assert_not_called()
        deploy.run.assert_not_called()
        check.host.prepare.assert_not_called()

    async def test_disabled_and_unreadable_controls_prevent_all_mutations(self):
        for control in ("disabled", "read_error"):
            with self.subTest(control=control):
                prepare, deploy = Mock(), Mock()
                result = await DeploymentApplyWorkflow(
                    steps=(deploy,), pre_apply_steps=(prepare,),
                    prerequisite_checks=(self.check(control=control),),
                ).run()
                self.assertFalse(result.executed)
                prepare.run.assert_not_called()
                deploy.run.assert_not_called()
                deploy.verify.assert_not_called()

    async def test_active_kernel_allows_existing_deployment_contract(self):
        check = self.check(HostPreparationStatus.SUCCESS, True)
        calls = []
        observation = check.host.verify.return_value
        check.host.verify.side_effect = lambda: calls.append("kernel") or observation
        prepare = Mock(spec=["run"])
        prepare.run.side_effect = lambda: calls.append("prepare")
        deploy = Mock(spec=["run", "verify", "verification_target_id"])
        deploy.verification_target_id = "test:deployment"
        deploy.run.side_effect = lambda: calls.append("deploy")
        deploy.verify.return_value = VerificationResult(
            target_id="test:deployment", status=VerificationStatus.VERIFIED, message="ready",
        )
        result = await DeploymentApplyWorkflow(
            steps=(deploy,), pre_apply_steps=(prepare,), prerequisite_checks=(check,),
        ).run()
        self.assertTrue(result.executed)
        deploy.run.assert_called_once()
        self.assertEqual(calls, ["kernel", "prepare", "deploy"])

    def test_success_without_verified_evidence_is_blocked(self):
        self.assertEqual(self.check(HostPreparationStatus.SUCCESS).verify().status,
                         VerificationStatus.BLOCKED)

    async def test_unverified_host_blocks_before_preparation(self):
        prepare, deploy = Mock(), Mock()
        result = await DeploymentApplyWorkflow(
            steps=(deploy,), pre_apply_steps=(prepare,),
            prerequisite_checks=(VerifyHostPrerequisites(None),),
        ).run()
        self.assertEqual(result.verification_results[0].evidence["classification"],
                         "host_environment_unverified")
        prepare.run.assert_not_called()
        deploy.run.assert_not_called()

    async def test_probe_exception_fails_closed_before_preparation(self):
        check = self.check()
        check.host.verify.side_effect = OSError("sensitive diagnostic")
        prepare, deploy = Mock(), Mock()
        result = await DeploymentApplyWorkflow(
            steps=(deploy,), pre_apply_steps=(prepare,), prerequisite_checks=(check,),
        ).run()
        prepare.run.assert_not_called()
        deploy.run.assert_not_called()
        self.assertNotIn("sensitive diagnostic", str(result))
