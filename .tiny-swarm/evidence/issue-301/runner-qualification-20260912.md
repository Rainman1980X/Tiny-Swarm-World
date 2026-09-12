# RC1-R05 Runner Qualification Evidence

Date: 2026-09-12

The repository runner API reported one online runner:

| Field | Observed value |
|---|---|
| Name | `tsw-protected-wsl2` |
| Status | `online` |
| Busy | `false` at observation time |
| Labels | `self-hosted`, `Linux`, `X64`, `tsw-protected`, `classic-live`, `tsw-classic` |
| Runner version | `2.337.0` |
| Host | Linux on WSL2, x86_64 |
| Incus | 6.0.5 client/server |
| Docker | 29.8.0 server |
| Python | 3.14 |

The `tsw-classic` label was added because it is the label selected by
`.github/workflows/nightly-classic-live.yml`. The runner process is running
under `/home/micro/actions-runner-tsw` and writes only local diagnostics.

This evidence qualifies runner registration and local capability only. It does
not qualify target ownership, protected-environment approval, credentials,
candidate images, a live lifecycle, or failure recovery.
