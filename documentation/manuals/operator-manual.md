# Operator Manual

Use this page to choose the next task. Commands run from the repository root
in a Linux or WSL2 shell with the project's Python environment active.

| Task | Instructions | Effect |
|---|---|---|
| First installation | [Installation guide](../user_guide/installation.adoc) | Prepares and then resets/creates the managed test environment. |
| Open services and sign in | [User Handbook](../user_guide/user-handbook.adoc#open-the-services) | Uses the configured routes and effective credentials. |
| Inspect an installation | [Daily operation](../user_guide/usage.adoc#daily-operation) | Read-only platform verification. |
| Reconcile or recover | [Daily operation](../user_guide/usage.adoc#daily-operation) | Explicitly changes managed state; preserves the distinction from fresh reset. |
| Diagnose a failure | [First response](../user_guide/troubleshooting.adoc#first-response) | Starts with the first failed phase and exit codes. |
| Change credentials | [Optional overrides](../user_guide/installation.adoc#operator-credential-overrides) | Supplies an explicit input; it is not an automatic rotation procedure. |

## Before the first live run

Incus installation, initialization, host networking and permissions are
operator prerequisites. Tiny Swarm World installs Docker inside managed LXC
nodes; it does not prepare the Incus host daemon for you.

**The installer wrapper resets the managed environment before setup.** Read the
reset scope before running it on a machine with data you want to keep. Use
`platform verify` to inspect an existing installation first.

## Credentials and evidence

The standard internal-test installation uses the
[credential catalog](../arc42/08_configuration/internal-test-credential-catalog.md)
without a manually prepared password file. Overrides are optional and require
a protected Linux-native file/directory when file-based. Infisical bootstrap
login and synchronized service items are separate concerns.

Use the evidence path printed by your run. Redact diagnostics before sharing;
keep credentials, session tokens and private material out of reports.
For exposure policy or an incident, use the
[Security Manual](security-manual.md).

## What is verified

Static preflight and local tests do not prove live service access. A usable
installation also needs successful platform verification and actual service
logins. RC1 qualification is tracked in
[#294](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/294).
The supported update workflow remains pending; do not treat reset or reconcile
as a product upgrade.
