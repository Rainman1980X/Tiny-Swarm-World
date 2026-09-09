import json
import os
import re
import subprocess
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BRIDGE_SCRIPT = REPOSITORY_ROOT / "tools" / "windows" / "tws-wsl-bridge.ps1"
BRIDGE_SERVICE_RUNNER = REPOSITORY_ROOT / "tools" / "windows" / "tws-wsl-bridge-service.ps1"
BRIDGE_PESTER_TESTS = REPOSITORY_ROOT / "tests" / "windows" / "tws-wsl-bridge.Tests.ps1"
BRIDGE_GUIDE = REPOSITORY_ROOT / "tools" / "windows" / "README.windows-wsl-bridge.md"
BRIDGE_CONFIG = REPOSITORY_ROOT / "tools" / "windows" / "tws-wsl-bridge.config.json"
NETWORK_GUIDE = REPOSITORY_ROOT / "documentation" / "system" / "network.adoc"
USER_HANDBOOK = REPOSITORY_ROOT / "documentation" / "user_guide" / "user-handbook.adoc"
WINDOWS_POWERSHELL = Path(
    "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
)


class TestWindowsWslBridgeAssets(unittest.TestCase):
    def test_bridge_script_exposes_read_only_prerequisite_action(self):
        script = BRIDGE_SCRIPT.read_text(encoding="utf-8")

        self.assertIn(
            'ValidateSet("prerequisites", "discover", "install", "reconcile", "refresh", "verify", "status", "uninstall")',
            script,
        )
        self.assertIn('"prerequisites" {', script)
        self.assertIn("No bridge state was changed.", script)
        self.assertIn("function Get-BridgePrerequisiteResults", script)
        self.assertIn("function Assert-BridgePrerequisites", script)

    def test_install_and_reconcile_gate_mutations_on_prerequisites(self):
        script = BRIDGE_SCRIPT.read_text(encoding="utf-8")

        install_block = _switch_block(script, "install")
        self.assertLess(
            install_block.index("Assert-BridgePrerequisites"),
            install_block.index("Install-BridgeService"),
        )
        for action in ("reconcile", "refresh"):
            with self.subTest(action=action):
                block = _switch_block(script, action)
                prerequisite_index = block.index("Assert-BridgePrerequisites")
                reconcile_index = block.index("Invoke-BridgeReconcile")
                self.assertLess(prerequisite_index, reconcile_index)

    def test_bridge_registers_periodic_windows_service_agent(self):
        script = BRIDGE_SCRIPT.read_text(encoding="utf-8")
        service_runner = BRIDGE_SERVICE_RUNNER.read_text(encoding="utf-8")
        config = BRIDGE_CONFIG.read_text(encoding="utf-8")
        definition_function = _function_block(script, "New-BridgeServiceDefinition")

        self.assertIn("function Get-BridgeDiscovery", script)
        self.assertIn("function Invoke-BridgeReconcile", script)
        self.assertIn("function Install-BridgeService", script)
        self.assertIn("function Test-BridgeServiceReady", script)
        self.assertIn("function Uninstall-BridgeService", script)
        self.assertIn("WinSW.NET461.exe", script)
        self.assertIn(
            '$WinSwSha256 = "B5066B7BBDFBA1293E5D15CDA3CAAEA88FBEAB35BD5B38C41C913D492AADFC4F"',
            script,
        )
        self.assertIn("<hidewindow>true</hidewindow>", script)
        self.assertIn("Get-Credential", script)
        self.assertIn("New-Service", script)
        self.assertIn("SeServiceLogonRight", script)
        self.assertIn("Test-BridgeServiceAccountMatchesCurrentIdentity", script)
        self.assertIn("SecurityIdentifier", script)
        self.assertIn('$normalizedAccount.StartsWith(".\\")', script)
        self.assertIn("Test-BridgeServicePathMatches", script)
        self.assertIn("Remove-BridgeServiceRegistration", script)
        self.assertIn("& sc.exe delete $ServiceName", script)
        self.assertIn("function Protect-BridgeServiceRoot", script)
        self.assertIn("[Environment+SpecialFolder]::CommonApplicationData", script)
        self.assertNotIn(
            'Join-Path $env:ProgramData "TinySwarmWorld\\WslBridge"',
            script,
        )
        self.assertIn("DeleteSubdirectoriesAndFiles", script)
        acl_function = _function_block(script, "Set-BridgeExactAcl")
        self.assertIn("Invoke-BridgeHandleAclHardening", acl_function)
        self.assertIn("FileFlagOpenReparsePoint", script)
        self.assertIn("SetSecurityInfo", script)
        self.assertNotIn("icacls.exe", script)
        self.assertIn("$InstalledBridgeScriptPath", script)
        self.assertIn("$InstalledServiceRunnerPath", script)
        self.assertIn("$InstalledConfigPath", script)
        self.assertIn("$InstalledPortRegistryPath", script)
        self.assertIn(
            "$escapedBridge = [Security.SecurityElement]::Escape($InstalledBridgeScriptPath)",
            definition_function,
        )
        self.assertIn(
            "$escapedRunner = [Security.SecurityElement]::Escape($InstalledServiceRunnerPath)",
            definition_function,
        )
        self.assertNotIn("Escape($PSCommandPath)", definition_function)
        self.assertIn("function Write-TextAtomically", script)
        self.assertIn('Global\\TinySwarmWorldWslBridgeReconcile', script)
        self.assertIn('Global\\TinySwarmWorldWslBridgeServiceUpdate', script)
        self.assertIn("function Get-FirewallRuleSnapshot", script)
        self.assertIn("function Get-ExactBridgeFirewallRules", script)
        self.assertIn("FiltersByRuleId", script)
        self.assertIn("Get-CimInstance -ClassName Win32_Service", script)
        self.assertNotIn("<password>", script)
        self.assertIn("while ($true)", service_runner)
        self.assertIn("-NoProfile", service_runner)
        self.assertIn("-NonInteractive", service_runner)
        self.assertIn("-Action refresh", service_runner)
        self.assertIn("-PortRegistryPath $PortRegistryPath", service_runner)
        self.assertNotIn("StateEvidencePath", service_runner)
        self.assertNotIn("StateEvidencePath", definition_function)
        self.assertNotIn(
            "StateEvidencePath",
            _function_block(script, "Write-StateFile"),
        )
        self.assertIn(
            "StateEvidencePath",
            _function_block(script, "Test-BridgeLegacyServiceDefinitionOwned"),
        )
        self.assertIn("$consecutiveFailures -ge 3", service_runner)
        self.assertLess(service_runner.index("while ($true)"), service_runner.index("Start-Sleep"))
        self.assertIn('contractVersion    = 2', script)
        self.assertIn("agentMode          = Get-BridgeAgentMode", script)
        self.assertIn("bundleId           = $bundleIdentity.BundleId", script)
        self.assertIn('"discoveryIntervalMinutes": 1', config)

    def test_service_upgrade_is_transactional_and_behavior_tested(self):
        script = BRIDGE_SCRIPT.read_text(encoding="utf-8")
        tests = BRIDGE_PESTER_TESTS.read_text(encoding="utf-8")
        install_function = _function_block(script, "Install-BridgeService")

        for function_name in (
            "Get-BridgeServiceOwnership",
            "New-BridgeStagedPayload",
            "Test-BridgeStagedPayload",
            "Write-BridgeTransactionJournal",
            "Switch-BridgePayload",
            "Restore-BridgePayload",
            "Recover-BridgeInterruptedTransaction",
            "Wait-BridgeServiceHeartbeat",
        ):
            self.assertIn(f"function {function_name}", script)
        self.assertLess(
            install_function.index("Get-BridgeServiceOwnership"),
            install_function.index("Request-BridgeServiceCredential"),
        )
        self.assertLess(
            install_function.index("New-BridgeStagedPayload"),
            install_function.index("Stop-BridgeServiceChecked"),
        )
        self.assertLess(
            install_function.index("Stop-BridgeServiceChecked"),
            install_function.index("Switch-BridgePayload"),
        )
        self.assertIn("partial candidate move", tests)
        self.assertIn("ownership is a collision", tests)
        self.assertIn("credential dialog is cancelled", tests)
        self.assertIn("ACL hardening reports an error", tests)
        self.assertIn("bounded mutex timeout", tests)
        self.assertIn("three consecutive reconcile errors", tests)

    @unittest.skipUnless(
        os.name == "nt" or WINDOWS_POWERSHELL.exists(),
        "Windows PowerShell is unavailable on this Linux host.",
    )
    def test_windows_service_behavior_contract_with_pester(self):
        executable = "powershell.exe" if os.name == "nt" else str(WINDOWS_POWERSHELL)
        script_path = _as_windows_path(BRIDGE_PESTER_TESTS)
        command = (
            "Import-Module Pester; "
            f"$result = Invoke-Pester -Script '{script_path}' -PassThru; "
            "if ($result.FailedCount -ne 0) { exit 1 }"
        )

        completed = subprocess.run(
            [executable, "-NoProfile", "-NonInteractive", "-Command", command],
            cwd=REPOSITORY_ROOT,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=60,
        )

        self.assertEqual(completed.returncode, 0, completed.stdout)

    def test_service_is_the_only_new_agent_registration_path(self):
        script = BRIDGE_SCRIPT.read_text(encoding="utf-8")

        self.assertIn('Name "service-management"', script)
        self.assertIn("Windows service management commands are available.", script)
        self.assertNotIn("function Register-BridgeTask", script)
        self.assertNotIn("function Repair-BridgeTaskAction", script)
        self.assertNotIn("New-ScheduledTaskAction", script)
        self.assertNotIn("tws-wsl-bridge-hidden.vbs", script)
        self.assertNotIn("function Test-BridgeTaskReady", script)
        self.assertIn("function Unregister-BridgeTask", script)

    def test_resource_reconcile_paths_are_no_op_when_state_matches(self):
        script = BRIDGE_SCRIPT.read_text(encoding="utf-8")

        for expected in (
            "Test-PortProxyMappingsReady",
            "PORTPROXY unchanged",
            "Test-FirewallRuleReady",
            "FIREWALL unchanged",
            "Test-HostsFileReady",
            "HOSTS unchanged",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, script)

    def test_managed_hosts_block_writes_one_hostname_per_line(self):
        script = BRIDGE_SCRIPT.read_text(encoding="utf-8")
        block = _function_block(script, "Get-ReconciledHostsContent")

        self.assertIn(
            '$hostNames | ForEach-Object { "$hostsAddress`t$_" }',
            block,
        )
        self.assertNotIn("$($hostNames -join ' ')", block)

    def test_windows_hosts_use_only_the_canonical_tsw_route_namespace(self):
        script = BRIDGE_SCRIPT.read_text(encoding="utf-8")
        config_text = BRIDGE_CONFIG.read_text(encoding="utf-8")
        guide = BRIDGE_GUIDE.read_text(encoding="utf-8")
        network_guide = NETWORK_GUIDE.read_text(encoding="utf-8")

        self.assertEqual(json.loads(config_text)["hostNames"], [])
        self.assertIn("Read-TswPortRegistry", script)
        self.assertIn("route_host", script)
        self.assertIn("*.tsw.local", guide)
        self.assertNotIn(".tws.local", script + config_text + guide + network_guide)

    def test_reconcile_records_discovery_before_failing_on_remaining_drift(self):
        script = BRIDGE_SCRIPT.read_text(encoding="utf-8")
        block = _function_block(script, "Invoke-BridgeReconcile")

        pending_state_index = block.index("reconcile_in_progress")
        mutation_index = block.index("Reconcile-PortProxy")
        discovery_index = block.index("Get-BridgeDiscovery")
        state_index = block.rindex("Write-StateFile")
        failure_index = block.index("if (-not $discovery.Ready)")
        self.assertLess(pending_state_index, mutation_index)
        self.assertLess(discovery_index, state_index)
        self.assertLess(state_index, failure_index)

    def test_bridge_guides_document_reproducible_preparation(self):
        bridge_guide = BRIDGE_GUIDE.read_text(encoding="utf-8")
        network_guide = NETWORK_GUIDE.read_text(encoding="utf-8")
        user_handbook = USER_HANDBOOK.read_text(encoding="utf-8")

        for expected in (
            "-Action prerequisites",
            "-Action install",
            "systemd",
            "iphlpsvc",
            "Prepared-state contract",
            "infra/config/ports.yaml",
            "Windows service",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, bridge_guide)

        self.assertIn("-Action prerequisites", network_guide)
        self.assertIn("tools/windows/README.windows-wsl-bridge.md", network_guide)
        for expected in (
            "Complete The Required Windows Prework For WSL2",
            "-Action prerequisites",
            "-Action install",
            "Get-Service -Name TinySwarmWorldWslBridge",
            "tws-wsl-bridge.config.json",
            "%ProgramData%\\TinySwarmWorld\\WslBridge",
            "TSW_WINDOWS_EXPOSURE=disabled",
        ):
            with self.subTest(handbook_expected=expected):
                self.assertIn(expected, user_handbook)


def _switch_block(script: str, action: str) -> str:
    match = re.search(
        rf'^(?P<indent>[ \t]+)"{re.escape(action)}" \{{(?P<body>.*?)^(?P=indent)\}}',
        script,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"Missing PowerShell switch block for {action}")
    return match.group("body")


def _function_block(script: str, name: str) -> str:
    match = re.search(
        rf"^function {re.escape(name)} \{{(?P<body>.*?)^\}}",
        script,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"Missing PowerShell function {name}")
    return match.group("body")


def _as_windows_path(path: Path) -> str:
    if os.name == "nt":
        return str(path)
    parts = path.resolve().parts
    if len(parts) >= 4 and parts[1] == "mnt" and len(parts[2]) == 1:
        remainder = "\\".join(parts[3:])
        return f"{parts[2].upper()}:\\{remainder}"
    raise AssertionError(f"Cannot translate WSL path to Windows: {path}")


if __name__ == "__main__":
    unittest.main()
