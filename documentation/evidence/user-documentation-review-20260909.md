# User documentation technical-editor review — 2026-09-09

## Scope and baseline

Initial review: main `69df4c67231ecd7b3d228129431630ac8e187f2a`.
Final publication base: main `ea028cfb422208d55cf503d5ce88aded190b2d83`.
This is one documentation-only editorial slice, authorized by the user's request
to review and correct documentation from an operator's perspective.

Primary reader journey: prepare host → prepare Python → fresh installation →
find credentials → open services → verify → operate/recover → understand update
limitations. Edited entry points are README, documentation index, Operator
Manual, User Handbook, installation, usage and troubleshooting guides.
Architecture and credential contracts were read as references, not rewritten.
Historical audit/workflow records and every service-specific reference were
not exhaustively audited.

PR #293 merged while this review was in progress. The main-to-main diff
contains no overlapping edits to the seven selected user pages. The final
patch preserves that merge and corrects installer evidence paths against its
new `_installation_evidence_directory` implementation, including the explicit
root override and appended host/run directories. The printed run path remains
the operator authority. The merge does not prove the remaining live acceptance.

## Findings and corrections

| ID | User-facing problem | Correction | Repository basis |
|---|---|---|---|
| DOC-01 | Competing quickstarts and developer material obscure the first install. | One concise README journey; detailed preparation stays in the installation guide. | README; documentation audience skill |
| DOC-02 | Clone-and-install example omits runtime imports needed before the bootstrap fallback. | Explicit venv, locked dependencies and editable package installation before invoking installer. | `simple_installer.py` imports and `installer.run` order; `pyproject.toml` |
| DOC-03 | README promises VERSION 2 from Linux commands that do not emit that output. | Remove the incorrect duplicated WSL procedure; link existing host preparation. | Existing host detection and handbook WSL prework |
| DOC-04 | Reset wrapper is recommended as routine re-run/recovery. | Warn before fresh examples; distinguish verify, platform reconcile, broader setup, reset and update. | `installer.run` reset-before-setup; CLI workflow catalog |
| DOC-05 | Missing update support is not visible at the operation decision. | Explicitly identify unsupported `install.sh --update` and link #297. | Simple installer argument parser; CLI workflow catalog |
| DOC-06 | Optional credential preparation becomes a mandatory file requirement later. | Default path uses catalog; overrides remain optional throughout. | `_prepare_bootstrap_environment`, `_load_operator_install_file` |
| DOC-07 | Override example omits owner-only parent directory and invites DrvFS storage. | Native-home path, 0700 directory, 0600 file, effective ownership and no symlink guidance; preserve existing file. | `_validate_secure_override_path` |
| DOC-08 | Universal admin login wording hides Infisical email identity. | Point to service-specific catalog; name Portainer and Infisical identity distinction. | `_print_operator_credentials`; catalog |
| DOC-09 | Missing Infisical items are described as values in generated local files. | Separate default catalog, protected overrides, bootstrap login and optional synchronized items. | Credential-source precedence; installer seeding default |
| DOC-10 | Authenticated Pulsar example sources an optional file unconditionally. | Remove that assumption; require effective token through an appropriate private client. | Catalog/default path and explicit override semantics |
| DOC-11 | Reachability examples can be mistaken for TLS or authentication proof. | Label curl -k as HTTP diagnostics; require TLS verification and actual login separately. | Verification-state policy; current PR #293 authentication qualification |
| DOC-12 | Shared Incus cleanup unsets settings in every location. | Require profile-consumer review and only the diagnosed owner-specific correction. | Existing ownership boundary; shared-profile semantics |
| DOC-13 | AsciiDoc catalog links use Markdown syntax; root table has extra cells. | Correct link syntax and remove excess table separators. | AsciiDoc source inspection |
| DOC-14 | Python support statements and developer dependencies differ across entry points. | State >=3.12 and current 3.12/3.13 CI coverage; separate runtime and developer preparation. | `pyproject.toml`; compatibility workflow; QUALITY |
| DOC-15 | Nexus proxy availability is equated with its use for all image pulls. | Describe proxy capability separately from actual selected image/registry routing. | Configuration and contradictory user-guide claims; no runtime routing claim added |
| DOC-16 | Static configuration or completed issue status can suggest completed RC1 qualification. | Link authoritative RC1 tracker and distinguish documented procedure from executed acceptance. | #294; existing RC1 audit |
| DOC-18 | Main advanced during the review and moved installer evidence off the checkout. | Rebase publication on the new main and update handbook/installation paths and lookup command. | PR #293; `_installation_evidence_directory` |
| DOC-17 | Troubleshooting import advice starts tests; a historical run ID is copyable as current. | Use import checks; require the actual printed run directory and handle missing setup exit after failed reset. | Installer exit/evidence handling |

## Validation and independent review

- `git diff --check`: PASS for the documentation-only patch.
- Checked 60 newly introduced relative links against the complete remote
  repository tree; locally available target fragments also checked: PASS.
- Checked Markdown fences, AsciiDoc listing/table delimiter balance and newly
  added Markdown-style links inside AsciiDoc: PASS.
- Commands/options compared statically with the current installer, CLI catalog,
  package metadata and credential validation. No installation, reset,
  reconciliation, authenticated browser or service command was executed.
- An independent read-only reviewer examined source and the diff. Its verdict
  was suitable for a documentation-only PR after two small corrections:
  identify the private authenticated-client approach without referring to an
  unnamed procedure, and warn about the remaining APT-mirror fresh-reset
  example. Both corrections were applied.
- Full Python quality suite: NOT RUN. This partial review snapshot changes no
  Python, tests, runtime configuration or quality policy. QUALITY.md explicitly
  permits a justified skip for documentation-only work; no full-suite PASS is
  claimed. Required repository CI remains observable on the PR.
- Rendered AsciiDoc/HTML preview: NOT RUN; an AsciiDoc renderer was unavailable.
  Source structure and new link destinations were checked instead.

## Publication boundary and remaining work

Publish on an isolated `docs/` branch based on the inspected main commit.
This is not a `workflow execute` or `push auto` invocation; no existing
workflow locks or implementation branch are modified. The change does not
close #294 or any release-acceptance issue. PR #293 was merged independently
while the review was running; its product changes are preserved in the base.

Product limitations remain owned by the existing issues: credential acceptance
#295/#296, update #297, Linux lifecycle #298, WSL/recovery #299, CI/Sonar #300,
Nightly #301 and final audit #302. Editing their explanation does not resolve
those runtime gaps.

Further installer changes must keep the evidence location and entry-point
behavior in sync with these user pages.


## Follow-up: place the handbook in user_guide

The user requested a closer review of the handbook's logical location.
The canonical file is now `documentation/user_guide/user-handbook.adoc`,
next to the installation, usage and troubleshooting guides. The former file
is removed, not duplicated.

Updated the root README, documentation index, Operator Manual, assembled
`documentation/document.adoc`, active audit source mapping, documentation
ownership skill/registry, installer diagnostic link and the existing test
fixture path. Historical changed-file lists/review findings retain their
original paths because they describe earlier revisions.

The handbook uses explicit relative-link prefixes so links resolve correctly
both as a standalone page and when included in the root aggregate document.
The affected README/registry governing hashes were refreshed.

Verification:
- `git diff --check`: PASS.
- 22 handbook link resolutions checked across standalone and aggregate
  contexts, including available target anchors: PASS.
- Existing `test_bridge_guides_document_reproducible_preparation`: PASS.
- Python AST parsing of the diagnostic/test path edits and JSON parsing: PASS.
- Documentation skill frontmatter validation: PASS.
- Independent read-only review of the move and prefix handling: approved.
- The only Python changes are a diagnostic path string and a test fixture
  path. No runtime control flow changed. Full product suite and rendered
  AsciiDoc preview remain unexecuted; this follow-up does not claim them.
