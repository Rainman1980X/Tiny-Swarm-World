#Requires -Version 5.1
#Requires -RunAsAdministrator
<#
.SYNOPSIS
Creates an Ubuntu Hyper-V VM for native Tiny Swarm World tests.
.DESCRIPTION
Run on the Windows host in an elevated PowerShell, not inside WSL.
Requires enabled Hyper-V and a completed reboot. Windows Home does not
include the full Hyper-V role. Firmware virtualization must be enabled.

Download the Ubuntu Server 24.04 LTS amd64 ISO and verify its checksum:
https://releases.ubuntu.com/24.04/

Example (adjust the ISO filename):
  .\New-TSWTestVM.ps1 -IsoPath D:\ISO\ubuntu-24.04.4-live-server-amd64.iso -StartVM

For 32 GiB guest RAM, use -MemoryGiB 32 on a suitably equipped host.
List switches with Get-VMSwitch. Select one with -SwitchName 'MySwitch'.
The default is the existing Windows 'Default Switch' (NAT/DHCP).
No external network adapter is rebound by this script.

On a 32 GiB host, save your WSL work, stop WSL workloads, then run:
  wsl --shutdown
Do not reopen WSL or Docker Desktop during the test. This script does not
terminate WSL automatically. A WSL memory limit is a ceiling, not a fixed
reservation. Budget actual memory use; 48 GiB may still be too little for
a 32 GiB VM plus 19 GiB WSL plus Windows.

INSTALL UBUNTU
  vmconnect.exe localhost TSW-RC1-Ubuntu
Select Ubuntu Server, DHCP, and the full virtual disk. When using guided
LVM, allocate adequate space to / (preferably all available guest space).
Create your own user and enable 'Install OpenSSH server'.
After installation, shut down Ubuntu, then on Windows:
  Get-VMDvdDrive -VMName TSW-RC1-Ubuntu | Set-VMDvdDrive -Path $null
  Start-VM -Name TSW-RC1-Ubuntu
The default VM name above must be adjusted if -VMName was supplied.

SSH AND INCUS (run in Ubuntu)
  sudo apt update
  sudo apt install -y openssh-server incus git ca-certificates curl
  sudo systemctl enable --now ssh
  hostname -I
If UFW is active, allow SSH before connecting: sudo ufw allow OpenSSH
From Windows, replace USER and VM_IP:
  ssh USER@VM_IP
Check the first SSH host fingerprint against the Ubuntu console:
  sudo ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub

On this fresh VM only, initialize Incus interactively:
  sudo incus admin init
Choose: no cluster; create storage; dir for a simple smoke test;
create incusbr0 with automatic IPv4 and NAT; no remote API exposure.
Use the repository's required storage configuration for the actual RC1 run.
Then verify a container:
  sudo incus launch images:ubuntu/24.04 tsw-smoke
  sudo incus exec tsw-smoke -- cat /etc/os-release
  sudo incus exec tsw-smoke -- getent hosts archive.ubuntu.com
  sudo incus list
After inspection, remove only this disposable test container:
  sudo incus delete tsw-smoke --force

Incus LXC containers do not need nested hardware virtualization. Incus VMs
would require a separate KVM/nested-virtualization setup.
Clone the TSW repository onto the guest Linux filesystem, e.g. ~/src.
Use the current repository instructions for native Linux E2E tests.
This script provisions the VM shell; it does not install Ubuntu unattended
or claim an RC1 test result. No Hyper-V execution was possible in the
authoring environment.

Sources:
https://ubuntu.com/server/docs/how-to/virtualisation/ubuntu-on-hyper-v/
https://learn.microsoft.com/en-us/powershell/module/hyper-v/set-vmfirmware
https://linuxcontainers.org/incus/docs/main/installing/
https://linuxcontainers.org/incus/docs/main/howto/initialize/
#>
[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Medium')]
param(
    [Parameter(Mandatory = $true)]
    [ValidateScript({ Test-Path -LiteralPath $_ -PathType Leaf })]
    [string]$IsoPath,
    [ValidatePattern('^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$')]
    [string]$VMName = 'TSW-RC1-Ubuntu',
    [string]$VMRoot = 'C:\Hyper-V',
    [string]$SwitchName = 'Default Switch',
    [ValidateRange(24, 256)][int]$MemoryGiB = 24,
    [ValidateRange(1, 64)][int]$CPUCount = 8,
    [ValidateRange(100, 4096)][int]$DiskGiB = 100,
    [switch]$StartVM
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
Import-Module Hyper-V -ErrorAction Stop
if ((Get-Service vmms).Status -ne 'Running') {
    throw 'Hyper-V VM management service is not running. Enable Hyper-V and reboot first.'
}
$iso = (Resolve-Path -LiteralPath $IsoPath).ProviderPath
if ([IO.Path]::GetExtension($iso) -ine '.iso') { throw 'Supply an Ubuntu amd64 .iso file.' }
$existing = @(Get-VM | Where-Object { $_.Name -eq $VMName })
if ($existing.Count -gt 0) { throw "VM '$VMName' already exists. Inspect it or choose another name." }
$network = @(Get-VMSwitch | Where-Object { $_.Name -eq $SwitchName })
if ($network.Count -ne 1) {
    throw "Switch '$SwitchName' not found uniquely. Run Get-VMSwitch and pass -SwitchName."
}
if ($network[0].SwitchType -eq 'Private') { throw 'A private switch does not provide host SSH or Internet access.' }
$machine = Get-CimInstance Win32_ComputerSystem
if ($CPUCount -gt $machine.NumberOfLogicalProcessors) {
    throw "Requested $CPUCount CPUs exceeds the host logical CPU count."
}
$ramBytes = [long]$MemoryGiB * 1GB
if ([long]$machine.TotalPhysicalMemory -lt ($ramBytes + 6GB)) {
    throw 'Insufficient physical RAM: leave at least 6 GiB for Windows, preferably more.'
}
$vmPath = Join-Path $VMRoot $VMName
if (Test-Path -LiteralPath $vmPath) { throw "Path '$vmPath' already exists; no existing files will be overwritten." }
$diskPath = Join-Path $vmPath "$VMName.vhdx"
if (-not $PSCmdlet.ShouldProcess($VMName, "Create Generation 2 VM: $CPUCount CPUs, $MemoryGiB GiB RAM, $DiskGiB GiB dynamic VHDX")) {
    return
}
try {
    New-Item -ItemType Directory -Path $vmPath | Out-Null
    New-VHD -Path $diskPath -SizeBytes ([long]$DiskGiB * 1GB) -Dynamic | Out-Null
    New-VM -Name $VMName -Generation 2 -MemoryStartupBytes $ramBytes -Path $vmPath -VHDPath $diskPath -SwitchName $SwitchName | Out-Null
    Set-VMProcessor -VMName $VMName -Count $CPUCount
    Set-VMMemory -VMName $VMName -DynamicMemoryEnabled $false -StartupBytes $ramBytes
    Set-VM -Name $VMName -AutomaticStartAction Nothing -AutomaticStopAction ShutDown -AutomaticCheckpointsEnabled $false
    $dvd = Add-VMDvdDrive -VMName $VMName -Path $iso -Passthru
    Set-VMFirmware -VMName $VMName -EnableSecureBoot On -SecureBootTemplate MicrosoftUEFICertificateAuthority -FirstBootDevice $dvd
} catch {
    Write-Warning "Creation failed. Partial resources may remain at '$vmPath'. Inspect them before retrying; nothing was automatically deleted."
    throw
}
Get-VM -Name $VMName | Select-Object Name, State, ProcessorCount, MemoryStartup
Write-Host "VM created. Ubuntu installation: vmconnect.exe localhost $VMName"
if ($StartVM) {
    $os = Get-CimInstance Win32_OperatingSystem
    $freeBytes = [long]$os.FreePhysicalMemory * 1KB
    if ($freeBytes -lt ($ramBytes + 2GB)) {
        Write-Warning 'VM created but not started: insufficient free RAM. Save and close WSL workloads, run wsl --shutdown, then start the VM manually.'
    } else {
        Start-VM -Name $VMName
    }
}
Write-Host 'Full Ubuntu, SSH and Incus instructions: Get-Help .\New-TSWTestVM.ps1 -Full'
