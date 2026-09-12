from __future__ import annotations

from pathlib import Path
import unittest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_ROOT = REPOSITORY_ROOT / ".github" / "workflows"


class CiWorkflowContractTests(unittest.TestCase):
    def test_python_quality_gate_runs_the_canonical_gate_on_push_and_pull_request(self) -> None:
        workflow = self._workflow("python-quality-gate.yml")

        self.assertIn("name: Python Quality Gate", workflow)
        self.assertIn("  push:\n    branches: [main]", workflow)
        self.assertIn("  pull_request:\n    branches: [main]", workflow)
        self.assertIn("python3 tools/quality_gate.py quality", workflow)
        self.assertIn("pip install --require-hashes -r requirements.lock", workflow)
        self.assertIn("pip install --no-deps -e .", workflow)
        self.assertIn("actions/upload-artifact@", workflow)
        self.assertIn("if-no-files-found: error", workflow)
        self.assertNotIn("pip install -r requirements-dev.txt", workflow)
        self.assertNotIn("install.sh", workflow)
        self.assertNotIn("docker swarm", workflow)
        self.assertNotIn("incus", workflow.lower())

    def test_quality_tool_installation_is_explicitly_pinned(self) -> None:
        workflow = self._workflow("python-quality-gate.yml")

        for requirement in (
            "coverage==7.15.4",
            "import-linter==2.13",
            "mypy==2.3.1",
            "pip-audit==2.10.1",
            "pip-tools==7.6.1",
            "ruff==0.15.22",
            "types-PyYAML==6.0.12.20260518",
            "types-requests==2.33.0.20260712",
        ):
            with self.subTest(requirement=requirement):
                self.assertIn(f'"{requirement}"', workflow)

    def test_sonar_workflow_owns_external_analysis_only(self) -> None:
        workflow = self._workflow("sonar_external_gate.yml")

        self.assertIn("workflow_run:", workflow)
        self.assertIn("workflows: [Python Quality Gate]", workflow)
        self.assertIn("actions/download-artifact@", workflow)
        self.assertIn("sonar-coverage-${{ github.event.workflow_run.id }}", workflow)
        self.assertIn("github.event.workflow_run.conclusion != 'success'", workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", workflow)
        self.assertIn("Require SonarCloud token", workflow)
        self.assertIn("external gate is not green", workflow)
        self.assertIn("exit 1", workflow)
        self.assertIn("SonarSource/sonarqube-scan-action@", workflow)
        self.assertNotIn("tools/quality_gate.py quality", workflow)
        self.assertNotIn("Skip SonarCloud Scan", workflow)

    def test_sonar_workflow_does_not_duplicate_the_locked_runtime_gate(self) -> None:
        workflow = self._workflow("sonar_external_gate.yml")

        self.assertIn("persist-credentials: false", workflow)
        self.assertIn("ref: ${{ github.event.workflow_run.head_sha }}", workflow)
        self.assertIn("-Dsonar.scm.revision=${{ github.event.workflow_run.head_sha }}", workflow)
        self.assertIn("-Dsonar.qualitygate.wait=true", workflow)
        self.assertNotIn("tools/quality_gate.py quality", workflow)
        self.assertNotIn("pip install --require-hashes -r requirements.lock", workflow)

    def test_python_compatibility_workflow_runs_the_declared_conda_matrix(self) -> None:
        workflow = self._workflow("python-compatibility.yml")

        self.assertIn("name: Python Compatibility", workflow)
        self.assertIn("  push:\n    branches: [main]", workflow)
        self.assertIn("  pull_request:\n    branches: [main]", workflow)
        self.assertIn("fail-fast: false", workflow)
        self.assertIn('python-version: ["3.12", "3.13"]', workflow)
        self.assertIn("conda-incubator/setup-miniconda@835234971496cad1653abb28a638a281cf32541f", workflow)
        self.assertIn("environment-file: environment.yml", workflow)
        self.assertIn("python-version: ${{ matrix.python-version }}", workflow)
        self.assertIn("python -m pip install --require-hashes -r requirements.lock", workflow)
        self.assertIn('python -m pip install "packaging==25.0"', workflow)
        self.assertIn("PYTHONPATH=src python -m unittest discover -s tests -t .", workflow)
        self.assertNotIn("install.sh", workflow)
        self.assertNotIn("docker swarm", workflow.lower())
        self.assertNotIn("incus", workflow.lower())

    def test_classic_live_workflow_is_protected_and_fail_closed(self) -> None:
        workflow = self._workflow("nightly-classic-live.yml")

        self.assertIn("name: Nightly Classic Live", workflow)
        self.assertIn("schedule:", workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("live_approval:", workflow)
        self.assertIn("options: [approve, block]", workflow)
        self.assertIn("runs-on: [self-hosted, linux, tsw-classic]", workflow)
        self.assertIn('TSW_LIVE_RUNNER_VERIFIED: "1"', workflow)
        self.assertIn("environment:", workflow)
        self.assertIn("tiny-swarm-world-classic-live", workflow)
        self.assertIn("needs: qualify-runner", workflow)
        self.assertIn("if: ${{ always() }}", workflow)
        self.assertIn("Reject blocked manual execution", workflow)
        self.assertIn("test -n \"${TARGET_OWNER}\"", workflow)
        self.assertIn("command -v incus", workflow)
        self.assertIn("command -v docker", workflow)
        self.assertIn("run_classic_acceptance.py --approve-live", workflow)
        self.assertIn("--test-only", workflow)
        self.assertIn("TSW_CLASSIC_UPDATE_STACK", workflow)
        self.assertIn("TSW_CLASSIC_UPDATE_FROM_IMAGE", workflow)
        self.assertNotIn("TSW_CLASSIC_CREDENTIAL_ROTATION_REFERENCE", workflow)
        self.assertNotIn("--credential-rotation-reference", workflow)
        self.assertIn("actions/upload-artifact@", workflow)
        self.assertIn("if-no-files-found: error", workflow)
        self.assertNotIn("runs-on: ubuntu-latest", workflow)
        self.assertNotIn("docker swarm", workflow.lower())

    def test_classic_live_runner_records_only_redacted_terminal_evidence(self) -> None:
        runner = (REPOSITORY_ROOT / "tools/live/run_classic_acceptance.py").read_text(
            encoding="utf-8"
        )

        for marker in (
            "LIVE_CONSENT_MISSING",
            "LIVE_PREREQUISITE_MISSING",
            "LIVE_FAILED_AFTER_MUTATION",
            "LIVE_VERIFIED",
            "checksums.sha256",
            "raw stdout, stderr, credentials and environment values were not written",
            "tools/install_debugger.py",
            '"classic_e2e"',
            '"reconcile"',
            '"reconcile_e2e"',
            '"update_e2e"',
            '"recovery"',
            '"recovery_e2e"',
            '"TSW_RUN_POST_INSTALL_BROWSER_LIVE=1"',
            '"PYTHONPATH=src"',
            '"tests.e2e.classic.test_post_install_browser_live"',
            '"update"',
            '"platform"',
            '"runner"',
            '"target_owner_reference_present"',
            '"execution_profile"',
            '"not_applicable_test_only"',
            '"--test-only"',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, runner)
        self.assertIn("capture_output=True", runner)
        self.assertNotIn("print(completed.stdout", runner)
        self.assertNotIn("print(completed.stderr", runner)
        self.assertLess(runner.index('"classic_e2e"'), runner.index('"reconcile"'))
        self.assertLess(runner.index('"reconcile"'), runner.index('"reconcile_e2e"'))
        self.assertLess(runner.index('"reconcile_e2e"'), runner.index('"update"'))
        self.assertLess(runner.index('"update"'), runner.index('"update_e2e"'))
        self.assertLess(runner.index('"update_e2e"'), runner.index('"recovery"'))
        self.assertLess(runner.index('"recovery"'), runner.index('"recovery_e2e"'))

    def test_branch_protection_status_checks_are_documented(self) -> None:
        documentation = (REPOSITORY_ROOT / "documentation/governance/ci-quality-gates.md").read_text(
            encoding="utf-8"
        )

        for check in (
            "Python Quality Gate / Locked Python quality gate",
            "Python Compatibility / Conda Python 3.12",
            "Python Compatibility / Conda Python 3.13",
            "SonarCloud Trusted External Gate / SonarCloud external analysis",
            "Nightly Classic Live / Execute Classic live chain",
        ):
            with self.subTest(check=check):
                self.assertIn(f"`{check}`", documentation)

    def _workflow(self, name: str) -> str:
        return (WORKFLOW_ROOT / name).read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
