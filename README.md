# Tiny Swarm World

Tiny Swarm World creates a local development and test environment with Docker
Swarm, Portainer, Infisical, Nexus, Jenkins, Pulsar, SonarQube and supporting
services. It provisions managed Linux containers through Incus and runs Docker
Engine inside those containers.

The current implementation is the **Classic profile**. RC1 qualification is
still in progress; follow the [RC1 acceptance tracker](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/294)
for the remaining checks. A successful installation on one machine does not
establish that every supported host and lifecycle has passed acceptance.

## Start here

| What you want to do | Read |
|---|---|
| Prepare a machine and install for the first time | [Installation guide](documentation/user_guide/installation.adoc) |
| Find service URLs and sign in | [User Handbook](documentation/user-handbook.adoc#open-the-services) and [credential catalog](documentation/arc42/08_configuration/internal-test-credential-catalog.md) |
| Inspect or reconcile an existing installation | [Daily operation](documentation/user_guide/usage.adoc#daily-operation) |
| Diagnose a failed run | [Troubleshooting](documentation/user_guide/troubleshooting.adoc#first-response) |
| Change code or run development tests | [Developer Manual](documentation/manuals/developer-manual.md) |
| Find architecture, security or audit references | [Documentation index](documentation/README.adoc) |

## Before you install

Use a native Linux or WSL2 shell. WSL2 needs systemd; Windows-native product
execution is not supported.

Prepare these prerequisites in the same shell and user account that will run
the installer:

- Python **3.12 or newer**, with virtual-environment support, and Git. The
  [compatibility workflow](.github/workflows/python-compatibility.yml) currently
  tests Python 3.12 and 3.13.
- Incus installed and initialized, with usable storage, networking and profiles.
  `incus version` and `incus info` must work without `sudo`.
- Host networking and capacity checked against the
  [ready-for-install checklist](documentation/user_guide/installation.adoc#ready-for-install-checklist).
- For WSL2 Windows-browser access, the existing
  [Windows bridge prework](documentation/user-handbook.adoc#_complete_the_required_windows_prework_for_wsl2).
  Native Linux does not need that bridge.

The installer creates managed nodes and their Docker runtime. **It does not
install or initialize the host's Incus daemon.** A host Docker installation
does not replace Docker inside the managed nodes.

Prefer a checkout under the Linux home directory. A deliberate WSL2 checkout
under `/mnt/c`, `/mnt/d` or another Windows mount requires the explicit
filesystem exception described in the installation guide.

## Prepare the checkout

Run these commands after the host prerequisites are ready:

```bash
mkdir -p ~/projects
cd ~/projects
git clone https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World.git
cd Tiny-Swarm-World

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install --upgrade pip
python3 -m pip install --require-hashes -r requirements.lock
python3 -m pip install --no-deps -e .
```

Install the runtime dependencies before calling the installer. The wrapper
imports Python modules before its internal dependency-bootstrap fallback can
run; cloning the repository alone is not a complete setup.

Inspect the available workflows and run static preflight:

```bash
tiny-swarm-world --list-workflows
tiny-swarm-world --preflight
```

Resolve reported blockers before installing. Static preflight does not prove
that services are running. Development tools and the full quality gate are
described in the [Developer Manual](documentation/manuals/developer-manual.md);
they are separate from preparing the runtime package.

## Install a fresh test environment

**`./install.sh` resets the managed Tiny Swarm World environment before setup.**
Use it only for a fresh or deliberately disposable installation. Existing
managed nodes and their data may be removed. To keep an existing environment,
use the [operation guide](documentation/user_guide/usage.adoc#daily-operation).

After completing the installation guide's host and networking checklist:

```bash
./install.sh
```

The default service profile is `service-access`. The installer asks for the
reset phrase `RESET_TINY_SWARM_PLATFORM` and for live-operation consent.
`--headless` changes presentation; it does not make the operation read-only.

The standard internal-test path needs **no credential file**. It uses
deterministic catalog values. These defaults are for isolated, disposable
internal testing; use the documented access boundary before exposing services.

If an override is needed, follow the
[optional credential setup](documentation/user_guide/installation.adoc#operator-credential-overrides).
A credential file must be user-owned, mode `0600`, inside a user-owned
`0700` directory on a Linux-native filesystem. The WSL source-path exception
does not relax that requirement.

## Open services and verify the result

After successful setup, the installer prints access targets and login
identifiers. Start with the configured Service Access route, normally
[https://service-access.tsw.local](https://service-access.tsw.local), when local
name resolution, forwarding and TLS trust are configured.

Use the [credential catalog](documentation/arc42/08_configuration/internal-test-credential-catalog.md)
for default login details, or your protected source for an explicit override.
Portainer uses `admin`; Infisical uses an email address. Service-specific
exceptions are listed in the catalog. Passwords are not printed by the
installer, and a dashboard secret reference does not prove the item exists in
Infisical.

Check the platform:

```bash
tiny-swarm-world --service-profile service-access platform verify
```

Then sign in to the required services from the browser you intend to use.
An HTTP 200 response or a login page proves neither authentication nor a fully
working installation. See the
[verification steps](documentation/user_guide/installation.adoc#verify-installed-runtime).

If a route is unavailable, distinguish name resolution, forwarding, TLS,
service readiness and authentication using the
[troubleshooting guide](documentation/user_guide/troubleshooting.adoc#first-response).
Use the evidence directory printed for your run, inspect exit codes first,
and redact diagnostics before sharing them.

## Reconcile, reset and update are different operations

| Operation | Meaning |
|---|---|
| `platform verify` | Inspect the existing platform without repairing it. |
| `platform reconcile --live` | Reconcile managed platform state with explicit consent; it is not a complete application update. |
| `setup run --live` | Run the broader setup workflow without the installer's preliminary reset; it still changes infrastructure. |
| `./install.sh` | Reset the managed environment, then perform fresh setup. |
| Product update | A canonical update workflow and cross-host RC1 acceptance remain tracked in [#297](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/297). |

There is no supported `./install.sh --update` command in this revision.
Pulling new source code and running reconcile does not establish a supported
upgrade of a running installation.

See [Daily operation](documentation/user_guide/usage.adoc#daily-operation) for
commands, configuration continuity and recovery choices. The
[live operation surface catalog](documentation/system/live-operation-surfaces.adoc)
identifies supported workflow boundaries and retained compatibility assets.

## For contributors

The Python code follows a domain/application/infrastructure split.
Start with the [Developer Manual](documentation/manuals/developer-manual.md),
[AGENTS.md](AGENTS.md) and [QUALITY.md](QUALITY.md).

The future [multi-runtime vision](https://github.com/MatthiasBurger-Coder/Tiny-Swarm-World/issues/251)
covers Podman and Kubernetes. Those profiles are separate from the current
Classic implementation.
